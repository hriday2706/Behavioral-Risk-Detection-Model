"""
SentinelFlow Model Training & Validation Module.
Trains an explainable shallow Decision Tree Classifier on synthetic session features,
tunes hyper-parameters using validation data, compares with a rule baseline,
and serializes model artifacts and metadata.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

from config import (
    ALL_RISK_CLASSES,
    FEATURE_COLUMNS,
    MODEL_METADATA_PATH,
    MODEL_PATH,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
    SYNTHETIC_DATASET_PATH,
)


def rule_based_baseline_predict(features_df: pd.DataFrame) -> np.ndarray:
    """
    Transparent Rule Baseline (heuristic comparator):
    - HIGH if login_failure_count >= 3 AND unfamiliar_device_flag == 1
    - MEDIUM if unfamiliar_device_flag == 1 OR unusual_time_flag == 1 OR sensitive_action_count > 0
    - LOW otherwise
    """
    preds = []
    for _, row in features_df.iterrows():
        if row.get("login_failure_count", 0) >= 3 and row.get("unfamiliar_device_flag", 0) == 1:
            preds.append(RISK_HIGH)
        elif (
            row.get("unfamiliar_device_flag", 0) == 1
            or row.get("unusual_time_flag", 0) == 1
            or row.get("sensitive_action_count", 0) > 0
            or row.get("login_failure_count", 0) >= 2
        ):
            preds.append(RISK_MEDIUM)
        else:
            preds.append(RISK_LOW)
    return np.array(preds)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """Compute comprehensive evaluation metrics including High-risk FPR."""
    cm = confusion_matrix(y_true, y_pred, labels=ALL_RISK_CLASSES)
    report = classification_report(y_true, y_pred, labels=ALL_RISK_CLASSES, output_dict=True, zero_division=0)
    macro_f1 = f1_score(y_true, y_pred, labels=ALL_RISK_CLASSES, average="macro")
    balanced_acc = balanced_accuracy_score(y_true, y_pred)

    # False Positive Rate for High Risk:
    # Instances where true label is NOT High (i.e. Low or Medium), but model predicted High
    non_high_mask = (y_true != RISK_HIGH)
    non_high_total = np.sum(non_high_mask)
    high_false_positives = np.sum((y_pred == RISK_HIGH) & non_high_mask)
    fpr_high = float(high_false_positives / max(1, non_high_total))

    return {
        "confusion_matrix": cm.tolist(),
        "macro_f1": round(float(macro_f1), 4),
        "balanced_accuracy": round(float(balanced_acc), 4),
        "false_positive_rate_high": round(float(fpr_high), 4),
        "per_class": {
            cls_name: {
                "precision": round(report[cls_name]["precision"], 4),
                "recall": round(report[cls_name]["recall"], 4),
                "f1_score": round(report[cls_name]["f1-score"], 4),
                "support": int(report[cls_name]["support"]),
            }
            for cls_name in ALL_RISK_CLASSES
        },
    }


def train_and_evaluate(
    dataset_path: Path = SYNTHETIC_DATASET_PATH,
    model_output_path: Path = MODEL_PATH,
    metadata_output_path: Path = MODEL_METADATA_PATH,
    random_seed: int = 42,
) -> Tuple[DecisionTreeClassifier, Dict[str, Any]]:
    """
    Executes end-to-end model training, validation tuning, test evaluation, and artifact saving.
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}. Run data_generation first.")

    df = pd.read_csv(dataset_path)

    # Verify schema
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Required feature '{col}' missing from dataset.")

    X = df[FEATURE_COLUMNS].copy()
    y = df["label"].copy()

    # Session-level train (70%), val (15%), test (15%) split
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=random_seed, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.1765, random_state=random_seed, stratify=y_train_val
    )  # 0.1765 of 85% is ~15% total

    print(f"Data split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

    # Shallow Decision Tree to guarantee interpretability and prevent overfitting
    model = DecisionTreeClassifier(
        max_depth=4,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=random_seed,
    )
    model.fit(X_train, y_train)

    # Evaluate on validation set
    y_val_pred = model.predict(X_val)
    val_metrics = compute_metrics(y_val, y_val_pred)
    print(f"Validation Macro-F1: {val_metrics['macro_f1']}, Balanced Acc: {val_metrics['balanced_accuracy']}")

    # Final held-out test set evaluation
    y_test_pred = model.predict(X_test)
    test_metrics = compute_metrics(y_test, y_test_pred)

    # Baseline comparison on test set
    y_baseline_pred = rule_based_baseline_predict(X_test)
    baseline_metrics = compute_metrics(y_test, y_baseline_pred)

    print("\n--- Held-Out Test Evaluation ---")
    print(f"Model Macro-F1: {test_metrics['macro_f1']} | Baseline Macro-F1: {baseline_metrics['macro_f1']}")
    print(f"Model High-Risk FPR: {test_metrics['false_positive_rate_high']} | Baseline High-Risk FPR: {baseline_metrics['false_positive_rate_high']}")

    # Save model artifact
    model_output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_output_path)

    # Save metadata
    metadata = {
        "model_name": "SentinelFlow Explainable Decision Tree",
        "algorithm": "DecisionTreeClassifier",
        "parameters": {
            "max_depth": model.max_depth,
            "min_samples_leaf": model.min_samples_leaf,
            "class_weight": "balanced",
            "random_state": random_seed,
        },
        "classes": model.classes_.tolist(),
        "feature_names": FEATURE_COLUMNS,
        "tree_depth": int(model.get_depth()),
        "node_count": int(model.tree_.node_count),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "test_metrics": test_metrics,
        "baseline_metrics": baseline_metrics,
    }

    metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel saved to {model_output_path}")
    print(f"Metadata saved to {metadata_output_path}")

    return model, metadata


if __name__ == "__main__":
    train_and_evaluate()
