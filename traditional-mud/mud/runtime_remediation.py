from __future__ import annotations

from mud.canonical_command_help import install_canonical_command_help
from mud.command_collision_policy import install_command_collision_policy
from mud.corpse_loot import install_corpse_loot_runtime
from mud.final_command_telemetry import install_final_command_telemetry


def install_runtime_remediation(player_session_class) -> None:
    """Install audit remediations that must sit outside the assembled stack."""

    # Corpse looting is installed at the final command/combat edge so every
    # existing enemy source, party loot rule, and economy drop table feeds the
    # same persistent corpse system without authored areas having to opt in.
    install_corpse_loot_runtime(player_session_class)
    install_command_collision_policy(player_session_class)
    install_canonical_command_help(player_session_class)
    install_final_command_telemetry(player_session_class)
    player_session_class._runtime_remediation_installed = True
