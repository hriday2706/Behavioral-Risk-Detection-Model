# SentinelFlow Behavioral Feature Dictionary

This document formally defines the session-level behavioral features used in SentinelFlow.
All features are derived deterministically from timestamped session event histories.
**Strict Rule:** No feature encodes user identity, account name, scenario label, or raw row ID.

---

## 1. Feature Definitions

| Feature Name | Type | Unit | Range | Definition / Extraction Logic | Handling of Edge Cases & Missingness |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `login_attempt_count` | Integer | Count | \([0, \infty)\) | Total number of `login_attempt` (or associated `login_failure` / `login_success`) events in the session. | 0 if no login attempts occurred in the recorded session window. |
| `login_failure_count` | Integer | Count | \([0, \infty)\) | Number of explicit `login_failure` events recorded. | 0 if no failures. |
| `login_failure_rate` | Float | Ratio | \([0.0, 1.0]\) | Ratio of `login_failure_count` to `login_attempt_count`. | Set to `0.0` when `login_attempt_count == 0` to prevent division by zero. |
| `median_login_interval_sec` | Float | Seconds | \([0.0, \infty)\) | Median time interval in seconds between consecutive login attempts in the session. | If fewer than 2 login attempts occurred, assigned a neutral imputation sentinel `-1.0` (handled by imputer). |
| `min_login_interval_sec` | Float | Seconds | \([0.0, \infty)\) | Minimum elapsed seconds between consecutive login attempts. Rapid bursts (< 2.0s) may indicate automated scripting. | Assigned `-1.0` if fewer than 2 login attempts occurred. |
| `session_duration_sec` | Float | Seconds | \([0.0, \infty)\) | Elapsed time from the earliest recorded event in the session to the latest event (or assessment checkpoint). | `0.0` if only 1 event or empty session. |
| `sensitive_action_count` | Integer | Count | \([0, \infty)\) | Total count of requested sensitive actions (`password_change_requested`, `email_update_requested`). | `0` if none requested. |
| `time_to_first_sensitive_action_sec` | Float | Seconds | \([0.0, \infty)\) | Time elapsed from successful login (`login_success`) to the first sensitive action request. | Assigned sentinel `-1.0` if no sensitive actions occurred or no login occurred. |
| `actions_last_60_sec` | Integer | Count | \([0, \infty)\) | Count of events occurring within the 60-second window preceding the evaluation timestamp. | Evaluated strictly relative to server event timestamps. |
| `unfamiliar_device_flag` | Binary | Flag (0/1) | \(\{0, 1\}\) | `1` if the session's client/device context is marked unfamiliar/new in simulated telemetry, `0` if familiar. | Categorical binary; default `0` if unspecified. |
| `unusual_time_flag` | Binary | Flag (0/1) | \(\{0, 1\}\) | `1` if the session started outside standard demo daytime hours (e.g., between 01:00 and 05:00 UTC). | Derived from `timestamp_utc` hour; `0` if missing. |
| `location_anomaly_flag` | Binary | Flag (0/1) | \(\{0, 1\}\) | `1` if simulated geo-telemetry indicates a coarse location discrepancy, `0` otherwise. | Contextual simulated flag; never claimed as verified GPS or physical location. |
| `security_change_after_login_flag` | Binary | Flag (0/1) | \(\{0, 1\}\) | `1` if a security credential change (password/email update) was requested within 120 seconds of login success, `0` otherwise. | `0` if no security change occurred or occurred > 120s post-login. |
| `action_burst_count` | Integer | Count | \([0, \infty)\) | Maximum number of actions occurring in any rolling 30-second window across the session. | Computed over all sorted session events. |

---

## 2. Feature Vector Schema Order
For model input consistency between training and live inference pipelines:
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

---

## 3. Disclaimers & Integrity
- **Simulated Context:** `unfamiliar_device_flag`, `unusual_time_flag`, and `location_anomaly_flag` are simulated contextual attributes for this proof of concept. They do NOT reflect hardware biometric fingerprinting or real IP geolocation.
- **Leakage Prevention:** Features are strictly derived from past events up to the assessment point. Future events are strictly excluded.
