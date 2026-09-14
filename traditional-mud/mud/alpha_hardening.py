from __future__ import annotations

import json
import time
from dataclasses import dataclass
from statistics import median

import mud.crafting as crafting
from mud.character_options import CLASSES_BY_KEY, RACES_BY_KEY
from mud.equipment_system import EQUIPMENT_SLOTS, normalize_slot
from mud.mechanics import class_abilities_for_level
from mud.production_hardening import ensure_production_schema
from mud.room_engine import PlayerRoomContext
from mud.starter_race_loops import STARTER_RACE_LOOPS_BY_RACE


HARDENING_VERSION = "1.0.0"
CONTENT_CEILING = 40
CHECKPOINTS = (10, 20, 30, 40)
LEVEL_BANDS = ((1, 10), (11, 20), (21, 30), (31, 40))
SOLO_SAMPLES_PER_CLASS_BAND = 5
GROUP_SAMPLES_PER_BAND = 3
OUTSIDE_PLAYTESTER_TARGET = 20
MEANINGFUL_COMMANDS = 25
OBSERVATION_CATEGORIES = frozenset({"onboarding", "combat", "gear", "group", "navigation", "story", "other"})


@dataclass(frozen=True, slots=True)
class FirstTenMatrixAudit:
    combinations: int
    walkable_starts: int
    level_ten_kits: int
    problems: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.problems and self.combinations == 40


@dataclass(frozen=True, slots=True)
class GearCheckpoint:
    checkpoint: int
    tier: int
    items: int
    slots: tuple[str, ...]
    median_power: float


@dataclass(frozen=True, slots=True)
class GearCurveAudit:
    checkpoints: tuple[GearCheckpoint, ...]
    monotonic_power: bool
    catalog_problems: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.catalog_problems and self.monotonic_power


@dataclass(frozen=True, slots=True)
class CombatCell:
    level_low: int
    level_high: int
    class_key: str
    fights: int
    victories: int
    deaths: int
    average_seconds: float
    party_fights: int

    @property
    def death_rate(self) -> float:
        return 0.0 if self.fights <= 0 else self.deaths / self.fights


@dataclass(frozen=True, slots=True)
class CombatAudit:
    hours: int
    cells: tuple[CombatCell, ...]
    solo_cells_ready: int
    solo_cells_total: int
    group_bands_ready: int
    group_bands_total: int
    warnings: tuple[str, ...]

    @property
    def evidence_ready(self) -> bool:
        return self.solo_cells_ready == self.solo_cells_total and self.group_bands_ready == self.group_bands_total


@dataclass(frozen=True, slots=True)
class PlaytestAudit:
    hours: int
    active_testers: int
    meaningful_testers: int
    race_class_combinations_seen: int
    stuck_reports: int
    bug_reports: int
    observations: int

    @property
    def cohort_ready(self) -> bool:
        return self.meaningful_testers >= OUTSIDE_PLAYTESTER_TARGET


@dataclass(frozen=True, slots=True)
class HardeningReadiness:
    first_ten: FirstTenMatrixAudit
    gear: GearCurveAudit
    combat: CombatAudit
    playtest: PlaytestAudit

    @property
    def ready_for_41_50(self) -> bool:
        return self.first_ten.ready and self.gear.ready and self.combat.evidence_ready and self.playtest.cohort_ready

    @property
    def status(self) -> str:
        return "READY FOR 41-50" if self.ready_for_41_50 else "HOLD 41-50: HARDEN 1-40"


