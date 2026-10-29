"""
SentinelFlow Feature Extraction Module.
Derives deterministic session-level behavioral features from sorted session events.
Used identically during synthetic dataset generation, model training, and live inference.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import numpy as np

from config import (
    BURST_WINDOW_SEC,
    FEATURE_COLUMNS,
    MAX_RECENT_ACTIONS_WINDOW_SEC,
    SECURITY_CHANGE_ALERT_WINDOW_SEC,
    UNUSUAL_HOURS_END_UTC,
    UNUSUAL_HOURS_START_UTC,
)
from src.event_schema import EventType, SENSITIVE_ACTIONS, SessionEvent


def parse_iso_timestamp(ts: Union[str, datetime]) -> datetime:
    """Safely parse ISO-8601 UTC timestamp string into timezone-aware datetime."""
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    cleaned = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def extract_session_features(
    events: List[Union[SessionEvent, Dict[str, Any]]],
    evaluation_time: Optional[Union[str, datetime]] = None,
) -> Dict[str, float]:
    """
    Extracts the 14 documented behavioral features from a list of session events.

    Parameters:
        events: List of SessionEvent instances or dictionary equivalents.
        evaluation_time: Optional cutoff timestamp (ISO string or datetime).
                         Events occurring after this timestamp are excluded (leakage prevention).

    Returns:
        Dictionary mapping feature names to numerical values.
    """
    if not events:
        # Default empty session feature representation
        return {col: 0.0 if "flag" in col or "count" in col or "rate" in col else -1.0 for col in FEATURE_COLUMNS}

    # Normalize to objects with attributes and timestamps
    parsed_events = []
    for ev in events:
        if isinstance(ev, dict):
            # Parse dict
            ts = parse_iso_timestamp(ev["timestamp_utc"])
            parsed_events.append({
                "event_type": ev.get("event_type", ""),
                "timestamp": ts,
                "success": bool(ev.get("success", True)),
                "device_familiarity": str(ev.get("device_familiarity", "familiar")).lower(),
                "location_context": str(ev.get("location_context", "home")).lower(),
            })
        else:
            ts = parse_iso_timestamp(ev.timestamp_utc)
            parsed_events.append({
                "event_type": ev.event_type,
                "timestamp": ts,
                "success": bool(ev.success),
                "device_familiarity": str(ev.device_familiarity).lower(),
                "location_context": str(ev.location_context).lower(),
            })

    # Sort strictly by timestamp (chronological)
    parsed_events.sort(key=lambda x: x["timestamp"])

    # Apply evaluation_time cutoff if provided
    if evaluation_time is not None:
        eval_dt = parse_iso_timestamp(evaluation_time)
        parsed_events = [e for e in parsed_events if e["timestamp"] <= eval_dt]
        if not parsed_events:
            return {col: 0.0 if "flag" in col or "count" in col or "rate" in col else -1.0 for col in FEATURE_COLUMNS}

    first_event_time = parsed_events[0]["timestamp"]
    latest_event_time = parsed_events[-1]["timestamp"]
    session_duration_sec = max(0.0, (latest_event_time - first_event_time).total_seconds())

    # 1. Login attempts & failures
    login_events = [
        e for e in parsed_events
        if e["event_type"] in (EventType.LOGIN_ATTEMPT.value, EventType.LOGIN_FAILURE.value, EventType.LOGIN_SUCCESS.value)
    ]
    login_failure_events = [
        e for e in parsed_events
        if e["event_type"] == EventType.LOGIN_FAILURE.value or (e["event_type"] == EventType.LOGIN_ATTEMPT.value and not e["success"])
    ]
    login_success_events = [
        e for e in parsed_events
        if e["event_type"] == EventType.LOGIN_SUCCESS.value or (e["event_type"] == EventType.LOGIN_ATTEMPT.value and e["success"])
    ]

    login_attempt_count = len(login_events)
    login_failure_count = len(login_failure_events)
    login_failure_rate = float(login_failure_count / max(1, login_attempt_count)) if login_attempt_count > 0 else 0.0

    # Login intervals
    if len(login_events) >= 2:
        intervals = [
            (login_events[i]["timestamp"] - login_events[i - 1]["timestamp"]).total_seconds()
            for i in range(1, len(login_events))
        ]
        intervals = [max(0.0, iv) for iv in intervals]
        median_login_interval_sec = float(np.median(intervals))
        min_login_interval_sec = float(np.min(intervals))
    else:
        median_login_interval_sec = -1.0
        min_login_interval_sec = -1.0

    # 2. Sensitive action features
    sensitive_events = [e for e in parsed_events if e["event_type"] in SENSITIVE_ACTIONS]
    sensitive_action_count = len(sensitive_events)

    time_to_first_sensitive_action_sec = -1.0
    security_change_after_login_flag = 0.0

    if login_success_events and sensitive_events:
        first_login_success_time = login_success_events[0]["timestamp"]
        first_sensitive_time = sensitive_events[0]["timestamp"]
        delta = (first_sensitive_time - first_login_success_time).total_seconds()
        if delta >= 0:
            time_to_first_sensitive_action_sec = float(delta)
            if delta <= SECURITY_CHANGE_ALERT_WINDOW_SEC:
                security_change_after_login_flag = 1.0

    # 3. Recent activity in last 60 seconds
    actions_last_60_sec = 0
    for e in parsed_events:
        if (latest_event_time - e["timestamp"]).total_seconds() <= MAX_RECENT_ACTIONS_WINDOW_SEC:
            actions_last_60_sec += 1

    # 4. Contextual signals (simulated)
    unfamiliar_device_flag = 1.0 if any(e["device_familiarity"] == "unfamiliar" for e in parsed_events) else 0.0
    location_anomaly_flag = 1.0 if any(e["location_context"] not in ("home", "office", "familiar") for e in parsed_events) else 0.0

    # Unusual hours: based on session start UTC hour
    start_hour_utc = first_event_time.hour
    unusual_time_flag = 1.0 if (UNUSUAL_HOURS_START_UTC <= start_hour_utc <= UNUSUAL_HOURS_END_UTC) else 0.0

    # 5. Action burst count: maximum actions in any rolling 30-second window
    action_burst_count = 1
    if len(parsed_events) > 1:
        timestamps = [e["timestamp"].timestamp() for e in parsed_events]
        max_in_window = 1
        for i in range(len(timestamps)):
            window_end = timestamps[i] + BURST_WINDOW_SEC
            count = sum(1 for t in timestamps[i:] if t <= window_end)
            if count > max_in_window:
                max_in_window = count
        action_burst_count = max_in_window

    features = {
        "login_attempt_count": float(login_attempt_count),
        "login_failure_count": float(login_failure_count),
        "login_failure_rate": round(float(login_failure_rate), 4),
        "median_login_interval_sec": round(float(median_login_interval_sec), 2),
        "min_login_interval_sec": round(float(min_login_interval_sec), 2),
        "session_duration_sec": round(float(session_duration_sec), 2),
        "sensitive_action_count": float(sensitive_action_count),
        "time_to_first_sensitive_action_sec": round(float(time_to_first_sensitive_action_sec), 2),
        "actions_last_60_sec": float(actions_last_60_sec),
        "unfamiliar_device_flag": float(unfamiliar_device_flag),
        "unusual_time_flag": float(unusual_time_flag),
        "location_anomaly_flag": float(location_anomaly_flag),
        "security_change_after_login_flag": float(security_change_after_login_flag),
        "action_burst_count": float(action_burst_count),
    }

    return features


def features_to_vector(features_dict: Dict[str, float]) -> List[float]:
    """Convert features dictionary to an ordered numerical vector matching FEATURE_COLUMNS."""
    return [features_dict.get(col, 0.0) for col in FEATURE_COLUMNS]
