from __future__ import annotations

from mud.command_collision_policy import install_command_collision_policy


def install_runtime_remediation(player_session_class) -> None:
    """Install audit remediations that must sit outside the assembled stack."""

    install_command_collision_policy(player_session_class)
    player_session_class._runtime_remediation_installed = True
