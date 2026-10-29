"""
SentinelFlow Model Evaluation Module.
Inspects saved Decision Tree, tests latency, and prints evaluation summary.
"""

from pathlib import Path
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

from config import ALL_RISK_CLASSES, FEATURE_COLUMNS, MODEL_PATH, SYNTHETIC_DATASET_PATH


def evaluate_saved_model(
    model_path: Path = MODEL_PATH,
    dataset_path: Path = SYNTHETIC_DATASET_PATH
) -> None:
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found at {model_path}")
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    model = joblib.load(model_path)
    df = pd.read_csv(dataset_path)

    X = df[FEATURE_COLUMNS]
    y = df["label"]

    # Latency test: 1,000 single-instance predictions
    sample_vec = X.iloc[[0]].values
    latencies = []
    for _ in range(1000):
        t0 = time.perf_counter()
        _ = model.predict(sample_vec)
        latencies.append((time.perf_counter() - t0) * 1000)

    median_lat_ms = np.median(latencies)
    p95_lat_ms = np.percentile(latencies, 95)

    y_pred = model.predict(X)
    print("=== Model Evaluation on Full Synthetic Population ===")
    print(f"Total instances evaluated: {len(X)}")
    print(f"Median inference latency: {median_lat_ms:.3f} ms (p95: {p95_lat_ms:.3f} ms)")
    print("\nConfusion Matrix (Low, Medium, High):")
    print(confusion_matrix(y, y_pred, labels=ALL_RISK_CLASSES))
    print("\nClassification Report:")
    print(classification_report(y, y_pred, labels=ALL_RISK_CLASSES))


if __name__ == "__main__":
    evaluate_saved_model()
