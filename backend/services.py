"""
SentinelFlow Backend Application Services.
Manages session lifecycle, event recording, backend-enforced policy verification,
and demonstration scenarios.
"""

from datetime import datetime, timezone
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple
import uuid

from backend.database import (
    get_db_connection,
    get_session_events,
    get_session_info,
    insert_event,
    set_session_verified,
)
from config import DATABASE_PATH
from src.event_schema import EventType, SessionEvent
from src.inference import RiskInferenceEngine


class SessionService:
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self.inference_engine = RiskInferenceEngine.get_instance()

    def start_demo_session(
        self,
        username: str = "alex_demo",
        device_familiarity: str = "familiar",
        location_context: str = "home",
        simulate_login_failure: bool = False,
    ) -> Dict[str, Any]:
        """Starts or resets a demo session, recording login attempts and outcomes."""
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT user_id, full_name, account_number, balance FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        if not user:
            # Fallback to first user
            cur.execute("SELECT user_id, full_name, account_number, balance FROM users LIMIT 1")
            user = cur.fetchone()

        user_id = user["user_id"]
        session_id = f"sess-{uuid.uuid4().hex[:10]}"
        now_utc = datetime.now(timezone.utc).isoformat()

        # Insert session
        cur.execute(
            """
            INSERT INTO sessions (session_id, user_id, is_verified, device_familiarity, location_context, created_at)
            VALUES (?, ?, 0, ?, ?, ?)
            """,
            (session_id, user_id, device_familiarity, location_context, now_utc),
        )
        conn.commit()
        conn.close()

        # Record session_started event
        ev_start = SessionEvent.create(
            session_id=session_id,
            user_id=user_id,
            event_type=EventType.SESSION_STARTED.value,
            timestamp_utc=now_utc,
            device_familiarity=device_familiarity,
            location_context=location_context,
            metadata={"username": username},
        )
        insert_event(ev_start, self.db_path)

        if simulate_login_failure:
            # Record failed login attempt
            ev_fail = SessionEvent.create(
                session_id=session_id,
                user_id=user_id,
                event_type=EventType.LOGIN_FAILURE.value,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                success=False,
                device_familiarity=device_familiarity,
                location_context=location_context,
                metadata={"reason": "incorrect_password_simulated"},
            )
            insert_event(ev_fail, self.db_path)

        # Successful login
        ev_login = SessionEvent.create(
            session_id=session_id,
            user_id=user_id,
            event_type=EventType.LOGIN_SUCCESS.value,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            success=True,
            device_familiarity=device_familiarity,
            location_context=location_context,
            metadata={"auth_method": "demo_credentials"},
        )
        insert_event(ev_login, self.db_path)

        return self.get_session_summary(session_id)

    def record_user_event(
        self,
        session_id: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> Dict[str, Any]:
        """Records an event and calculates the real-time risk assessment."""
        session_info = get_session_info(session_id, self.db_path)
        if not session_info:
            raise ValueError(f"Session {session_id} not found.")

        event = SessionEvent.create(
            session_id=session_id,
            user_id=session_info["user_id"],
            event_type=event_type,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            success=success,
            device_familiarity=session_info["device_familiarity"],
            location_context=session_info["location_context"],
            metadata=metadata or {},
        )
        insert_event(event, self.db_path)

        return self.get_risk_assessment(session_id, target_action=event_type)

    def get_risk_assessment(
        self,
        session_id: str,
        target_action: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Recalculates behavioral features from stored events and runs model inference."""
        session_info = get_session_info(session_id, self.db_path)
        if not session_info:
            raise ValueError(f"Session {session_id} not found.")

        events = get_session_events(session_id, self.db_path)
        is_verified = bool(session_info.get("is_verified", False))

        assessment = self.inference_engine.assess_session(
            events=events,
            target_action=target_action,
            is_verified_in_session=is_verified,
        )
        assessment["session_id"] = session_id
        assessment["is_verified"] = is_verified
        return assessment

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Returns session metadata, event timeline, and latest risk status."""
        session_info = get_session_info(session_id, self.db_path)
        if not session_info:
            raise ValueError(f"Session {session_id} not found.")

        events = get_session_events(session_id, self.db_path)
        assessment = self.get_risk_assessment(session_id)

        return {
            "session": session_info,
            "events": [e.to_dict() for e in events],
            "risk_assessment": assessment,
        }

    def request_verification(self, session_id: str) -> Dict[str, Any]:
        """Issues a simulated OTP/step-up verification challenge."""
        session_info = get_session_info(session_id, self.db_path)
        if not session_info:
            raise ValueError(f"Session {session_id} not found.")

        challenge_id = f"chal-{uuid.uuid4().hex[:8]}"
        demo_code = "123456"  # Standard deterministic hackathon demo code
        now_utc = datetime.now(timezone.utc).isoformat()

        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO verifications (challenge_id, session_id, code, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (challenge_id, session_id, demo_code, now_utc),
        )
        conn.commit()
        conn.close()

        # Record step-up requested event
        ev_challenge = SessionEvent.create(
            session_id=session_id,
            user_id=session_info["user_id"],
            event_type=EventType.STEP_UP_REQUESTED.value,
            timestamp_utc=now_utc,
            device_familiarity=session_info["device_familiarity"],
            location_context=session_info["location_context"],
            metadata={"challenge_id": challenge_id},
        )
        insert_event(ev_challenge, self.db_path)

        return {
            "challenge_id": challenge_id,
            "demo_code": demo_code,
            "message": "Simulated OTP challenge generated. Enter code '123456' to verify.",
            "instructions": "Demonstration only. No real SMS/MFA sent.",
        }

    def complete_verification(self, session_id: str, challenge_code: str) -> Dict[str, Any]:
        """Validates verification code and unlocks sensitive operations on the session."""
        session_info = get_session_info(session_id, self.db_path)
        if not session_info:
            raise ValueError(f"Session {session_id} not found.")

        now_utc = datetime.now(timezone.utc).isoformat()
        is_success = (challenge_code.strip() == "123456")

        if is_success:
            set_session_verified(session_id, True, self.db_path)
            ev = SessionEvent.create(
                session_id=session_id,
                user_id=session_info["user_id"],
                event_type=EventType.STEP_UP_SUCCEEDED.value,
                timestamp_utc=now_utc,
                success=True,
                device_familiarity=session_info["device_familiarity"],
                location_context=session_info["location_context"],
                metadata={"verification_type": "simulated_sms_otp"},
            )
            insert_event(ev, self.db_path)
            msg = "Verification successful! Sensitive actions unlocked for this session."
        else:
            ev = SessionEvent.create(
                session_id=session_id,
                user_id=session_info["user_id"],
                event_type=EventType.STEP_UP_FAILED.value,
                timestamp_utc=now_utc,
                success=False,
                device_familiarity=session_info["device_familiarity"],
                location_context=session_info["location_context"],
                metadata={"reason": "invalid_code"},
            )
            insert_event(ev, self.db_path)
            msg = "Verification failed: Incorrect code."

        return {
            "success": is_success,
            "message": msg,
            "risk_assessment": self.get_risk_assessment(session_id),
        }

    def load_preset_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """
        Loads one of the 3 canonical repeatable demonstration scenarios:
        'A' - Routine session
        'B' - Elevated-risk pattern
        'C' - Ambiguous session
        """
        from datetime import timedelta
        scenario_key = scenario_name.strip().upper()

        if scenario_key == "A":
            # Scenario A: Routine session
            summary = self.start_demo_session(
                username="alex_demo",
                device_familiarity="familiar",
                location_context="home",
                simulate_login_failure=False,
            )
            sid = summary["session"]["session_id"]
            # Perform ordinary actions
            self.record_user_event(sid, EventType.BALANCE_VIEWED.value, metadata={"amount": 14850.50})
            self.record_user_event(sid, EventType.STATEMENT_DOWNLOADED.value, metadata={"statement_month": "February 2026"})
            return self.get_session_summary(sid)

        elif scenario_key == "B":
            # Scenario B: Elevated-risk pattern
            # Unfamiliar device + repeated rapid failed attempts + crack login + sensitive request
            conn = get_db_connection(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE username = 'alex_demo'")
            user_id = cur.fetchone()["user_id"]
            sid = f"sess-scenario-B-{uuid.uuid4().hex[:6]}"
            t0 = datetime.now(timezone.utc)

            cur.execute(
                """
                INSERT INTO sessions (session_id, user_id, is_verified, device_familiarity, location_context, created_at)
                VALUES (?, ?, 0, 'unfamiliar', 'foreign_datacenter_proxy', ?)
                """,
                (sid, user_id, t0.isoformat()),
            )
            conn.commit()
            conn.close()

            # Rapid failed login burst
            insert_event(SessionEvent.create(sid, user_id, EventType.SESSION_STARTED.value, t0.isoformat(), device_familiarity="unfamiliar", location_context="foreign_datacenter_proxy"), self.db_path)
            insert_event(SessionEvent.create(sid, user_id, EventType.LOGIN_FAILURE.value, (t0 + timedelta(seconds=1.1)).isoformat(), success=False, device_familiarity="unfamiliar", location_context="foreign_datacenter_proxy"), self.db_path)
            insert_event(SessionEvent.create(sid, user_id, EventType.LOGIN_FAILURE.value, (t0 + timedelta(seconds=2.4)).isoformat(), success=False, device_familiarity="unfamiliar", location_context="foreign_datacenter_proxy"), self.db_path)
            insert_event(SessionEvent.create(sid, user_id, EventType.LOGIN_FAILURE.value, (t0 + timedelta(seconds=3.6)).isoformat(), success=False, device_familiarity="unfamiliar", location_context="foreign_datacenter_proxy"), self.db_path)
            insert_event(SessionEvent.create(sid, user_id, EventType.LOGIN_FAILURE.value, (t0 + timedelta(seconds=4.8)).isoformat(), success=False, device_familiarity="unfamiliar", location_context="foreign_datacenter_proxy"), self.db_path)
            insert_event(SessionEvent.create(sid, user_id, EventType.LOGIN_SUCCESS.value, (t0 + timedelta(seconds=6.5)).isoformat(), success=True, device_familiarity="unfamiliar", location_context="foreign_datacenter_proxy"), self.db_path)

            # Sensitive action requested immediately (< 15 seconds after login)
            insert_event(SessionEvent.create(sid, user_id, EventType.PASSWORD_CHANGE_REQUESTED.value, (t0 + timedelta(seconds=12.0)).isoformat(), device_familiarity="unfamiliar", location_context="foreign_datacenter_proxy"), self.db_path)
            return self.get_session_summary(sid)

        elif scenario_key == "C":
            # Scenario C: Ambiguous session
            # Unfamiliar device context, but normal pacing, no rapid burst, harmless actions
            summary = self.start_demo_session(
                username="alex_demo",
                device_familiarity="unfamiliar",
                location_context="hotel_wifi",
                simulate_login_failure=False,
            )
            sid = summary["session"]["session_id"]
            self.record_user_event(sid, EventType.BALANCE_VIEWED.value, metadata={"amount": 14850.50})
            return self.get_session_summary(sid)

        else:
            raise ValueError(f"Unknown scenario '{scenario_name}'. Expected A, B, or C.")
