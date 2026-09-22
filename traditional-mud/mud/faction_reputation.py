from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FactionDefinition:
    key: str
    name: str
    home_regions: tuple[str, ...] = ()
    allies: tuple[str, ...] = ()
    rivals: tuple[str, ...] = ()


FACTIONS: tuple[FactionDefinition, ...] = (
    FactionDefinition("blackglass_crown", "Blackglass Crown", ("human_kingdom",), allies=("chainmark_houses",)),
    FactionDefinition("green_circle", "The Green Circle", ("great_elf_forest",), allies=("rainroot_chorus",)),
    FactionDefinition("moon_courts", "The Moon Courts", ("moon_elf_highlands",)),
    FactionDefinition("chainmark_houses", "Chainmark Trade Houses", ("dwarf_holds",), allies=("blackglass_crown",)),
    FactionDefinition("brassgut_clans", "Brassgut Clans", ("goblin_swamps",)),
    FactionDefinition("troll_tribes", "The Troll Tribes", ("troll_wilds",)),
    FactionDefinition("pale_houses", "The Pale Houses", ("undead_necropolis",)),
    FactionDefinition("rainroot_chorus", "The Rainroot Chorus", ("sporekin_underways",), allies=("green_circle",)),
)
FACTIONS_BY_KEY = {f.key: f for f in FACTIONS}

REGION_FACTION = {
    region: faction.key
    for faction in FACTIONS
    for region in faction.home_regions
}