def ensure_alpha_hardening_schema(database) -> None:
    ensure_production_schema(database)
    with database.connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS alpha_hardening_combat_context (
                combat_log_id INTEGER PRIMARY KEY,
                character_id INTEGER,
                race_key TEXT NOT NULL DEFAULT '',
                class_key TEXT NOT NULL DEFAULT '',
                character_level INTEGER NOT NULL DEFAULT 1,
                party_size INTEGER NOT NULL DEFAULT 1,
                room_key TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (combat_log_id) REFERENCES production_combat_log(id) ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS alpha_hardening_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                category TEXT NOT NULL,
                note TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_alpha_hardening_observations_created
            ON alpha_hardening_observations(created_at);
            """
        )


def _party_size(session) -> int:
    try:
        from mud.party_system import _party_for_session

        party = _party_for_session(session)
        if party is not None:
            return max(1, len(party.member_ids))
    except Exception:
        pass
    return 1


def _record_combat_context(session, combat_log_id: int) -> None:
    character = getattr(session, "character", None)
    if character is None:
        return
    ensure_alpha_hardening_schema(session.database)
    with session.database.connect() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO alpha_hardening_combat_context (
                combat_log_id, character_id, race_key, class_key,
                character_level, party_size, room_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(combat_log_id),
                int(character.id),
                str(getattr(character, "race", "") or ""),
                str(getattr(character, "character_class", "") or ""),
                int(getattr(character, "level", 1) or 1),
                _party_size(session),
                str(getattr(character, "current_room", "") or ""),
            ),
        )


async def _delegate_prompt(session, previous_prompt, command: str) -> None:
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


def install_alpha_hardening_runtime(player_session_class) -> None:
    """Attach party/class context to the production combat telemetry already in use."""
    if getattr(player_session_class, "_alpha_hardening_runtime_installed", False):
        return

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

        before_id = getattr(self, "_production_combat_log_id", None)
        await _delegate_prompt(self, previous_prompt, command)
        after_id = getattr(self, "_production_combat_log_id", None)
        if after_id is not None and after_id != before_id:
            _record_combat_context(self, int(after_id))

    player_session_class.playing_prompt = playing_prompt
    player_session_class._alpha_hardening_runtime_installed = True


def audit_first_ten_matrix(world) -> FirstTenMatrixAudit:
    problems: list[str] = []
    walkable = 0
    kits = 0
    combinations = 0

    for race_key in sorted(RACES_BY_KEY):
        loop = STARTER_RACE_LOOPS_BY_RACE.get(race_key)
        if loop is None:
            problems.append(f"{race_key}: no authored starter loop")
            continue
        for class_key in sorted(CLASSES_BY_KEY):
            combinations += 1
            context = PlayerRoomContext(
                character_id=999999,
                race_key=race_key,
                class_key=class_key,
                level=1,
                character_flags=frozenset(),
            )
            view = world.build_view(loop.starting_room_key, context)
            allowed = False
            if view is not None:
                for visible in view.exits:
                    resolution = world.resolve_exit(loop.starting_room_key, visible.direction, context)
                    if resolution.allowed:
                        allowed = True
                        break
            if allowed:
                walkable += 1
            else:
                problems.append(f"{race_key}/{class_key}: no walkable exit from live start")

            deity = "zerjz" if class_key == "priest" else None
            abilities = class_abilities_for_level(class_key, 10, deity)
            if abilities:
                kits += 1
            else:
                problems.append(f"{race_key}/{class_key}: empty level-10 class kit")

    if combinations != 40:
        problems.append(f"expected 40 race/class combinations, found {combinations}")
    return FirstTenMatrixAudit(combinations, walkable, kits, tuple(problems))


def _equipment_power(item) -> float:
    equipment = getattr(item, "equipment", None)
    if equipment is None:
        return 0.0
    stats = equipment.stat_bonuses
    raw_stats = stats.might + stats.grace + stats.love + stats.mind + stats.hp
    return float(max(0, int(getattr(item, "tier", 0))) * 10 + equipment.armor_class * 2 + raw_stats + len(equipment.scripted_effects) * 5)


def audit_gear_curve() -> GearCurveAudit:
    by_tier: dict[int, list] = {}
    for item in crafting.ITEMS_BY_KEY.values():
        if getattr(item, "equipment", None) is None:
            continue
        tier = max(0, int(getattr(item, "tier", 0) or 0))
        by_tier.setdefault(tier, []).append(item)

    checkpoints: list[GearCheckpoint] = []
    problems: list[str] = []
    medians: list[float] = []
    for checkpoint, tier in zip(CHECKPOINTS, (1, 2, 3, 4)):
        items = by_tier.get(tier, [])
        slots: set[str] = set()
        powers: list[float] = []
        for item in items:
            try:
                slot = normalize_slot(item.equipment.slot)
            except ValueError:
                continue
            if slot in EQUIPMENT_SLOTS:
                slots.add(slot)
            powers.append(_equipment_power(item))
        power = float(median(powers)) if powers else 0.0
        medians.append(power)
        checkpoints.append(GearCheckpoint(checkpoint, tier, len(items), tuple(sorted(slots)), power))
        if not items:
            problems.append(f"level {checkpoint}: no tier-{tier} equipment exists")
        if len(slots) < 4:
            problems.append(f"level {checkpoint}: tier-{tier} gear covers only {len(slots)} core slots")

    monotonic = all(later > earlier for earlier, later in zip(medians, medians[1:]))
    if not monotonic:
        problems.append("median equipment power does not rise cleanly across tiers 1-4")
    return GearCurveAudit(tuple(checkpoints), monotonic, tuple(problems))


def _band_for_level(level: int) -> tuple[int, int] | None:
    for low, high in LEVEL_BANDS:
        if low <= level <= high:
            return low, high
    return None


def combat_balance_audit(database, hours: int = 24 * 14) -> CombatAudit:
    ensure_alpha_hardening_schema(database)
    hours = max(1, min(24 * 90, int(hours)))
    cutoff = time.time() - hours * 3600
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT p.character_level,
                   COALESCE(NULLIF(c.class_key, ''), ch.character_class, '') AS class_key,
                   COALESCE(c.party_size, 1) AS party_size,
                   p.outcome,
                   p.duration_seconds
            FROM production_combat_log p
            LEFT JOIN alpha_hardening_combat_context c ON c.combat_log_id = p.id
            LEFT JOIN characters ch ON ch.id = p.character_id
            WHERE p.started_at_epoch >= ?
              AND p.outcome <> 'open'
              AND p.character_level BETWEEN 1 AND 40
            """,
            (cutoff,),
        ).fetchall()

    buckets: dict[tuple[int, int, str], list] = {}
    for row in rows:
        band = _band_for_level(int(row["character_level"] or 0))
        class_key = str(row["class_key"] or "")
        if band is None or class_key not in CLASSES_BY_KEY:
            continue
        buckets.setdefault((band[0], band[1], class_key), []).append(row)

    cells: list[CombatCell] = []
    warnings: list[str] = []
    ready_cells = 0
    for low, high in LEVEL_BANDS:
        band_cells: list[CombatCell] = []
        for class_key in sorted(CLASSES_BY_KEY):
            samples = buckets.get((low, high, class_key), [])
            solo = [row for row in samples if int(row["party_size"] or 1) <= 1]
            completed = len(solo)
            victories = sum(1 for row in solo if row["outcome"] == "victory")
            deaths = sum(1 for row in solo if row["outcome"] == "death")
            durations = [float(row["duration_seconds"] or 0.0) for row in solo if row["duration_seconds"] is not None]
            avg = sum(durations) / len(durations) if durations else 0.0
            party_fights = sum(1 for row in samples if int(row["party_size"] or 1) >= 2)
            cell = CombatCell(low, high, class_key, completed, victories, deaths, avg, party_fights)
            cells.append(cell)
            band_cells.append(cell)
            if completed >= SOLO_SAMPLES_PER_CLASS_BAND:
                ready_cells += 1
                if victories == 0:
                    warnings.append(f"levels {low}-{high} {class_key}: no victories in {completed} solo samples")
                if cell.death_rate > 0.50:
                    warnings.append(f"levels {low}-{high} {class_key}: death rate {cell.death_rate:.0%}")

        comparable = [cell for cell in band_cells if cell.fights >= SOLO_SAMPLES_PER_CLASS_BAND and cell.average_seconds > 0]
        if len(comparable) == len(CLASSES_BY_KEY):
            fastest = min(comparable, key=lambda item: item.average_seconds)
            slowest = max(comparable, key=lambda item: item.average_seconds)
            if slowest.average_seconds > fastest.average_seconds * 1.75:
                warnings.append(
                    f"levels {low}-{high}: {slowest.class_key} averages {slowest.average_seconds:.1f}s vs "
                    f"{fastest.class_key} {fastest.average_seconds:.1f}s; inspect class pacing"
                )

    group_ready = 0
    for low, high in LEVEL_BANDS:
        total = sum(cell.party_fights for cell in cells if cell.level_low == low and cell.level_high == high)
        if total >= GROUP_SAMPLES_PER_BAND:
            group_ready += 1

    return CombatAudit(
        hours=hours,
        cells=tuple(cells),
        solo_cells_ready=ready_cells,
        solo_cells_total=len(LEVEL_BANDS) * len(CLASSES_BY_KEY),
        group_bands_ready=group_ready,
        group_bands_total=len(LEVEL_BANDS),
        warnings=tuple(warnings),
    )


