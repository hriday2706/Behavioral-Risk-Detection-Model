# SentinelFlow Synthetic Dataset Card

## 1. Dataset Summary
- **Dataset Name:** SentinelFlow Synthetic Behavioral Sessions (`synthetic_sessions.csv`)
- **Total Records:** 1,200 simulated sessions
- **Intended Use:** Hackathon proof-of-concept modeling and explainable decision-tree validation.
- **Labels:** Multi-class synthetic risk proxy (`low`, `medium`, `high`).
- **Distribution:**
  - `low`: 600 sessions (50.0%)
  - `medium`: 360 sessions (30.0%)
  - `high`: 240 sessions (20.0%)

## 2. Scenario Families & Generation Logic
1. **Routine (`low`):**
   - Normal human pacing (intervals 4s - 60s).
   - Occasional single typo failure (25% probability), recovered successfully.
   - 10% simulated unfamiliar devices to prevent single-feature shortcut overfitting.
   - Paced interactions (`balance_viewed`, `statement_downloaded`).
2. **Ambiguous (`medium`):**
   - Moderate anomalies without compound threat markers.
   - Variants include: new device with ordinary behavior, unusual login hour with familiar context, isolated spaced failures, or security change requested after a standard human delay.
3. **Elevated Risk (`high`):**
   - Rapid bursts of failed attempts (min interval < 3.2s, 3-6 failures).
   - Unfamiliar device and proxy/datacenter contextual anomaly.
   - Immediate sensitive action requests (`password_change_requested`, `email_update_requested`) within <= 35 seconds of login.

## 3. Leakage Prevention
- **Excluded Identifiers:** `session_id`, `user_id`, and `scenario_family` are never fed into model training.
- **Identical Feature Code:** Feature values in the CSV are computed with the exact same `extract_session_features` function used by the live application.
- **Session-Level Splitting:** Splits are partitioned by session; all checkpoints of any session reside within a single split.

## 4. Ethical Considerations and Disclaimers
- **Synthetic Data Disclaimer:** This dataset consists purely of mock, computer-generated event sequences. It does NOT represent real banking fraud prevalence or production-grade attacker evasion techniques.
- **No Real PII:** No passwords, bank accounts, SSNs, credit cards, or actual IP addresses exist in this data.
