from __future__ import annotations

import asyncio

from mud.alpha_hardening import (
    hardening_readiness,
    install_alpha_hardening_runtime,
    recent_observations,
    record_observation,
)
from mud.alpha_ux import alpha_ux_summary
from mud.production_hardening import (
    active_session_snapshot,
    alpha_allowlist,
    alpha_gate_enabled,
    audit_inventory_integrity,
    combat_summary,
    create_database_backup,
    database_integrity,
    last_backup_row,
)
from mud.staff_control import _has_role, _role_for, _staff_mode


async def _delegate(session, previous_prompt, command: str) -> None:
    had = "prompt" in session.__dict__
    old = session.__dict__.get("prompt")

    async def replay(_text: str):
        return command

    session.prompt = replay
    try:
        await previous_prompt(session)
    finally:
        if had:
            session.prompt = old
        else:
            session.__dict__.pop("prompt", None)


def _authorized(session) -> bool:
    return _staff_mode(session) and _has_role(session, "admin")


async def _health(session) -> None:
    healthy, integrity = database_integrity(session.database)
    audit = audit_inventory_integrity(session.database)
    backup = last_backup_row(session.database)
    summary = combat_summary(session.database, 24)
    ux = alpha_ux_summary(session.database, 24)
    sessions = active_session_snapshot()

    await session.send("\r\n--- Production Health ---\r\n")
    await session.send(
        f"Database integrity : {'OK' if healthy else 'FAILED'} ({'; '.join(integrity)})\r\n"
        f"Inventory audit    : {'OK' if audit.healthy else 'ATTENTION'}\r\n"
        f"Active sessions    : {len(sessions)}\r\n"
        f"Closed alpha gate  : {'ON' if alpha_gate_enabled() else 'OFF'}\r\n"
    )
    if backup is None:
        await session.send("Last backup        : none recorded\r\n")
    else:
        await session.send(
            f"Last backup        : {backup['created_at']} ({backup['reason']}, {int(backup['size_bytes'])} bytes, {backup['integrity']})\r\n"
        )
    await session.send(
        f"24h combat sample  : {summary.fights} completed fights, {summary.victories} victories, "
        f"{summary.deaths} deaths, average {summary.average_seconds:.1f}s\r\n"
        f"24h UX sample      : {int(ux.get('events_command', 0))} commands, "
        f"{int(ux.get('stalled_without_movement', 0))} characters with 12+ commands and no movement, "
        f"{int(ux.get('reports_stuck', 0))} stuck reports\r\n"
    )
    if not audit.healthy:
        await session.send(
            "Inventory warnings : "
            f"FK {audit.foreign_key_violations}, nonpositive {audit.nonpositive_item_rows}, "
            f"unknown {audit.unknown_item_rows}, equipped-missing {audit.equipped_missing_rows}, "
            f"provenance {audit.provenance_mismatches}\r\n"
        )


async def _item_audit(session) -> None:
    audit = audit_inventory_integrity(session.database)
    await session.send("\r\n--- Item / Economy Integrity Audit ---\r\n")
    await session.send(
        f"Foreign-key violations : {audit.foreign_key_violations}\r\n"
        f"Nonpositive item rows   : {audit.nonpositive_item_rows}\r\n"
        f"Unknown item rows       : {audit.unknown_item_rows}\r\n"
        f"Equipped but not owned  : {audit.equipped_missing_rows}\r\n"
        f"Provenance mismatches   : {audit.provenance_mismatches}\r\n"
    )
    if audit.details:
        await session.send("Details (read-only; nothing was changed):\r\n")
        for line in audit.details[:30]:
            await session.send(f"  - {line}\r\n")
    else:
        await session.send("No item-integrity problems detected.\r\n")


async def _combat_metrics(session, hours: int) -> None:
    summary = combat_summary(session.database, hours)
    await session.send(
        f"\r\n--- Combat Metrics: last {summary.hours}h ---\r\n"
        f"Completed fights : {summary.fights}\r\n"
        f"Victories        : {summary.victories}\r\n"
        f"Deaths           : {summary.deaths}\r\n"
        f"Average duration : {summary.average_seconds:.1f}s\r\n"
        f"Average level    : {summary.average_level:.1f}\r\n"
        "Use these numbers with actual player observation; they are tuning evidence, not an automatic balance target.\r\n"
    )