def _alpha_tables(database) -> set[str]:
    with database.connect() as db:
        rows = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(row[0]) for row in rows}


def playtest_audit(database, hours: int = 24 * 30) -> PlaytestAudit:
    ensure_alpha_hardening_schema(database)
    hours = max(1, min(24 * 180, int(hours)))
    tables = _alpha_tables(database)
    if not {"alpha_ux_events", "alpha_ux_milestones", "alpha_player_reports"}.issubset(tables):
        return PlaytestAudit(hours, 0, 0, 0, 0, 0, 0)

    with database.connect() as db:
        command_rows = db.execute(
            """
            SELECT e.character_id, COUNT(*) AS commands,
                   COALESCE(ch.race, '') AS race_key,
                   COALESCE(ch.character_class, '') AS class_key
            FROM alpha_ux_events e
            LEFT JOIN characters ch ON ch.id = e.character_id
            WHERE e.created_at >= datetime('now', ?)
              AND e.event_key = 'command'
              AND e.character_id IS NOT NULL
            GROUP BY e.character_id
            """,
            (f"-{hours} hours",),
        ).fetchall()
        milestone_rows = db.execute(
            "SELECT character_id, milestone_key FROM alpha_ux_milestones"
        ).fetchall()
        report_rows = db.execute(
            """
            SELECT report_type, COUNT(*) AS total
            FROM alpha_player_reports
            WHERE created_at >= datetime('now', ?)
            GROUP BY report_type
            """,
            (f"-{hours} hours",),
        ).fetchall()
        observation_count = db.execute(
            "SELECT COUNT(*) FROM alpha_hardening_observations WHERE created_at >= datetime('now', ?)",
            (f"-{hours} hours",),
        ).fetchone()[0]

    milestones: dict[int, set[str]] = {}
    for row in milestone_rows:
        milestones.setdefault(int(row["character_id"]), set()).add(str(row["milestone_key"]))
    required = {"first_movement", "first_combat", "first_quest_progress"}
    meaningful = []
    combos: set[tuple[str, str]] = set()
    for row in command_rows:
        character_id = int(row["character_id"])
        if int(row["commands"] or 0) < MEANINGFUL_COMMANDS:
            continue
        if not required.issubset(milestones.get(character_id, set())):
            continue
        meaningful.append(character_id)
        race_key = str(row["race_key"] or "")
        class_key = str(row["class_key"] or "")
        if race_key and class_key:
            combos.add((race_key, class_key))

    reports = {str(row["report_type"]): int(row["total"] or 0) for row in report_rows}
    return PlaytestAudit(
        hours=hours,
        active_testers=len(command_rows),
        meaningful_testers=len(meaningful),
        race_class_combinations_seen=len(combos),
        stuck_reports=reports.get("stuck", 0),
        bug_reports=reports.get("bug", 0),
        observations=int(observation_count or 0),
    )


