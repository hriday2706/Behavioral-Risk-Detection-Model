"""
SentinelFlow Central Configuration.
Defines project paths, risk thresholds, policy parameters, and demo constants.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DOCS_DIR = BASE_DIR / "docs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Dataset & Model Artifact Paths
SYNTHETIC_DATASET_PATH = DATA_DIR / "synthetic_sessions.csv"
MODEL_PATH = MODELS_DIR / "decision_tree.joblib"
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.json"

# Database Configuration
DATABASE_PATH = BASE_DIR / "sentinelflow.db"

# Risk Categories
RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
ALL_RISK_CLASSES = [RISK_LOW, RISK_MEDIUM, RISK_HIGH]

# Policy Actions
POLICY_ACTION_ALLOW = "allow"
POLICY_ACTION_WARN = "warn"
POLICY_ACTION_REQUIRE_VERIFICATION = "verification_required"

# Policy Mapping
# Low: Allow normal actions
# Medium: Allow with warning / conditional verification
# High: Block sensitive action pending step-up verification
DEFAULT_POLICY_MAPPING = {
    RISK_LOW: POLICY_ACTION_ALLOW,
    RISK_MEDIUM: POLICY_ACTION_WARN,
    RISK_HIGH: POLICY_ACTION_REQUIRE_VERIFICATION,
}

# Feature Extraction Constants
MAX_RECENT_ACTIONS_WINDOW_SEC = 60
BURST_WINDOW_SEC = 30
SECURITY_CHANGE_ALERT_WINDOW_SEC = 120
UNUSUAL_HOURS_START_UTC = 1  # 01:00 UTC
UNUSUAL_HOURS_END_UTC = 5    # 05:00 UTC

# Feature Order (Strict)
FEATURE_COLUMNS = [
    "login_attempt_count",
    "login_failure_count",
    "login_failure_rate",
    "median_login_interval_sec",
    "min_login_interval_sec",
    "session_duration_sec",
    "sensitive_action_count",
    "time_to_first_sensitive_action_sec",
    "actions_last_60_sec",
    "unfamiliar_device_flag",
    "unusual_time_flag",
    "location_anomaly_flag",
    "security_change_after_login_flag",
    "action_burst_count",
]