# Race-specific quest keys predate the faction system and therefore use cultural
# prefixes rather than later faction names. Keep that old content meaningful
# without forcing hundreds of stable quest keys to be renamed.
QUEST_KEY_FACTION_PREFIXES: tuple[tuple[str, str], ...] = (
    ("human_", "blackglass_crown"),
    ("forest_elf_", "green_circle"),
    ("moon_elf_", "moon_courts"),
    ("dwarf_", "chainmark_houses"),
    ("goblin_", "brassgut_clans"),
    ("troll_", "troll_tribes"),
    ("undead_", "pale_houses"),
    ("sporekin_", "rainroot_chorus"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS character_faction_reputation (
    character_id INTEGER NOT NULL,
    faction_key TEXT NOT NULL,
    standing INTEGER NOT NULL DEFAULT 0,
    renown INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, faction_key),
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS character_faction_reputation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    faction_key TEXT NOT NULL,
    standing_delta INTEGER NOT NULL DEFAULT 0,
    renown_delta INTEGER NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',
    source_key TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_faction_rep_events_character
ON character_faction_reputation_events(character_id, id);
"""


def ensure_schema(database) -> None:
    with database.connect() as db:
        db.executescript(SCHEMA)


def _clamp_standing(value: int) -> int:
    return max(-1000, min(1000, int(value)))


def _clamp_renown(value: int) -> int:
    return max(0, min(1000, int(value)))


def get_reputation(database, character_id: int, faction_key: str) -> tuple[int, int]:
    ensure_schema(database)
    with database.connect() as db:
        row = db.execute(
            "SELECT standing, renown FROM character_faction_reputation WHERE character_id=? AND faction_key=?",
            (int(character_id), faction_key),
        ).fetchone()
    return (0, 0) if row is None else (int(row["standing"]), int(row["renown"]))


def adjust_reputation(
    database,
    character_id: int,
    faction_key: str,
    *,
    standing: int = 0,
    renown: int = 0,
    reason: str = "",
    source_key: str = "",
    propagate: bool = True,
) -> None:
    if faction_key not in FACTIONS_BY_KEY or (standing == 0 and renown == 0):
        return
    ensure_schema(database)
    changes: list[tuple[str, int, int, str]] = [(faction_key, int(standing), int(renown), reason)]
    if propagate:
        faction = FACTIONS_BY_KEY[faction_key]
        for key in faction.allies:
            changes.append((key, int(round(standing * 0.20)), int(round(renown * 0.10)), f"Word spread from {faction.name}."))
        for key in faction.rivals:
            changes.append((key, -int(round(standing * 0.12)), int(round(renown * 0.05)), f"Word spread from rival {faction.name}."))

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for key, ds, dr, why in changes:
            if ds == 0 and dr == 0:
                continue
            row = db.execute(
                "SELECT standing, renown FROM character_faction_reputation WHERE character_id=? AND faction_key=?",
                (int(character_id), key),
            ).fetchone()
            old_s, old_r = ((0, 0) if row is None else (int(row["standing"]), int(row["renown"])))
            new_s, new_r = _clamp_standing(old_s + ds), _clamp_renown(old_r + max(0, dr))
            db.execute(
                """
                INSERT INTO character_faction_reputation(character_id,faction_key,standing,renown)
                VALUES(?,?,?,?)
                ON CONFLICT(character_id,faction_key) DO UPDATE SET standing=excluded.standing, renown=excluded.renown
                """,
                (int(character_id), key, new_s, new_r),
            )
            db.execute(
                """
                INSERT INTO character_faction_reputation_events
                (character_id,faction_key,standing_delta,renown_delta,reason,source_key)
                VALUES(?,?,?,?,?,?)
                """,
                (int(character_id), key, new_s-old_s, new_r-old_r, why, source_key),
            )


def standing_word(value: int) -> str:
    if value <= -700: return "hated"
    if value <= -350: return "hostile"
    if value <= -120: return "distrusted"
    if value < 120: return "unknown"
    if value < 350: return "regarded"
    if value < 700: return "trusted"
    return "honored"


def renown_word(value: int) -> str:
    if value < 80: return "little known"
    if value < 250: return "recognized"
    if value < 500: return "well known"
    if value < 750: return "famous"
    return "legendary"


def merchant_price_multiplier(standing: int) -> float:
    if standing >= 700: return 0.85
    if standing >= 350: return 0.92
    if standing >= 120: return 0.97
    if standing <= -700: return 1.35
    if standing <= -350: return 1.20
    if standing <= -120: return 1.08
    return 1.0


def npc_reaction(standing: int, renown: int) -> str:
    known = renown >= 80
    if standing <= -700: return "recognizes you and makes no effort to hide open hatred" if known else "regards you with open hostility"
    if standing <= -350: return "recognizes you with immediate suspicion" if known else "watches you with suspicion"
    if standing <= -120: return "keeps the exchange cool and guarded"
    if standing >= 700: return "recognizes you warmly and treats you as an honored friend"
    if standing >= 350: return "recognizes you and speaks with established trust" if known else "treats you with clear trust"
    if standing >= 120: return "offers you a noticeably warmer welcome"
    if known: return "recognizes your name, though your standing here remains uncertain"
    return ""


def faction_for_region(region_key: str | None) -> str | None:
    return REGION_FACTION.get(str(region_key or ""))


def regional_reaction(database, character_id: int, region_key: str | None) -> str:
    """Return a diegetic local-reputation cue for a faction-controlled region."""
    faction_key = faction_for_region(region_key)
    if faction_key is None or database is None or not callable(getattr(database, "connect", None)):
        return ""
    standing, renown = get_reputation(database, character_id, faction_key)
    reaction = npc_reaction(standing, renown)
    if not reaction:
        return ""
    faction = FACTIONS_BY_KEY[faction_key]
    return f"Word has spread through {faction.name}; a nearby local {reaction}."


def render_reputation(database, character_id: int) -> str:
    ensure_schema(database)
    lines = ["--- Reputation ---"]
    any_known = False
    for faction in FACTIONS:
        standing, renown = get_reputation(database, character_id, faction.key)
        if standing == 0 and renown == 0:
            continue
        any_known = True
        lines.append(f"{faction.name}: {standing_word(standing)}; {renown_word(renown)}.")
    if not any_known:
        lines.append("No faction has formed a lasting opinion of you yet.")
    lines.append("Standing reflects how a faction regards you. Renown reflects how widely your name is known.")
    return "\r\n".join(lines)


def _quest_faction(quest) -> str | None:
    key = str(getattr(quest, "key", "") or "").casefold()

    # Newer authored quests may opt into a faction directly without changing the
    # shared QuestDefinition contract.
    explicit = str(
        getattr(quest, "faction_key", "")
        or getattr(quest, "reputation_faction", "")
        or ""
    )
    if explicit in FACTIONS_BY_KEY:
        return explicit

    for prefix, faction_key in QUEST_KEY_FACTION_PREFIXES:
        if key.startswith(prefix):
            return faction_key

    # Preserve support for content whose stable key already contains the faction
    # name itself.
    for faction_key in FACTIONS_BY_KEY:
        token = faction_key.split("_")[0]
        if token and token in key:
            return faction_key
    return None


def install_faction_database_hooks(database_class) -> None:
    if getattr(database_class, "_faction_reputation_hooks_installed", False):
        return
    previous_complete = database_class.complete_quest

    def complete_quest(self, character_id: int, quest_key: str):
        before = self.get_quest(character_id, quest_key)
        result = previous_complete(self, character_id, quest_key)
        after = self.get_quest(character_id, quest_key)
        if before is None or after is None or str(before.get("status")) != "active" or str(after.get("status")) != "completed":
            return result
        try:
            from mud.quests import QUESTS_BY_KEY
            quest = QUESTS_BY_KEY.get(quest_key)
            faction_key = _quest_faction(quest) if quest is not None else None
            if faction_key:
                adjust_reputation(self, character_id, faction_key, standing=18, renown=10, reason=f"Completed {getattr(quest, 'name', quest_key)}.", source_key=quest_key)
        except Exception:
            pass
        return result

    database_class.complete_quest = complete_quest
    database_class._faction_reputation_hooks_installed = True


async def _delegate(session, previous_prompt, command: str) -> None:
    had = "prompt" in session.__dict__
    old = session.__dict__.get("prompt")
    async def replay(_text: str) -> str: return command
    session.prompt = replay
    try: await previous_prompt(session)
    finally:
        if had: session.prompt = old
        else: session.__dict__.pop("prompt", None)


def install_faction_reputation_runtime(player_session_class, database_class, world_service) -> None:
    if getattr(player_session_class, "_faction_reputation_runtime_installed", False):
        return
    install_faction_database_hooks(database_class)
    previous_prompt = player_session_class.playing_prompt

    async def playing_prompt(self) -> None:
        if self.character is None:
            await previous_prompt(self); return
        command = await self.prompt("\r\n> ")
        if command is None:
            self.state = type(self.state).DISCONNECTED; return
        normalized = " ".join(command.strip().casefold().split())
        if normalized in {"reputation", "rep", "standing", "factions"}:
            await self.send("\r\n" + render_reputation(self.database, self.character.id) + "\r\n")
            return
        await _delegate(self, previous_prompt, command)

    player_session_class.playing_prompt = playing_prompt
    player_session_class._faction_reputation_runtime_installed = True