def record_observation(database, category: str, note: str) -> None:
    ensure_alpha_hardening_schema(database)
    category = category.strip().lower()
    if category not in OBSERVATION_CATEGORIES:
        raise ValueError("Observation category must be one of: " + ", ".join(sorted(OBSERVATION_CATEGORIES)))
    clean = " ".join(note.replace("\r", " ").replace("\n", " ").split())[:1000]
    if not clean:
        raise ValueError("Observation note cannot be empty")
    with database.connect() as db:
        db.execute(
            "INSERT INTO alpha_hardening_observations (category, note) VALUES (?, ?)",
            (category, clean),
        )


def recent_observations(database, hours: int = 24 * 30, limit: int = 20) -> tuple[dict[str, str], ...]:
    ensure_alpha_hardening_schema(database)
    hours = max(1, min(24 * 180, int(hours)))
    limit = max(1, min(100, int(limit)))
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT created_at, category, note
            FROM alpha_hardening_observations
            WHERE created_at >= datetime('now', ?)
            ORDER BY id DESC
            LIMIT ?
            """,
            (f"-{hours} hours", limit),
        ).fetchall()
    return tuple({"created_at": str(row["created_at"]), "category": str(row["category"]), "note": str(row["note"])} for row in rows)


def hardening_readiness(database, world, hours: int = 24 * 30) -> HardeningReadiness:
    return HardeningReadiness(
        first_ten=audit_first_ten_matrix(world),
        gear=audit_gear_curve(),
        combat=combat_balance_audit(database, hours),
        playtest=playtest_audit(database, hours),
    )
