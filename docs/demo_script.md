# SentinelFlow Demonstration & Presentation Script

This script walks through the end-to-end hackathon demonstration flow.

---

## 1. Introduction & Research Question (1 Minute)
- **Concept:** Explain that SentinelFlow estimates session risk from combinations of behavioral signals over time rather than treating isolated single events (such as one password typo or a new browser) as proof of fraud.
- **Explainability:** Emphasize that the system uses a trained scikit-learn Decision Tree whose actual node split conditions are translated into plain-language explanations, with backend-enforced verification.
- **Disclaimer:** Synthetic data demonstration; not claimed as production banking infrastructure.

---

## 2. Walkthrough: The 3 Repeatable Scenarios (3 Minutes)

### Scenario A — Routine Session
1. Click **"Scenario A: Routine"** in the top bar.
2. **Observe:**
   - Familiar device context, normal daytime hours.
   - Paced interactions (`balance_viewed`, `statement_downloaded`).
   - Risk Category: **`LOW RISK`** (Green badge).
   - Class Probabilities: Low Risk dominant (~90-100%).
   - Model Explanation: *"The model did not identify a high-risk pattern in the supplied session features."*
   - Policy Status: **Allowed**. Sensitive actions (password change) proceed normally without interruption.

### Scenario B — Elevated-Risk Pattern
1. Click **"Scenario B: Elevated Risk"** in the top bar.
2. **Observe:**
   - Event timeline shows rapid burst of 4 failed login attempts (< 1.5s intervals) from an unfamiliar proxy device, followed by login success.
   - Password change was requested immediately within seconds of login.
   - Risk Category: **`HIGH RISK`** (Crimson badge).
   - Model Decision Path:
     - `login_failure_count (observed 4.0) exceeded learned threshold of 2.50`
     - `time_to_first_sensitive_action_sec (observed 5.5s) was <= learned threshold of 35.0s`
   - Policy Status: **Verification Required**.
3. **Trigger Sensitive Action:**
   - Click "Change Account Password" button.
   - Notice the backend blocks the action with HTTP 403 and automatically surfaces the **Simulated Step-Up Verification Modal**.
4. **Complete Verification:**
   - Enter demo code `123456` and click **"Verify & Unlock"**.
   - Notice the session updates to **`VERIFIED`**.
   - Sensitive action is now authorized and unlocked!

### Scenario C — Ambiguous Session
1. Click **"Scenario C: Ambiguous"** in the top bar.
2. **Observe:**
   - Unfamiliar device context is enabled, but pacing is normal and no brute-force attempts or immediate credential changes occur.
   - Risk Category: Evaluated as **`MEDIUM`** or **`LOW`** (showing that an unfamiliar device alone does not artificially force a high-risk alert).
   - Context observation reports: *"Unfamiliar device flagged in telemetry, but not decisive in the tree split."*

---

## 3. Held-Out Evaluation Metrics & Transparent Baseline
- Click **"Model Card & Metrics"** in the header.
- Show held-out test evaluation results:
  - **Macro-F1:** 91.2% (vs 87.5% for rule baseline).
  - **Balanced Accuracy:** 91.4%.
  - **High-Risk FPR:** 0.0%.
  - **Inference Latency:** < 0.1 ms per prediction.
- Close the presentation by summarizing honest limitations and privacy principles.
