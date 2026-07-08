"""Permission and approval primitives for Lily tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PermissionLevel(str, Enum):
    """Coarse risk level for a tool action."""

    READ = "read"
    NETWORK = "network"
    WRITE = "write"
    EXECUTE = "execute"
    DESTRUCTIVE = "destructive"
    EXTERNAL_SEND = "external_send"


@dataclass(slots=True)
class PermissionRequest:
    """A permission request shown to the user or API client."""

    action: str
    reason: str
    risk_level: PermissionLevel
    affected_files: list[str] = field(default_factory=list)
    tool_name: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PermissionDecision:
    """A caller decision for a requested action."""

    approved: bool
    always_allow: bool = False
    reason: str = ""


class PermissionManager:
    """Central guardrail layer between reasoning and tool execution."""

    def __init__(self, auto_approve_read: bool = True, trusted_mode: bool = False):
        self.auto_approve_read = auto_approve_read
        self.trusted_mode = trusted_mode
        self._always_allow: set[tuple[str, PermissionLevel]] = set()

    def evaluate(
        self,
        request: PermissionRequest,
        approvals: dict[str, PermissionDecision] | None = None,
    ) -> PermissionDecision:
        key = (request.tool_name or request.action, request.risk_level)
        if key in self._always_allow:
            return PermissionDecision(approved=True, always_allow=True, reason="Previously allowed.")

        if request.risk_level in {PermissionLevel.READ, PermissionLevel.NETWORK} and self.auto_approve_read:
            return PermissionDecision(approved=True, reason="Low-risk action.")

        if self.trusted_mode and request.risk_level in {
            PermissionLevel.READ,
            PermissionLevel.NETWORK,
            PermissionLevel.WRITE,
            PermissionLevel.EXECUTE,
        }:
            return PermissionDecision(approved=True, always_allow=True, reason="Trusted agent mode.")

        approval_key = self._approval_key(request)
        if approvals and approval_key in approvals:
            decision = approvals[approval_key]
            if decision.approved and decision.always_allow:
                self._always_allow.add(key)
            return decision

        return PermissionDecision(approved=False, reason="Approval required.")

    @staticmethod
    def _approval_key(request: PermissionRequest) -> str:
        return f"{request.tool_name or request.action}:{request.risk_level.value}:{request.action}"

    @classmethod
    def approval_key(cls, request: PermissionRequest) -> str:
        return cls._approval_key(request)
