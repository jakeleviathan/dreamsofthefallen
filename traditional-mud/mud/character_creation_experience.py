from __future__ import annotations

from dataclasses import dataclass

from mud.character_options import RaceDefinition


@dataclass(frozen=True, slots=True)
class RacePresentation:
    hook: str
    known_for: str
    world_view: str
    starting_area: str


RACE_PRESENTATIONS: dict[str, RacePresentation] = {
    "human": RacePresentation(
        hook="Outsiders who crossed from another world and made Astralis their home.",
        known_for="Adaptability, fast learning, Blackwall civic life, and a culture that made the outsider image of 'Demons' its own.",
        world_view="Rare outsiders. Many non-Humans call your people Demons, sometimes casually and sometimes with suspicion.",
        starting_area="Blackwall - a lived-in walled Human capital of watch yards, guild streets, caravans, archives, and old Earth traces.",
    ),
    "forest_elf": RacePresentation(
        hook="Woodland elves shaped by community, beauty, and a forest that is never entirely tame.",
        known_for="Grace, local stewardship, Druidic Circles, comfortable forest towns, and practical closeness to living things.",
        world_view="Beautiful and insular, with a reputation for being stubborn about who gets to call themselves an elf.",
        starting_area="The Great Elf Forest - a comfortable forest town whose safe paths gradually give way to wilder country.",
    ),
    "moon_elf": RacePresentation(
        hook="High-horizon elves who prize perspective, revision, and seeing beyond the first explanation.",
        known_for="Skyglass architecture, generational journals, civic Counterview, elegant high-altitude cities, and a sacred philosophy of perspective.",
        world_view="Generally accepted but unusual. Forest Elves sharply dispute your people's claim to simply be called elves.",
        starting_area="High Horizon - a safe high-altitude city of terraces, lifts, journals, night markets, gardens, and enormous views.",
    ),
    "dwarf": RacePresentation(
        hook="Steam-age mountain folk whose cities run on craft, contracts, lifts, unions, and stubborn competence.",
        known_for="Steam power, trade houses, labor unions, bureaucracy, workshops, foundries, freight systems, and meticulous craft.",
        world_view="A major trade power: dependable, procedural, cosmopolitan, and sometimes exhausting to negotiate with.",
        starting_area="The Mountain Industry - a vast working city spread through underground halls and busy surface districts.",
    ),
    "goblin": RacePresentation(
        hook="Swamp-born salvagers and dealmakers who turn somebody else's junk into tomorrow's solution.",
        known_for="Salvage, repair, bargaining, repurposing, clans, markets, shortcuts, improvised tools, and making ugly things work.",
        world_view="Often distrusted and treated as an underclass, while everyone still seems to need a Goblin fixer eventually.",
        starting_area="Rattlefen - a crowded, noisy swamp city of salvage claims, markets, workshops, canals, and deals.",
    ),
    "troll": RacePresentation(
        hook="Ancient hunters and survivors whose harsh homelands reward preparation more than bravado.",
        known_for="Hunting, warfare, animal handling, strong tribal ties, difficult wilderness, and natural regeneration.",
        world_view="Frequently stereotyped as stupid or dangerous despite ordinary intelligence and a highly practical culture.",
        starting_area="Frostroot Stronghold - a harsh but organized frontier home where survival is taught before the wilderness gets a vote.",
    ),
    "undead": RacePresentation(
        hook="Reanimated people building lives after death in a quiet civilization beneath the desert.",
        known_for="Remembering former lives, freedom after reanimation, necromantic traditions, old houses, funerary culture, and not needing mortal necessities.",
        world_view="Feared by many living peoples, who often see the dead body before they see the person inhabiting it.",
        starting_area="The Necropolis - a vast underground city beneath a desolate desert, eerie in tone but full of ordinary civic life.",
    ),
    "sporekin": RacePresentation(
        hook="Fungal people who share memory and feeling through the Chorus without surrendering individual choice.",
        known_for="The Chorus, deep underground networks, shared impressions, patient guidance, fungal biology, and strong regeneration.",
        world_view="Mysterious and often regarded as wise, though outsiders rarely understand where shared consciousness ends and the individual begins.",
        starting_area="Lumen Hollow - living fungal underways that rise gradually toward the breathing surface world.",
    ),
}


