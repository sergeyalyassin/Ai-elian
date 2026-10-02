from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PermissionProfile(StrEnum):
    STANDARD = "standard"
    UNRESTRICTED = "unrestricted"


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    allowed: bool
    reason: str
    requires_approval: bool = False


class PermissionPolicy:
    """Explicit capability policy; unrestricted mode is an intentional deployment choice."""
    def __init__(self, profile: PermissionProfile | str = PermissionProfile.STANDARD) -> None:
        self.profile = PermissionProfile(profile)

    def decide(self, tool_name: str, arguments: dict) -> PermissionDecision:
        if tool_name in {"file.write", "browser.action"}:
            return PermissionDecision(True, f"{tool_name} allowed by {self.profile} profile")
        if tool_name == "shell.run":
            command = arguments.get("command", [])
            dangerous = {"rm", "git", "curl", "wget", "ssh", "chmod", "chown", "docker"}
            if self.profile is PermissionProfile.UNRESTRICTED:
                return PermissionDecision(True, "shell command allowed by explicit unrestricted profile")
            if command and command[0] in dangerous:
                return PermissionDecision(False, "sensitive shell command requires approval or unrestricted profile", True)
            return PermissionDecision(True, "bounded local shell command allowed")
        return PermissionDecision(False, f"unregistered tool: {tool_name}")