async def _ux_metrics(session, hours: int) -> None:
    summary = alpha_ux_summary(session.database, hours)
    await session.send(
        f"\r\n--- Alpha UX Metrics: last {int(summary['hours'])}h ---\r\n"
        f"Commands observed       : {int(summary.get('events_command', 0))}\r\n"
        f"Average command latency : {float(summary.get('average_command_latency_ms', 0.0)):.1f} ms\r\n"
        f"Room changes            : {int(summary.get('events_room_change', 0))}\r\n"
        f"Inventory gains         : {int(summary.get('events_inventory_gain', 0))}\r\n"
        f"Quest state changes     : {int(summary.get('events_quest_state_change', 0))}\r\n"
        f"Stalled before movement : {int(summary.get('stalled_without_movement', 0))}\r\n"
        f"BUG reports             : {int(summary.get('reports_bug', 0))}\r\n"
        f"FEEDBACK reports        : {int(summary.get('reports_feedback', 0))}\r\n"
        f"STUCK reports           : {int(summary.get('reports_stuck', 0))}\r\n"
        "Command telemetry stores command families, not SAY/TELL/CHAT message contents. Use this as friction evidence, then reproduce the actual experience manually.\r\n"
    )


async def _hardening_report(session, hours: int) -> None:
    from mud.room_runtime import WORLD

    report = hardening_readiness(session.database, WORLD, hours)
    await session.send(f"\r\n--- 1-40 Alpha Hardening Gate: {report.status} ---\r\n")
    await session.send(
        f"First-ten matrix : {report.first_ten.walkable_starts}/{report.first_ten.combinations} walkable starts; "
        f"{report.first_ten.level_ten_kits}/{report.first_ten.combinations} level-10 class kits\r\n"
        f"Gear curve       : {'GREEN' if report.gear.ready else 'REVIEW'}; tier medians "
        + ", ".join(f"L{point.checkpoint}=T{point.tier}:{point.median_power:.1f}" for point in report.gear.checkpoints)
        + "\r\n"
        f"Solo combat      : {report.combat.solo_cells_ready}/{report.combat.solo_cells_total} class/level cells have at least 5 real fights\r\n"
        f"Group combat     : {report.combat.group_bands_ready}/{report.combat.group_bands_total} level bands have at least 3 real party fights\r\n"
        f"Outside cohort   : {report.playtest.meaningful_testers}/20 meaningful testers; "
        f"{report.playtest.race_class_combinations_seen}/40 race/class combinations seen\r\n"
        f"Friction reports : {report.playtest.stuck_reports} STUCK, {report.playtest.bug_reports} BUG, "
        f"{report.playtest.observations} staff observations\r\n"
    )
    if report.first_ten.problems:
        await session.send("First-ten problems:\r\n")
        for problem in report.first_ten.problems[:20]:
            await session.send(f"  - {problem}\r\n")
    if report.gear.catalog_problems:
        await session.send("Gear-curve review:\r\n")
        for problem in report.gear.catalog_problems[:20]:
            await session.send(f"  - {problem}\r\n")
    if report.combat.warnings:
        await session.send("Combat review:\r\n")
        for warning in report.combat.warnings[:20]:
            await session.send(f"  - {warning}\r\n")
    if not report.ready_for_41_50:
        await session.send(
            "Expansion gate remains closed. Keep polishing 1-40 until static checks are green, "
            "all class/level combat cells and group bands have real samples, and at least 20 outside testers complete a meaningful session.\r\n"
        )
    else:
        await session.send("Hardening evidence is complete enough to begin authored 41-50 work without skipping the alpha pass.\r\n")


async def _hardening_note(session, payload: str) -> None:
    parts = payload.strip().split(maxsplit=1)
    if len(parts) != 2:
        await session.send("Usage: STAFF HARDENING NOTE <onboarding|combat|gear|group|navigation|story|other> <observation>\r\n")
        return
    category, note = parts
    try:
        record_observation(session.database, category, note)
    except ValueError as exc:
        await session.send(f"{exc}\r\n")
        return
    await session.send("Hardening observation saved. Record what the player did, not what you coached them to do.\r\n")


async def _hardening_notes(session, hours: int) -> None:
    rows = recent_observations(session.database, hours)
    await session.send(f"\r\n--- Hardening Observations: last {hours}h ---\r\n")
    if not rows:
        await session.send("No staff observations recorded in this window.\r\n")
        return
    for row in rows:
        await session.send(f"{row['created_at']} [{row['category'].upper()}] {row['note']}\r\n")


async def _sessions(session) -> None:
    rows = active_session_snapshot()
    await session.send("\r\n--- Authenticated Sessions ---\r\n")
    if not rows:
        await session.send("No authenticated sessions are currently registered.\r\n")
        return
    for account, character, room in rows:
        await session.send(f"{account:<20} {character:<20} {room}\r\n")
    await session.send("One authenticated connection is allowed per account; a new login safely supersedes the older one.\r\n")


