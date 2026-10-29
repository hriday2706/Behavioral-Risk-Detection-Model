"""
SentinelFlow Flask API Routes.
Exposes REST endpoints for session recording, action gating, risk assessment,
verification, and demo scenarios.
"""

import json
from flask import Blueprint, jsonify, request
from backend.services import SessionService
from config import MODEL_METADATA_PATH
from src.event_schema import EventType

api_bp = Blueprint("api", __name__, url_prefix="/api")
service = SessionService()

# Global current demo session pointer for easy demo interaction
_current_session_id = None


def get_active_session_id() -> str:
    global _current_session_id
    if not _current_session_id:
        # Auto-initialize a default session if none exists
        summary = service.start_demo_session(username="alex_demo")
        _current_session_id = summary["session"]["session_id"]
    return _current_session_id


@api_bp.route("/demo/login", methods=["POST"])
def demo_login():
    """Start a demo session with configured context."""
    global _current_session_id
    data = request.get_json() or {}
    username = data.get("username", "alex_demo")
    device_familiarity = data.get("device_familiarity", "familiar")
    location_context = data.get("location_context", "home")
    simulate_failure = bool(data.get("simulate_login_failure", False))

    summary = service.start_demo_session(
        username=username,
        device_familiarity=device_familiarity,
        location_context=location_context,
        simulate_login_failure=simulate_failure,
    )
    _current_session_id = summary["session"]["session_id"]
    return jsonify(summary), 200


@api_bp.route("/events", methods=["POST"])
def record_event():
    """Record a custom validated event."""
    data = request.get_json() or {}
    session_id = data.get("session_id") or get_active_session_id()
    event_type = data.get("event_type")
    metadata = data.get("metadata", {})
    success = bool(data.get("success", True))

    if not event_type:
        return jsonify({"error": "event_type is required"}), 400

    try:
        assessment = service.record_user_event(
            session_id=session_id,
            event_type=event_type,
            metadata=metadata,
            success=success,
        )
        return jsonify(assessment), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@api_bp.route("/session/current", methods=["GET"])
def get_current_session():
    """Return active demo session summary and activity timeline."""
    sid = request.args.get("session_id") or get_active_session_id()
    try:
        summary = service.get_session_summary(sid)
        return jsonify(summary), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 404


@api_bp.route("/risk/current", methods=["GET"])
def get_current_risk():
    """Return latest risk prediction, tree path explanation, and policy status."""
    sid = request.args.get("session_id") or get_active_session_id()
    try:
        assessment = service.get_risk_assessment(sid)
        return jsonify(assessment), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 404


@api_bp.route("/actions/balance", methods=["POST"])
def action_balance():
    """Simulate viewing account balance (non-sensitive action)."""
    sid = request.args.get("session_id") or get_active_session_id()
    service.record_user_event(sid, EventType.BALANCE_VIEWED.value, metadata={"view": "summary"})
    summary = service.get_session_summary(sid)
    return jsonify({
        "status": "success",
        "action": "balance_viewed",
        "balance": summary["session"]["balance"],
        "account_number": summary["session"]["account_number"],
        "risk_assessment": summary["risk_assessment"],
    }), 200


@api_bp.route("/actions/statement", methods=["POST"])
def action_statement():
    """Simulate downloading account statement (non-sensitive action)."""
    sid = request.args.get("session_id") or get_active_session_id()
    service.record_user_event(sid, EventType.STATEMENT_DOWNLOADED.value, metadata={"format": "PDF"})
    summary = service.get_session_summary(sid)
    return jsonify({
        "status": "success",
        "action": "statement_downloaded",
        "document_name": "SentinelBank_Statement_Q1_2026.pdf",
        "risk_assessment": summary["risk_assessment"],
    }), 200


@api_bp.route("/actions/security-change", methods=["POST"])
def action_security_change():
    """
    Enforce backend security policy on sensitive actions (password/email update).
    If high risk and unverified, blocks action and requires step-up verification.
    """
    sid = request.args.get("session_id") or get_active_session_id()
    data = request.get_json() or {}
    change_type = data.get("change_type", "password")  # "password" or "email"

    event_type = (
        EventType.PASSWORD_CHANGE_REQUESTED.value
        if change_type == "password"
        else EventType.EMAIL_UPDATE_REQUESTED.value
    )

    # 1. Record the action request event in database
    service.record_user_event(sid, event_type, metadata={"target": change_type})

    # 2. Evaluate backend risk policy
    assessment = service.get_risk_assessment(sid, target_action=event_type)
    policy = assessment["risk_policy"]

    if not policy["action_allowed"]:
        return jsonify({
            "status": "blocked",
            "message": policy["message"],
            "requires_step_up": True,
            "policy": policy,
            "risk_assessment": assessment,
        }), 403

    return jsonify({
        "status": "success",
        "message": f"Security change ({change_type}) completed successfully.",
        "requires_step_up": False,
        "policy": policy,
        "risk_assessment": assessment,
    }), 200


@api_bp.route("/verification/request", methods=["POST"])
def request_verification_challenge():
    """Generate simulated verification challenge."""
    sid = request.args.get("session_id") or get_active_session_id()
    res = service.request_verification(sid)
    return jsonify(res), 200


@api_bp.route("/verification/complete", methods=["POST"])
def complete_verification_challenge():
    """Verify challenge code and unlock sensitive actions."""
    data = request.get_json() or {}
    sid = data.get("session_id") or get_active_session_id()
    code = data.get("code", "")
    res = service.complete_verification(sid, code)
    status_code = 200 if res["success"] else 400
    return jsonify(res), status_code


@api_bp.route("/demo/reset", methods=["POST"])
def demo_reset():
    """Reset demo session to a clean baseline."""
    global _current_session_id
    summary = service.start_demo_session(username="alex_demo")
    _current_session_id = summary["session"]["session_id"]
    return jsonify({
        "status": "reset",
        "message": "Demo session reset to clean state.",
        "summary": summary,
    }), 200


@api_bp.route("/demo/load-scenario", methods=["POST"])
def load_scenario():
    """Load one of the predefined presentation scenarios (A, B, C)."""
    global _current_session_id
    data = request.get_json() or {}
    scenario = data.get("scenario", "A")
    try:
        summary = service.load_preset_scenario(scenario)
        _current_session_id = summary["session"]["session_id"]
        return jsonify({
            "status": "loaded",
            "scenario": scenario,
            "summary": summary,
        }), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@api_bp.route("/model/info", methods=["GET"])
def model_info():
    """Return model metadata, features, metrics, and baseline comparisons."""
    if not MODEL_METADATA_PATH.exists():
        return jsonify({"error": "Model metadata not found."}), 404
    with open(MODEL_METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return jsonify(meta), 200
