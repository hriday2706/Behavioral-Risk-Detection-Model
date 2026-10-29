# SentinelFlow: Behavior-Based Risk Level Prediction System

SentinelFlow is a hackathon proof of concept estimating session risk in a banking-style demo from behavioral and contextual signals over time rather than treating isolated actions as definitive fraud.

## 1. Core Principles
- **Explainable by Design:** Uses a shallow, interpretable scikit-learn Decision Tree. Explanations correspond directly to the actual branch conditions traversed by the session's feature vector.
- **Separation of Concerns:** 
  - **Event Logging:** Records timestamped immutable actions in SQLite.
  - **Feature Extraction:** Pure function deriving statistical & temporal behavioral metrics.
  - **ML Inference:** Predicts risk tier (`low`, `medium`, `high`) and class probabilities.
  - **Decision-Path Explanation:** Reports traversed tree splits in human-readable terms.
  - **Risk Policy Layer:** Decides security response (`allow`, `warn`, `verification_required`).
  - **Frontend UI:** Displays dashboard, interactive actions, timeline, and risk breakdown.
- **Backend Enforcement:** Sensitive actions (`password_change_requested`, `email_update_requested`) are strictly gated by the backend policy, never client-side UI toggles.
- **Privacy & Ethical Integrity:** Fictional accounts only. No real banking credentials, no invasive hardware fingerprinting, and no unverified claims of physical geolocation.

---

## 2. Architecture Flow
```
User / Demo Action
       │
       ▼
Flask Backend API
       │
       ▼
SQLite Event Store (Timestamped history)
       │
       ▼
Feature Extraction (Deterministic behavioral metrics)
       │
       ▼
Trained Decision Tree Classifier
       │
       ▼
Decision-Path Explainer ──► Risk Policy Engine ──► Verification Gate
       │                              │
       └──────────────┬───────────────┘
                      ▼
            Frontend Risk Dashboard
```

---

## 3. Quickstart & Installation

```bash
# Clone repository and enter directory
cd "E:\Behvioural Risk Engine"

# Install dependencies
pip install -r requirements.txt

# Run automated tests
pytest -v

# Start development server
python app.py
```

Health endpoint: `GET http://127.0.0.1:5000/api/health`

---

## 4. Milestone Roadmap
- [x] **M0: Scope & Definitions** (Event schema, feature dictionary, labeling policy)
- [x] **M1: Environment & Skeleton** (Git, config, dependencies, health endpoint, test setup)
- [ ] **M2: Synthetic Data Generation** (Routine, ambiguous, elevated-risk session generator)
- [ ] **M3: Feature Extraction Engine** (Pure, fully tested session-to-features extractor)
- [ ] **M4: EDA & Leakage Checks** (Distribution analysis, correlation, leakage audit)
- [ ] **M5: Model Training & Evaluation** (Decision Tree training, metrics, confusion matrix)
- [ ] **M6: Decision-Path Explanation Module** (Tree traversal to natural language)
- [ ] **M7: Event Storage & Backend API** (SQLite persistence, routes, session manager)
- [ ] **M8: Banking Demo Frontend** (Dashboard, timeline, risk panel, scenarios)
- [ ] **M9: Backend-Enforced Step-Up Policy** (MFA challenge, sensitive action gating)
- [ ] **M10: End-to-End Verification & Presentation** (Demonstrations, documentation)
