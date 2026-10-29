# SentinelFlow Model Card: Explainable Decision Tree Classifier

## 1. Model Details
- **Model Name:** SentinelFlow Explainable Decision Tree Classifier
- **Model Version:** 1.0.0
- **Model Type:** Supervised Decision Tree (`sklearn.tree.DecisionTreeClassifier`)
- **Hyperparameters:**
  - `max_depth`: 4 (strictly restricted for human auditability and anti-overfitting)
  - `min_samples_leaf`: 8
  - `class_weight`: "balanced"
  - `random_state`: 42
- **Artifact Location:** `models/decision_tree.joblib`
- **Metadata Location:** `models/model_metadata.json`

---

## 2. Intended Use & Boundaries
- **Primary Use:** Demonstrating session-level risk categorization (`low`, `medium`, `high`) in a banking-style demo, coupled with human-readable decision-path extraction.
- **Out of Scope:** Real-world banking fraud detection, live payment authorization, production AML compliance.
- **Disclaimer:** Evaluated on synthetic data; metrics do not guarantee performance on real attack distributions.

---

## 3. Features & Preprocessing
Input vector follows strict 14-feature order:
1. `login_attempt_count`
2. `login_failure_count`
3. `login_failure_rate`
4. `median_login_interval_sec`
5. `min_login_interval_sec`
6. `session_duration_sec`
7. `sensitive_action_count`
8. `time_to_first_sensitive_action_sec`
9. `actions_last_60_sec`
10. `unfamiliar_device_flag`
11. `unusual_time_flag`
12. `location_anomaly_flag`
13. `security_change_after_login_flag`
14. `action_burst_count`

No identifiers, usernames, scenario labels, or target flags are accessible to the model.

---

## 4. Evaluation on Held-Out Test Set (N = 180)

| Metric | Decision Tree (Trained) | Transparent Rule Baseline |
| :--- | :--- | :--- |
| **Macro F1-Score** | **0.9117** | 0.8745 |
| **Balanced Accuracy** | **0.9136** | 0.9000 |
| **High-Risk FPR** | **0.0000** | 0.0000 |
| **Low-Risk F1** | **0.8989** | 0.8235 |
| **Medium-Risk F1** | **0.8364** | 0.8000 |
| **High-Risk F1** | **1.0000** | 1.0000 |

### Confusion Matrix (Test Set):
- True Low: 80 correctly predicted, 10 predicted Medium, 0 predicted High.
- True Medium: 46 correctly predicted, 8 predicted Low, 0 predicted High.
- True High: 36 correctly predicted, 0 predicted Low, 0 predicted Medium.

---

## 5. Explainability Architecture
Rather than relying on post-hoc black-box approximations (such as generic LIME or SHAP kernels), SentinelFlow traverses the actual scikit-learn tree structure (`tree_.decision_path`). Each traversal step extracts:
- Feature name and split threshold.
- Observed session feature value.
- Direction taken (<= or > threshold).
- Final leaf node distribution.
Contextual signals not present in the tree path are reported separately as contextual background notes.
