"""
SentinelFlow Decision-Path Explanation Module.
Extracts the exact decision path traversed by a feature vector through the
scikit-learn Decision Tree, translates internal split conditions into plain language,
and cleanly separates tree path conditions from contextual observations.
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

from config import FEATURE_COLUMNS, RISK_HIGH, RISK_LOW, RISK_MEDIUM


# Human-friendly descriptions for feature names
FEATURE_HUMAN_LABELS = {
    "login_attempt_count": "Login attempts count",
    "login_failure_count": "Login failure count",
    "login_failure_rate": "Login failure rate",
    "median_login_interval_sec": "Median interval between logins (sec)",
    "min_login_interval_sec": "Minimum interval between logins (sec)",
    "session_duration_sec": "Total session duration (sec)",
    "sensitive_action_count": "Sensitive action request count",
    "time_to_first_sensitive_action_sec": "Time from login to first sensitive action (sec)",
    "actions_last_60_sec": "Actions performed in last 60 seconds",
    "unfamiliar_device_flag": "Unfamiliar device indicator",
    "unusual_time_flag": "Unusual login hours indicator",
    "location_anomaly_flag": "Simulated location anomaly indicator",
    "security_change_after_login_flag": "Security credential change within 120s of login",
    "action_burst_count": "Max actions burst in 30s window",
}


def explain_decision_path(
    model: DecisionTreeClassifier,
    feature_dict: Dict[str, float],
    predicted_class: str,
) -> Dict[str, Any]:
    """
    Extracts the actual traversed nodes from the fitted Decision Tree.

    Returns:
        Dictionary containing:
        - predicted_class: str
        - path_steps: list of individual node explanations
        - path_summary: list of plain-language bullet points
        - contextual_observations: list of contextual telemetry notes
    """
    feature_names = FEATURE_COLUMNS
    df_input = pd.DataFrame([[feature_dict.get(col, 0.0) for col in feature_names]], columns=feature_names)

    # Obtain sparse decision path from scikit-learn
    dp = model.decision_path(df_input)
    node_indices = dp.indices

    tree = model.tree_
    path_steps = []
    features_on_path = set()

    for node_idx in node_indices:
        # Check if node is an internal split node (not a leaf)
        if tree.children_left[node_idx] != tree.children_right[node_idx]:
            feat_idx = tree.feature[node_idx]
            feat_name = feature_names[feat_idx]
            features_on_path.add(feat_name)
            threshold = float(tree.threshold[node_idx])
            observed_val = float(df_input.iloc[0, feat_idx])
            human_name = FEATURE_HUMAN_LABELS.get(feat_name, feat_name)

            if observed_val <= threshold:
                condition_desc = f"{human_name} ({observed_val}) was \u2264 learned threshold of {threshold:.2f}"
                branch = "left"
            else:
                condition_desc = f"{human_name} ({observed_val}) exceeded learned threshold of {threshold:.2f}"
                branch = "right"

            path_steps.append({
                "node_index": int(node_idx),
                "feature": feat_name,
                "feature_label": human_name,
                "observed_value": observed_val,
                "threshold": round(threshold, 2),
                "branch": branch,
                "description": condition_desc,
            })

    # Plain-language summary
    path_summary = []
    if predicted_class == RISK_LOW:
        path_summary.append("The model did not identify a high-risk pattern in the supplied session features.")
        for step in path_steps:
            path_summary.append(f"Model path: {step['description']}.")
    elif predicted_class == RISK_MEDIUM:
        path_summary.append("The model flagged moderate behavioral or contextual deviations.")
        for step in path_steps:
            path_summary.append(f"Model path: {step['description']}.")
    elif predicted_class == RISK_HIGH:
        path_summary.append("The model identified an elevated-risk behavioral combination.")
        for step in path_steps:
            path_summary.append(f"Model path: {step['description']}.")

    # Contextual observations: clearly separate telemetry from model path
    contextual_observations = []
    if feature_dict.get("unfamiliar_device_flag", 0.0) == 1.0:
        if "unfamiliar_device_flag" in features_on_path:
            contextual_observations.append("Context observation: Unfamiliar device context was evaluated directly in the tree path.")
        else:
            contextual_observations.append("Context observation: Unfamiliar device flagged in telemetry, but not decisive in the tree split.")
    else:
        contextual_observations.append("Context observation: Recognized familiar demo device.")

    if feature_dict.get("unusual_time_flag", 0.0) == 1.0:
        contextual_observations.append("Context observation: Session occurred during unusual simulated hours (01:00-05:00 UTC).")
    else:
        contextual_observations.append("Context observation: Normal business/daytime hours.")

    if feature_dict.get("location_anomaly_flag", 0.0) == 1.0:
        contextual_observations.append("Context observation: Simulated location anomaly flag present in telemetry.")

    return {
        "predicted_class": predicted_class,
        "path_steps": path_steps,
        "path_summary": path_summary,
        "contextual_observations": contextual_observations,
    }