async def _alpha(session) -> None:
    allowed = sorted(alpha_allowlist())
    await session.send(
        "\r\n--- Closed Alpha Gate ---\r\n"
        f"Status: {'ENABLED' if allowed else 'DISABLED'}\r\n"
        f"Invited account names: {len(allowed)}\r\n"
        "Configure with MUD_ALPHA_ALLOWLIST as a comma-separated environment variable. The owner account is always allowed.\r\n"
    )


async def _manual_backup(session) -> None:
    await session.send("Starting an online SQLite backup...\r\n")
    try:
        result = await asyncio.to_thread(create_database_backup, session.database, reason="staff")
    except Exception as exc:
        await session.send(f"Backup failed: {type(exc).__name__}: {exc}\r\n")
        return
    await session.send(
        f"Backup complete: {result.path} ({result.size_bytes} bytes, integrity {result.integrity}).\r\n"
    )


def install_production_operator_runtime(player_session_class) -> None:
    """Add quiet, role-gated production diagnostics to the existing staff console."""
    if getattr(player_session_class, "_production_operator_runtime_installed", False):
        return

    # The hardening layer sits immediately outside production combat telemetry so
    # each newly opened combat row can be tagged with the real class, level, race,
    # room, and party size before the staff console summarizes it.
    install_alpha_hardening_runtime(player_session_class)
    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if getattr(self, "character", None) is None:
            await previous_prompt(self)
            return

        prompt = "\r\n" + (self.current_prompt_text() if hasattr(self, "current_prompt_text") else "> ")
        command = await self.prompt(prompt)
        if command is None:
            state = getattr(self, "state", None)
            if state is not None and hasattr(type(state), "DISCONNECTED"):
                self.state = type(state).DISCONNECTED
            return
        normalized = " ".join(command.strip().lower().split())

        production_command = (
            normalized in {"staff health", "staff backup", "staff item audit", "staff sessions", "staff alpha"}
            or normalized.startswith("staff combat")
            or normalized.startswith("staff ux")
            or normalized.startswith("staff hardening")
        )
        if production_command:
            if not _authorized(self):
                await self.send("ADMIN staff mode is required for production controls.\r\n")
                return
            if normalized == "staff health":
                await _health(self)
                return
            if normalized == "staff backup":
                await _manual_backup(self)
                return
            if normalized == "staff item audit":
                await _item_audit(self)
                return
            if normalized == "staff sessions":
                await _sessions(self)
                return
            if normalized == "staff alpha":
                await _alpha(self)
                return
            if normalized.startswith("staff hardening note "):
                await _hardening_note(self, command.strip()[len("staff hardening note "):])
                return
            if normalized == "staff hardening note":
                await _hardening_note(self, "")
                return
            if normalized.startswith("staff hardening notes"):
                parts = normalized.split()
                hours = int(parts[3]) if len(parts) == 4 and parts[3].isdigit() else 24 * 30
                await _hardening_notes(self, hours)
                return
            if normalized.startswith("staff hardening"):
                parts = normalized.split()
                hours = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else 24 * 30
                await _hardening_report(self, hours)
                return
            parts = normalized.split()
            hours = int(parts[2]) if len(parts) == 3 and parts[2].isdigit() else 24
            if normalized.startswith("staff ux"):
                await _ux_metrics(self, hours)
            else:
                await _combat_metrics(self, hours)
            return

        await _delegate(self, previous_prompt, command)
        if normalized in {"staff", "staff help"} and _role_for(self) != "player":
            await self.send(
                "\r\nProduction controls (ADMIN+ in STAFF ON mode):\r\n"
                "STAFF HEALTH - database, inventory, backup, sessions, combat, and UX summary\r\n"
                "STAFF BACKUP - create and validate an online backup immediately\r\n"
                "STAFF ITEM AUDIT - read-only item/provenance invariant scan\r\n"
                "STAFF COMBAT [hours] - combat duration/death evidence for tuning\r\n"
                "STAFF UX [hours] - movement, command latency, friction, and player-report evidence\r\n"
                "STAFF HARDENING [hours] - 1-40 matrix, gear curve, combat/group samples, and outside-playtest gate\r\n"
                "STAFF HARDENING NOTE <category> <text> - record an uncoached playtest observation\r\n"
                "STAFF HARDENING NOTES [hours] - review recent observation notes\r\n"
                "STAFF SESSIONS - authenticated session registry\r\n"
                "STAFF ALPHA - closed-alpha gate status\r\n"
            )

    player_session_class.playing_prompt = playing_prompt
    player_session_class._production_operator_runtime_installed = True
