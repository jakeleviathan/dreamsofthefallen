from __future__ import annotations

from dataclasses import dataclass

from mud.character_options import ClassDefinition, RaceDefinition


@dataclass(frozen=True, slots=True)
class RacePresentation:
    hook: str
    known_for: str
    world_view: str
    starting_area: str


@dataclass(frozen=True, slots=True)
class ClassPresentation:
    hook: str
    play_style: str
    good_if: str


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


CLASS_PRESENTATIONS: dict[str, ClassPresentation] = {
    "brute": ClassPresentation(
        hook="Strength with responsibility: stand where the danger has to deal with you first.",
        play_style="A weapon-focused frontline fighter built around threat control, direct physical damage, and protecting other people by holding enemy attention.",
        good_if="You like being in the middle of the fight, controlling pressure, relying on weapons and gear, and making physical decisions that matter to the whole group.",
    ),
    "wizard": ClassPresentation(
        hook="Careful power through understanding.",
        play_style="A direct-damage arcane caster with powerful spells, self-protection, magical utility, and eventually world-spanning movement magic.",
        good_if="You like solving problems with precise spellwork, hitting hard from magic rather than weapons, and carrying some of your own protection and utility.",
    ),
    "druid": ClassPresentation(
        hook="Care for living things with healing, preparation, and practical nature magic.",
        play_style="A nature-oriented support caster combining healing, buffs, gathering utility, wards, and control without shapeshifting.",
        good_if="You like helping a group stay healthy and prepared, using nature as a toolkit, and being useful even when raw damage is not the answer.",
    ),
    "priest": ClassPresentation(
        hook="Ritual care without easy answers.",
        play_style="Astralis's strongest dedicated healer and defensive-support class, with an authored spiritual path that shapes later spells and abilities.",
        good_if="You like keeping other people alive, protecting a group, carrying major healing responsibility, and letting faith or tradition shape how your magic develops.",
    ),
    "necromancer": ClassPresentation(
        hook="Death work with consequences.",
        play_style="A caster built around life-draining magic, decay, damage over time, undead servants, and practical tools that deal directly with death.",
        good_if="You like pets, attrition, unusual utility, morally weighty magic, and power that often asks what should be done rather than only what can be done.",
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


def _find_class(options: tuple[ClassDefinition, ...], choice: str) -> ClassDefinition | None:
    normalized = _normalize_choice(choice)
    if normalized.isdigit():
        index = int(normalized)
        if 1 <= index <= len(options):
            return options[index - 1]
        return None
    for character_class in options:
        names = {
            _normalize_choice(character_class.key),
            _normalize_choice(character_class.name),
        }
        if normalized in names:
            return character_class
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


async def _show_calling_list(session, options: tuple[ClassDefinition, ...]) -> None:
    await session.send(
        "\r\n--- Choose Your Calling ---\r\n"
        "Start with the kind of adventurer you want to be. Pick a calling to see how it actually plays before committing.\r\n\r\n"
    )
    for index, character_class in enumerate(options, start=1):
        presentation = CLASS_PRESENTATIONS.get(character_class.key)
        hook = presentation.hook if presentation else character_class.description
        await session.send(f"{index}) {character_class.name} - {hook}\r\n")
    await session.send(
        "\r\nEvery people can follow every calling. Enter a number or class name to look closer.\r\n"
        "Type 0 or CANCEL to leave character creation.\r\n"
    )


async def _show_class_card(session, character_class: ClassDefinition) -> None:
    presentation = CLASS_PRESENTATIONS.get(character_class.key)
    await session.send(f"\r\n--- {character_class.name} ---\r\n")
    if presentation is None:
        await session.send(character_class.description + "\r\n")
    else:
        await session.send(
            f"Vibe: {presentation.hook}\r\n\r\n"
            f"How it plays: {presentation.play_style}\r\n"
            f"Good if you like: {presentation.good_if}\r\n"
            f"At the start: {character_class.early_game_identity}\r\n"
        )
    if character_class.requires_deity_path:
        await session.send(
            "Path: Your Priest tradition or patron is chosen immediately after class selection and shapes your authored spell path.\r\n"
        )
    await session.send(
        "\r\nType CHOOSE to continue with this class, MORE DETAILS for the longer mechanical picture, or BACK to compare classes.\r\n"
    )


async def _show_class_details(session, character_class: ClassDefinition) -> None:
    await session.send(f"\r\n--- More Details: {character_class.name} ---\r\n")
    await session.send(f"Core role: {character_class.description}\r\n")
    await session.send(f"Later identity: {character_class.endgame_identity}\r\n")
    await session.send(f"Equipment: {character_class.equipment_identity}\r\n")
    await session.send(
        "Ability progression: Your class has an authored ability path; you do not build it from a talent pool.\r\n"
    )
    if character_class.class_passives:
        await session.send("Class features: " + ", ".join(character_class.class_passives) + ".\r\n")
    if character_class.allows_shapeshifting:
        await session.send("Shapeshifting: This class can shapeshift.\r\n")
    elif character_class.key == "druid":
        await session.send("Shapeshifting: Druids in Dreams of the Fallen do not shapeshift.\r\n")
    if character_class.requires_deity_path:
        await session.send(
            "Spiritual path: Priest abilities branch through an authored patron or cultural tradition rather than a generic spell list.\r\n"
        )
    await session.send("\r\nType CHOOSE to continue or BACK to compare classes.\r\n")


async def choose_class_experience(
    session,
    options: tuple[ClassDefinition, ...],
) -> ClassDefinition | None:
    while True:
        await _show_calling_list(session, options)
        choice = await session.prompt("Calling: ")
        if choice is None:
            import mud.session as session_module

            session.state = session_module.SessionState.DISCONNECTED
            return None
        if _normalize_choice(choice) in {"0", "cancel", "quit", "q"}:
            await session.send("\r\nCharacter creation cancelled.\r\n")
            return None

        character_class = _find_class(options, choice)
        if character_class is None:
            await session.send("\r\nChoose one of the listed callings by number or class name.\r\n")
            continue

        await _show_class_card(session, character_class)
        while True:
            action = await session.prompt(f"{character_class.name}: ")
            if action is None:
                import mud.session as session_module

                session.state = session_module.SessionState.DISCONNECTED
                return None
            normalized = _normalize_choice(action)
            if normalized in {"choose", "select", "yes", "y", "continue"}:
                return character_class
            if normalized in {"more", "more details", "details", "info", "mechanics"}:
                await _show_class_details(session, character_class)
                continue
            if normalized in {"back", "b", "compare"}:
                break
            if normalized in {"0", "cancel", "quit", "q"}:
                await session.send("\r\nCharacter creation cancelled.\r\n")
                return None
            await session.send("Type CHOOSE, MORE DETAILS, or BACK.\r\n")


def install_character_creation_experience(player_session_class) -> None:
    """Make race and class selection hook-first without changing the underlying rules."""
    if getattr(player_session_class, "_character_creation_experience_installed", False):
        return

    previous_choose_creation_option = player_session_class.choose_creation_option

    async def choose_creation_option(self, label: str, options):
        normalized_label = label.strip().lower()
        if normalized_label == "race" and options and all(
            isinstance(option, RaceDefinition) for option in options
        ):
            return await choose_race_experience(self, tuple(options))
        if normalized_label == "class" and options and all(
            isinstance(option, ClassDefinition) for option in options
        ):
            return await choose_class_experience(self, tuple(options))
        return await previous_choose_creation_option(self, label, options)

    player_session_class.choose_creation_option = choose_creation_option
    player_session_class._character_creation_experience_installed = True