def _normalize_choice(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _find_race(options: tuple[RaceDefinition, ...], choice: str) -> RaceDefinition | None:
    normalized = _normalize_choice(choice)
    if normalized.isdigit():
        index = int(normalized)
        if 1 <= index <= len(options):
            return options[index - 1]
        return None
    for race in options:
        names = {
            _normalize_choice(race.key),
            _normalize_choice(race.name),
        }
        if normalized in names:
            return race
    return None


async def _show_people_list(session, options: tuple[RaceDefinition, ...]) -> None:
    await session.send(
        "\r\n--- Choose Your People ---\r\n"
        "Start with the feeling. Pick one that sounds interesting; you can read the details before committing.\r\n\r\n"
    )
    for index, race in enumerate(options, start=1):
        presentation = RACE_PRESENTATIONS.get(race.key)
        hook = presentation.hook if presentation else race.description
        await session.send(f"{index}) {race.name} - {hook}\r\n")
    await session.send(
        "\r\nEnter a number or race name to look closer. Type 0 or CANCEL to leave character creation.\r\n"
    )


async def _show_race_card(session, race: RaceDefinition) -> None:
    presentation = RACE_PRESENTATIONS.get(race.key)
    await session.send(f"\r\n--- {race.name} ---\r\n")
    if presentation is None:
        await session.send(race.description + "\r\n")
    else:
        await session.send(
            f"Vibe: {presentation.hook}\r\n\r\n"
            f"Known for: {presentation.known_for}\r\n"
            f"The world sees you as: {presentation.world_view}\r\n"
            f"Starting area: {presentation.starting_area}\r\n"
        )
    if race.passive_name:
        await session.send(f"Racial trait: {race.passive_name} - {race.passive_description}\r\n")
    if race.ability_name:
        await session.send(f"Racial ability: {race.ability_name} - {race.ability_description}\r\n")
    await session.send(
        "\r\nType CHOOSE to continue with this race, MORE LORE for the full background, or BACK to compare races.\r\n"
    )


async def _show_more_lore(session, race: RaceDefinition) -> None:
    await session.send(f"\r\n--- More Lore: {race.name} ---\r\n{race.description}\r\n")
    for item in race.lore:
        await session.send(f"- {item}\r\n")
    await session.send("\r\nType CHOOSE to continue or BACK to compare races.\r\n")


async def choose_race_experience(
    session,
    options: tuple[RaceDefinition, ...],
) -> RaceDefinition | None:
    while True:
        await _show_people_list(session, options)
        choice = await session.prompt("People: ")
        if choice is None:
            import mud.session as session_module

            session.state = session_module.SessionState.DISCONNECTED
            return None
        if _normalize_choice(choice) in {"0", "cancel", "quit", "q"}:
            await session.send("\r\nCharacter creation cancelled.\r\n")
            return None

        race = _find_race(options, choice)
        if race is None:
            await session.send("\r\nChoose one of the listed peoples by number or name.\r\n")
            continue

        await _show_race_card(session, race)
        while True:
            action = await session.prompt(f"{race.name}: ")
            if action is None:
                import mud.session as session_module

                session.state = session_module.SessionState.DISCONNECTED
                return None
            normalized = _normalize_choice(action)
            if normalized in {"choose", "select", "yes", "y", "continue"}:
                return race
            if normalized in {"more", "more lore", "lore", "details", "info"}:
                await _show_more_lore(session, race)
                continue
            if normalized in {"back", "b", "compare"}:
                break
            if normalized in {"0", "cancel", "quit", "q"}:
                await session.send("\r\nCharacter creation cancelled.\r\n")
                return None
            await session.send("Type CHOOSE, MORE LORE, or BACK.\r\n")


def install_character_creation_experience(player_session_class) -> None:
    """Make race selection hook-first without changing the underlying race/class rules."""
    if getattr(player_session_class, "_character_creation_experience_installed", False):
        return

    previous_choose_creation_option = player_session_class.choose_creation_option

    async def choose_creation_option(self, label: str, options):
        if label.strip().lower() == "race" and options and all(
            isinstance(option, RaceDefinition) for option in options
        ):
            return await choose_race_experience(self, tuple(options))
        return await previous_choose_creation_option(self, label, options)

    player_session_class.choose_creation_option = choose_creation_option
    player_session_class._character_creation_experience_installed = True
