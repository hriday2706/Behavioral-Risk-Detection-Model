"""
SentinelFlow Risk Policy & Step-Up Verification Engine.
Applies security rules based on model risk category, action sensitivity,
and session verification status.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from config import (
    DEFAULT_POLICY_MAPPING,
    POLICY_ACTION_ALLOW,
    POLICY_ACTION_REQUIRE_VERIFICATION,
    POLICY_ACTION_WARN,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
)
from src.event_schema import SENSITIVE_ACTIONS


@dataclass
class PolicyDecision:
    action_allowed: bool
    status: str
    message: str
    requires_step_up: bool
    policy_version: str = "demo-policy-v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_allowed": self.action_allowed,
            "status": self.status,
            "message": self.message,
            "requires_step_up": self.requires_step_up,
            "policy_version": self.policy_version,
        }


class RiskPolicyEngine:
    def __init__(
        self,
        strict_medium_verification: bool = False,
        policy_version: str = "demo-policy-v1"
    ):
        self.strict_medium_verification = strict_medium_verification
        self.policy_version = policy_version

    def evaluate(
        self,
        predicted_class: str,
        event_type: str,
        is_verified_in_session: bool = False,
    ) -> PolicyDecision:
        """
        Determines whether the requested action is permitted based on risk level,
        sensitivity of the action, and existing step-up verification status.
        """
        is_sensitive = event_type in SENSITIVE_ACTIONS

        # If action is non-sensitive (e.g. balance check, statement download)
        if not is_sensitive:
            if predicted_class == RISK_HIGH:
                return PolicyDecision(
                    action_allowed=True,
                    status=POLICY_ACTION_WARN,
                    message="Routine action allowed, but high-risk behavioral pattern is flagged.",
                    requires_step_up=False,
                    policy_version=self.policy_version,
                )
            elif predicted_class == RISK_MEDIUM:
                return PolicyDecision(
                    action_allowed=True,
                    status=POLICY_ACTION_ALLOW,
                    message="Action allowed under standard monitoring.",
                    requires_step_up=False,
                    policy_version=self.policy_version,
                )
            else:
                return PolicyDecision(
                    action_allowed=True,
                    status=POLICY_ACTION_ALLOW,
                    message="Action permitted.",
                    requires_step_up=False,
                    policy_version=self.policy_version,
                )

        # Action is sensitive (password change, email update)
        if is_verified_in_session:
            return PolicyDecision(
                action_allowed=True,
                status=POLICY_ACTION_ALLOW,
                message="Sensitive action permitted: Identity verified via step-up verification.",
                requires_step_up=False,
                policy_version=self.policy_version,
            )

        if predicted_class == RISK_HIGH:
            return PolicyDecision(
                action_allowed=False,
                status=POLICY_ACTION_REQUIRE_VERIFICATION,
                message="High-risk session detected. Sensitive security action blocked pending step-up verification.",
                requires_step_up=True,
                policy_version=self.policy_version,
            )

        if predicted_class == RISK_MEDIUM:
            if self.strict_medium_verification:
                return PolicyDecision(
                    action_allowed=False,
                    status=POLICY_ACTION_REQUIRE_VERIFICATION,
                    message="Ambiguous/medium risk session. Strict policy requires step-up verification.",
                    requires_step_up=True,
                    policy_version=self.policy_version,
                )
            else:
                return PolicyDecision(
                    action_allowed=True,
                    status=POLICY_ACTION_WARN,
                    message="Medium risk flagged. Action allowed with monitoring warning.",
                    requires_step_up=False,
                    policy_version=self.policy_version,
                )

        # Low risk sensitive action
        return PolicyDecision(
            action_allowed=True,
            status=POLICY_ACTION_ALLOW,
            message="Sensitive action permitted for routine low-risk session.",
            requires_step_up=False,
            policy_version=self.policy_version,
        )
