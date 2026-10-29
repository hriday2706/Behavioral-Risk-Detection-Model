"""
Unit tests for SentinelFlow Risk Policy Engine.
"""

import pytest
from src.risk_policy import RiskPolicyEngine
from src.event_schema import EventType
from config import POLICY_ACTION_ALLOW, POLICY_ACTION_REQUIRE_VERIFICATION, POLICY_ACTION_WARN, RISK_HIGH, RISK_LOW, RISK_MEDIUM


def test_low_risk_policy():
    engine = RiskPolicyEngine()
    # Non-sensitive action
    dec1 = engine.evaluate(RISK_LOW, EventType.BALANCE_VIEWED.value)
    assert dec1.action_allowed is True
    assert dec1.status == POLICY_ACTION_ALLOW

    # Sensitive action
    dec2 = engine.evaluate(RISK_LOW, EventType.PASSWORD_CHANGE_REQUESTED.value)
    assert dec2.action_allowed is True
    assert dec2.requires_step_up is False


def test_high_risk_policy_blocks_sensitive():
    engine = RiskPolicyEngine()
    # Non-sensitive action allowed with warn
    dec1 = engine.evaluate(RISK_HIGH, EventType.BALANCE_VIEWED.value)
    assert dec1.action_allowed is True
    assert dec1.status == POLICY_ACTION_WARN

    # Sensitive action blocked
    dec2 = engine.evaluate(RISK_HIGH, EventType.PASSWORD_CHANGE_REQUESTED.value, is_verified_in_session=False)
    assert dec2.action_allowed is False
    assert dec2.status == POLICY_ACTION_REQUIRE_VERIFICATION
    assert dec2.requires_step_up is True

    # Sensitive action unblocked when verified
    dec3 = engine.evaluate(RISK_HIGH, EventType.PASSWORD_CHANGE_REQUESTED.value, is_verified_in_session=True)
    assert dec3.action_allowed is True
    assert dec3.status == POLICY_ACTION_ALLOW
    assert dec3.requires_step_up is False


def test_medium_risk_policy_modes():
    # Default permissive
    engine_std = RiskPolicyEngine(strict_medium_verification=False)
    dec_std = engine_std.evaluate(RISK_MEDIUM, EventType.EMAIL_UPDATE_REQUESTED.value)
    assert dec_std.action_allowed is True
    assert dec_std.status == POLICY_ACTION_WARN

    # Strict mode
    engine_strict = RiskPolicyEngine(strict_medium_verification=True)
    dec_strict = engine_strict.evaluate(RISK_MEDIUM, EventType.EMAIL_UPDATE_REQUESTED.value)
    assert dec_strict.action_allowed is False
    assert dec_strict.status == POLICY_ACTION_REQUIRE_VERIFICATION
