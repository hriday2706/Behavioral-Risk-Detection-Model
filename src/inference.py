"""
SentinelFlow Model Inference & Risk Assessment Pipeline.
Orchestrates event extraction, model prediction, probability estimation,
tree explanation, and policy evaluation into a single entry point.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from config import ALL_RISK_CLASSES, FEATURE_COLUMNS, MODEL_PATH, RISK_LOW
from src.event_schema import SessionEvent
from src.explanations import explain_decision_path
from src.feature_extraction import extract_session_features, features_to_vector
from src.risk_policy import RiskPolicyEngine


class RiskInferenceEngine:
    _instance: Optional["RiskInferenceEngine"] = None

    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = model_path
        self.model = None
        self.policy_engine = RiskPolicyEngine()
        self.load_model()

    def load_model(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model artifact not found at {self.model_path}. Train model first."
            )
        self.model = joblib.load(self.model_path)

    @classmethod
    def get_instance(cls) -> "RiskInferenceEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def assess_session(
        self,
        events: List[Union[SessionEvent, Dict[str, Any]]],
        target_action: Optional[str] = None,
        is_verified_in_session: bool = False,
    ) -> Dict[str, Any]:
        """
        Full assessment: events -> features -> model -> path explanation -> policy.
        """
        if not events:
            # Baseline empty session
            features = extract_session_features([])
            pred_class = RISK_LOW
            probs = {cls_name: 0.33 for cls_name in ALL_RISK_CLASSES}
            probs[RISK_LOW] = 1.0
            probs["medium"] = 0.0
            probs["high"] = 0.0
            path_exp = {
                "predicted_class": RISK_LOW,
                "path_steps": [],
                "path_summary": ["No events recorded yet. Session is in initial state."],
                "contextual_observations": ["Awaiting initial activity."],
            }
            policy_decision = self.policy_engine.evaluate(
                predicted_class=pred_class,
                event_type=target_action or "session_started",
                is_verified_in_session=is_verified_in_session,
            )
            return {
                "predicted_class": pred_class,
                "class_probabilities": probs,
                "features": features,
                "model_path_explanation": path_exp["path_summary"],
                "path_steps": path_exp["path_steps"],
                "context_observations": path_exp["contextual_observations"],
                "risk_policy": policy_decision.to_dict(),
                "is_simulated_context": True,
            }

        # 1. Feature Extraction
        features = extract_session_features(events)
        df_input = pd.DataFrame([[features.get(col, 0.0) for col in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)

        # 2. Model Prediction & Probabilities
        pred_class = str(self.model.predict(df_input)[0])
        raw_probs = self.model.predict_proba(df_input)[0]
        class_probabilities = {
            cls_name: round(float(prob), 4)
            for cls_name, prob in zip(self.model.classes_, raw_probs)
        }

        # 3. Decision Path Explanation
        explanation = explain_decision_path(
            model=self.model,
            feature_dict=features,
            predicted_class=pred_class,
        )

        # 4. Risk Policy Evaluation
        effective_action = target_action or (events[-1].event_type if isinstance(events[-1], SessionEvent) else events[-1].get("event_type", "activity"))
        policy_decision = self.policy_engine.evaluate(
            predicted_class=pred_class,
            event_type=effective_action,
            is_verified_in_session=is_verified_in_session,
        )

        return {
            "predicted_class": pred_class,
            "class_probabilities": class_probabilities,
            "features": features,
            "model_path_explanation": explanation["path_summary"],
            "path_steps": explanation["path_steps"],
            "context_observations": explanation["contextual_observations"],
            "risk_policy": policy_decision.to_dict(),
            "is_simulated_context": True,
        }
