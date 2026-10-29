"""
SentinelFlow Synthetic Session Data Generator.
Generates realistic simulated session event streams across routine, ambiguous,
and elevated-risk patterns with randomized variations, interval jitter, and noise.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import random
from typing import Any, Dict, List, Tuple
import pandas as pd

from config import ALL_RISK_CLASSES, FEATURE_COLUMNS, RISK_HIGH, RISK_LOW, RISK_MEDIUM, SYNTHETIC_DATASET_PATH
from src.event_schema import EventType, SessionEvent
from src.feature_extraction import extract_session_features


def generate_routine_session(session_id: str, user_id: str, seed: int) -> Tuple[List[SessionEvent], str]:
    """
    Scenario Family: Routine Session (Target: low)
    - Familiar device (90%) or unfamiliar device without any suspicious actions (10%).
    - Normal daytime hours (90%) or harmless unusual time (10%).
    - 0 or 1 typo failure followed by success with human pacing (4s-15s).
    - Normal actions: balance_viewed, statement_downloaded.
    - No rapid burst of sensitive requests.
    """
    rng = random.Random(seed)
    events: List[SessionEvent] = []

    # Start time
    hour = rng.choice([9, 10, 11, 14, 15, 16, 17, 20]) if rng.random() > 0.1 else 2
    base_time = datetime(2026, 3, 10, hour, rng.randint(0, 50), rng.randint(0, 50), tzinfo=timezone.utc)
    curr_time = base_time

    device = "familiar" if rng.random() > 0.1 else "unfamiliar"
    location = "home" if rng.random() > 0.1 else "office"

    # Start event
    events.append(SessionEvent.create(
        session_id=session_id,
        user_id=user_id,
        event_type=EventType.SESSION_STARTED.value,
        timestamp_utc=curr_time.isoformat(),
        device_familiarity=device,
        location_context=location,
    ))

    # Optional 1 typo failure
    has_typo = rng.random() < 0.25
    if has_typo:
        curr_time += timedelta(seconds=rng.uniform(6.0, 18.0))
        events.append(SessionEvent.create(
            session_id=session_id,
            user_id=user_id,
            event_type=EventType.LOGIN_FAILURE.value,
            timestamp_utc=curr_time.isoformat(),
            success=False,
            device_familiarity=device,
            location_context=location,
        ))

    # Successful login
    curr_time += timedelta(seconds=rng.uniform(8.0, 25.0))
    events.append(SessionEvent.create(
        session_id=session_id,
        user_id=user_id,
        event_type=EventType.LOGIN_SUCCESS.value,
        timestamp_utc=curr_time.isoformat(),
        success=True,
        device_familiarity=device,
        location_context=location,
    ))

    # Ordinary actions
    num_actions = rng.randint(1, 4)
    action_types = [EventType.BALANCE_VIEWED.value, EventType.STATEMENT_DOWNLOADED.value]
    for _ in range(num_actions):
        curr_time += timedelta(seconds=rng.uniform(15.0, 60.0))
        act = rng.choice(action_types)
        events.append(SessionEvent.create(
            session_id=session_id,
            user_id=user_id,
            event_type=act,
            timestamp_utc=curr_time.isoformat(),
            success=True,
            device_familiarity=device,
            location_context=location,
        ))

    # Optional delayed security change (> 150s after login, well-paced)
    if rng.random() < 0.08:
        curr_time += timedelta(seconds=rng.uniform(160.0, 240.0))
        events.append(SessionEvent.create(
            session_id=session_id,
            user_id=user_id,
            event_type=EventType.PASSWORD_CHANGE_REQUESTED.value,
            timestamp_utc=curr_time.isoformat(),
            device_familiarity=device,
            location_context=location,
        ))

    return events, RISK_LOW


def generate_ambiguous_session(session_id: str, user_id: str, seed: int) -> Tuple[List[SessionEvent], str]:
    """
    Scenario Family: Ambiguous / Moderate Risk (Target: medium)
    - Moderate contextual anomaly or isolated atypical behavior:
      * Unfamiliar device or unusual login hour or 1-2 paced failures.
      * Sensitive action requested, but with normal human delay (80s - 140s), not an automated burst.
      * Moderate action frequency without brute force bursts.
    """
    rng = random.Random(seed)
    events: List[SessionEvent] = []

    # Variant selector
    variant = rng.choice(["new_device_only", "unusual_time_only", "isolated_failures", "paced_security_change"])

    hour = rng.choice([2, 3, 4]) if variant == "unusual_time_only" or rng.random() < 0.3 else rng.choice([8, 11, 13, 19])
    base_time = datetime(2026, 3, 10, hour, rng.randint(0, 50), rng.randint(0, 50), tzinfo=timezone.utc)
    curr_time = base_time

    device = "unfamiliar" if variant in ("new_device_only", "isolated_failures") or rng.random() < 0.5 else "familiar"
    location = "hotel" if rng.random() < 0.4 else "home"

    events.append(SessionEvent.create(
        session_id=session_id,
        user_id=user_id,
        event_type=EventType.SESSION_STARTED.value,
        timestamp_utc=curr_time.isoformat(),
        device_familiarity=device,
        location_context=location,
    ))

    # 1 or 2 failures with moderate human gaps (5s - 12s)
    num_failures = rng.randint(1, 2) if variant == "isolated_failures" else (1 if rng.random() < 0.35 else 0)
    for _ in range(num_failures):
        curr_time += timedelta(seconds=rng.uniform(5.0, 14.0))
        events.append(SessionEvent.create(
            session_id=session_id,
            user_id=user_id,
            event_type=EventType.LOGIN_FAILURE.value,
            timestamp_utc=curr_time.isoformat(),
            success=False,
            device_familiarity=device,
            location_context=location,
        ))

    curr_time += timedelta(seconds=rng.uniform(6.0, 18.0))
    events.append(SessionEvent.create(
        session_id=session_id,
        user_id=user_id,
        event_type=EventType.LOGIN_SUCCESS.value,
        timestamp_utc=curr_time.isoformat(),
        success=True,
        device_familiarity=device,
        location_context=location,
    ))

    # Actions: balance or statement
    curr_time += timedelta(seconds=rng.uniform(10.0, 30.0))
    events.append(SessionEvent.create(
        session_id=session_id,
        user_id=user_id,
        event_type=EventType.BALANCE_VIEWED.value,
        timestamp_utc=curr_time.isoformat(),
        success=True,
        device_familiarity=device,
        location_context=location,
    ))

    # Sensitive action with borderline timing (70s - 110s)
    if variant == "paced_security_change" or rng.random() < 0.5:
        curr_time += timedelta(seconds=rng.uniform(70.0, 110.0))
        act = rng.choice([EventType.PASSWORD_CHANGE_REQUESTED.value, EventType.EMAIL_UPDATE_REQUESTED.value])
        events.append(SessionEvent.create(
            session_id=session_id,
            user_id=user_id,
            event_type=act,
            timestamp_utc=curr_time.isoformat(),
            device_familiarity=device,
            location_context=location,
        ))

    return events, RISK_MEDIUM


def generate_elevated_risk_session(session_id: str, user_id: str, seed: int) -> Tuple[List[SessionEvent], str]:
    """
    Scenario Family: Elevated Risk / Account Takeover Indicators (Target: high)
    - Repeated rapid failed login attempts (bursts with min intervals < 3s, brute-force profile).
    - Unfamiliar device and/or contextual anomaly.
    - Rapid sensitive action requests within <= 60 seconds post-login.
    - High action burst frequency.
    """
    rng = random.Random(seed)
    events: List[SessionEvent] = []

    hour = rng.choice([1, 2, 3, 4, 14, 23])
    base_time = datetime(2026, 3, 10, hour, rng.randint(0, 50), rng.randint(0, 50), tzinfo=timezone.utc)
    curr_time = base_time

    device = "unfamiliar"
    location = rng.choice(["unknown_vpn", "foreign_asn", "datacenter_proxy"])

    events.append(SessionEvent.create(
        session_id=session_id,
        user_id=user_id,
        event_type=EventType.SESSION_STARTED.value,
        timestamp_utc=curr_time.isoformat(),
        device_familiarity=device,
        location_context=location,
    ))

    # Rapid failed login attempts (3 to 6 failures, 0.8s to 3.5s gaps)
    num_failures = rng.randint(3, 6)
    for _ in range(num_failures):
        curr_time += timedelta(seconds=rng.uniform(0.8, 3.2))
        events.append(SessionEvent.create(
            session_id=session_id,
            user_id=user_id,
            event_type=EventType.LOGIN_FAILURE.value,
            timestamp_utc=curr_time.isoformat(),
            success=False,
            device_familiarity=device,
            location_context=location,
        ))

    # Breached / cracked login success immediately after
    curr_time += timedelta(seconds=rng.uniform(1.0, 4.0))
    events.append(SessionEvent.create(
        session_id=session_id,
        user_id=user_id,
        event_type=EventType.LOGIN_SUCCESS.value,
        timestamp_utc=curr_time.isoformat(),
        success=True,
        device_familiarity=device,
        location_context=location,
    ))

    # Immediate sensitive actions in rapid burst (within 5s - 35s of login)
    curr_time += timedelta(seconds=rng.uniform(4.0, 15.0))
    events.append(SessionEvent.create(
        session_id=session_id,
        user_id=user_id,
        event_type=EventType.PASSWORD_CHANGE_REQUESTED.value,
        timestamp_utc=curr_time.isoformat(),
        device_familiarity=device,
        location_context=location,
    ))

    if rng.random() < 0.6:
        curr_time += timedelta(seconds=rng.uniform(2.0, 10.0))
        events.append(SessionEvent.create(
            session_id=session_id,
            user_id=user_id,
            event_type=EventType.EMAIL_UPDATE_REQUESTED.value,
            timestamp_utc=curr_time.isoformat(),
            device_familiarity=device,
            location_context=location,
        ))

    return events, RISK_HIGH


def generate_synthetic_dataset(
    n_samples: int = 1200,
    random_seed: int = 42,
    output_path: Path = SYNTHETIC_DATASET_PATH,
) -> pd.DataFrame:
    """
    Generates synthetic session event histories, derives features using
    extract_session_features, and writes them to a CSV dataset.
    """
    rng = random.Random(random_seed)
    records = []

    # Target class distribution: ~50% Low, ~30% Medium, ~20% High
    n_low = int(n_samples * 0.50)
    n_med = int(n_samples * 0.30)
    n_high = n_samples - n_low - n_med

    session_counter = 1

    # Routine
    for i in range(n_low):
        sid = f"sess_low_{session_counter:04d}"
        uid = f"user_{rng.randint(100, 150):03d}"
        seed = random_seed + session_counter
        events, label = generate_routine_session(sid, uid, seed)
        feats = extract_session_features(events)
        row = {"session_id": sid, "scenario_family": "routine", **feats, "label": label}
        records.append(row)
        session_counter += 1

    # Ambiguous
    for i in range(n_med):
        sid = f"sess_med_{session_counter:04d}"
        uid = f"user_{rng.randint(100, 150):03d}"
        seed = random_seed + session_counter
        events, label = generate_ambiguous_session(sid, uid, seed)
        feats = extract_session_features(events)
        row = {"session_id": sid, "scenario_family": "ambiguous", **feats, "label": label}
        records.append(row)
        session_counter += 1

    # Elevated Risk
    for i in range(n_high):
        sid = f"sess_high_{session_counter:04d}"
        uid = f"user_{rng.randint(100, 150):03d}"
        seed = random_seed + session_counter
        events, label = generate_elevated_risk_session(sid, uid, seed)
        feats = extract_session_features(events)
        row = {"session_id": sid, "scenario_family": "elevated_risk", **feats, "label": label}
        records.append(row)
        session_counter += 1

    df = pd.DataFrame(records)

    # Shuffle rows deterministically
    df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Synthetic dataset saved to {output_path} with {len(df)} rows.")
    print("Class distribution:")
    print(df["label"].value_counts(normalize=True))

    return df


if __name__ == "__main__":
    generate_synthetic_dataset()
