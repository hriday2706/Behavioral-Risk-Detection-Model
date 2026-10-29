# SentinelFlow Labeling Policy & Scope

## 1. Research Question
Can a small set of session-level behavioral features distinguish simulated routine sessions from simulated elevated-risk sessions while keeping false positives visible and predictions explainable?

## 2. Label Definitions (Multi-class: `low`, `medium`, `high`)
In this hackathon proof of concept, labels represent **synthetic risk tiers**, not confirmed legal or banking fraud verdicts.

- **`low` (Routine Session):**
  - Ordinary user pacing (human-paced intervals).
  - Normal or zero login failures (e.g. 0 or 1 typo followed by success).
  - Familiar device context or single benign novelty without rapid sensitive action requests.
  - Typical actions: balance check, statement download, standard session length.

- **`medium` (Ambiguous / Suspicious Session):**
  - Noticeable deviations or single strong contextual discrepancies without high-risk burst patterns.
  - Examples: Unfamiliar device logging in during unusual hours, but performing ordinary actions (testing false-alarm propensity).
  - Single failed attempt followed by success on a new device.
  - Paced security change request without preceding brute-force attempts.
  - Operational Response: Step-up monitoring or warning.

- **`high` (Elevated-Risk / Compromise Indicator):**
  - Compound anomalous signals occurring in close temporal proximity.
  - Multiple rapid failed login attempts (burst/brute-force profile) followed by sudden success.
  - Unfamiliar device context combined with immediate post-login sensitive actions (`password_change_requested`, `email_update_requested`) within <= 120 seconds.
  - Operational Response: Mandatory step-up verification (e.g., simulated MFA challenge) before sensitive operations are permitted.

## 3. Leakage Prevention and Data Hygiene Rules
1. **No Identifier Shortcuts:** Model inputs must never include `user_id`, `session_id`, `scenario_name`, `account_number`, or timestamp strings.
2. **Deterministic Multi-Signal Mapping:** Labels are assigned based on multi-signal combinations in synthetic data generation, deliberately including noisy, overlapping, and contradictory cases (e.g., unfamiliar device + ordinary session = `medium` or `low`, never automatically `high`).
3. **Session-Level Splitting:** Train, validation, and test splits are strictly separated by `session_id` and scenario generator seeds to prevent data contamination across splits.
4. **Honest Evaluation:** Synthetic evaluation shows feasibility of decision-tree behavioral routing; it does NOT establish real-world banking production accuracy.
