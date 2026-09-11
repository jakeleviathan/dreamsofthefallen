from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

import mud.quests as quests
import mud.world as world
from mud.human_blackwall_opening import (
    HUMAN_CARAVAN_COURT_KEY,
    HUMAN_OPENING_COMPLETE_FLAG,
    install_human_blackwall_content,
)
from mud.human_necromancer_start import (
    HUMAN_NECROMANCER_COMPLETE_FLAG,
    HUMAN_NECROMANCER_FIRST_LIFETAP_FLAG,
    HUMAN_NECROMANCER_GROWTH_DRAINED_FLAG,
    HUMAN_NECROMANCER_LIFE_CLEAR_FLAG,
    HUMAN_NECROMANCER_QUEST,
    HUMAN_NECROMANCER_QUEST_KEY,
    HUMAN_NECROMANCER_REMAINS_RECOVERED_FLAG,
    HUMAN_NECROMANCER_TUNNEL_STABLE_FLAG,
    HUMAN_SUBSIDENCE_CUT_KEY,
    TAMSIN_ROOK_KEY,
    human_necromancer_augmentations,
    install_human_necromancer_content,
    install_human_necromancer_runtime,
)
from mud.room_engine import PlayerRoomContext, WorldService


class FakeDatabase:
    def __init__(self, *, opening_complete: bool = True) -> None:
        self.flags: set[str] = set()
        if opening_complete:
            self.flags.add(HUMAN_OPENING_COMPLETE_FLAG)
        self.quests: dict[str, dict[str, str | None]] = {}
        self.ability_uses: list[tuple[int, str, int]] = []

    def list_flags(self, _character_id: int):
        return frozenset(self.flags)

    def grant_flag(self, _character_id: int, flag_key: str):
        self.flags.add(flag_key)

    def get_quest(self, _character_id: int, quest_key: str):
        row = self.quests.get(quest_key)
        return None if row is None else dict(row)

    def start_quest(self, _character_id: int, quest_key: str, current_step: str):
        self.quests.setdefault(
            quest_key,
            {"quest_key": quest_key, "status": "active", "current_step": current_step},
        )

    def advance_quest(self, _character_id: int, quest_key: str, current_step: str):
        self.quests[quest_key]["current_step"] = current_step

    def complete_quest(self, _character_id: int, quest_key: str):
        self.quests[quest_key]["status"] = "completed"
        self.quests[quest_key]["current_step"] = "complete"

    def record_ability_use(self, character_id: int, ability_key: str, skill_xp_gain: int = 1):
        self.ability_uses.append((character_id, ability_key, skill_xp_gain))


@dataclass
class FakeCharacter:
    id: int = 1
    name: str = "Mara"
    race: str = "human"
    character_class: str = "necromancer"
    deity_key: str | None = None
    current_room: str = HUMAN_CARAVAN_COURT_KEY
    level: int = 1


class FakeState:
    DISCONNECTED = "disconnected"


class FakeSession:
    def __init__(self, command: str = "", *, character=None, database=None) -> None:
        self.character = character or FakeCharacter()
        self.database = database or FakeDatabase()
        self.command = command
        self.outputs: list[str] = []
        self.state = FakeState()

    async def send(self, text: str):
        self.outputs.append(text)

    async def send_client_state(self):
        return None

    async def prompt(self, _text: str):
        return self.command

    async def enter_character(self):
        self.outputs.append("BASE ENTER\n")

    async def playing_prompt(self):
        command = await self.prompt("> ")
        self.outputs.append(f"BASE COMMAND: {command}\n")


class HumanNecromancerStartTests(unittest.TestCase):
    def setUp(self):
        self.rooms = world.ROOMS
        self.rooms_by_key = dict(world.ROOMS_BY_KEY)
        self.npcs = world.NPCS
        self.npcs_by_key = dict(world.NPCS_BY_KEY)
        self.quest_tuple = quests.QUESTS
        self.quest_map = dict(quests.QUESTS_BY_KEY)
        install_human_blackwall_content()
        install_human_necromancer_content()

    def tearDown(self):
        world.ROOMS = self.rooms
        world.ROOMS_BY_KEY.clear()
        world.ROOMS_BY_KEY.update(self.rooms_by_key)
        world.NPCS = self.npcs
        world.NPCS_BY_KEY.clear()
        world.NPCS_BY_KEY.update(self.npcs_by_key)
        quests.QUESTS = self.quest_tuple
        quests.QUESTS_BY_KEY.clear()
        quests.QUESTS_BY_KEY.update(self.quest_map)

    def test_content_adds_safe_civic_salvage_site_and_necromancer_mentor(self):
        self.assertIs(quests.QUESTS_BY_KEY[HUMAN_NECROMANCER_QUEST_KEY], HUMAN_NECROMANCER_QUEST)
        room = world.ROOMS_BY_KEY[HUMAN_SUBSIDENCE_CUT_KEY]
        self.assertIn("safe", room.tags)
        self.assertIn("necromancer", room.tags)
        self.assertIn("civic_work", room.tags)
        self.assertIn("salvage", room.tags)
        self.assertEqual(room.enemy_keys, ())
        self.assertIn(TAMSIN_ROOK_KEY, room.npc_keys)
        self.assertEqual(world.ROOMS_BY_KEY[HUMAN_CARAVAN_COURT_KEY].exits["north"], HUMAN_SUBSIDENCE_CUT_KEY)

        augmentation = human_necromancer_augmentations()[HUMAN_SUBSIDENCE_CUT_KEY]
        self.assertGreaterEqual(len(augmentation.features), 7)
        self.assertGreaterEqual(len(augmentation.description_layers), 4)

    def test_world_service_gets_named_route_from_caravan_court(self):
        service = WorldService(rooms=world.ROOMS_BY_KEY, augmentations={})
        install_human_necromancer_content(service)
        context = PlayerRoomContext(character_id=1, race_key="human", class_key="necromancer", level=1)
        result = service.resolve_exit(HUMAN_CARAVAN_COURT_KEY, "north", context)
        self.assertTrue(result.allowed)
        self.assertEqual(result.exit.destination_key, HUMAN_SUBSIDENCE_CUT_KEY)
        self.assertEqual(result.exit.name, "Blackwall Subsidence Cut")

    def test_only_human_necromancer_gets_extension_after_blackwall_opening(self):
        class NecromancerSession(FakeSession):
            pass

        install_human_necromancer_runtime(NecromancerSession)
        necromancer = NecromancerSession()
        asyncio.run(necromancer.enter_character())
        quest = necromancer.database.get_quest(1, HUMAN_NECROMANCER_QUEST_KEY)
        self.assertEqual(quest["current_step"], "meet_tamsin")
        self.assertIn("The Work Beneath the Wall", "".join(necromancer.outputs))

        class WizardSession(FakeSession):
            pass

        install_human_necromancer_runtime(WizardSession)
        wizard = WizardSession(character=FakeCharacter(character_class="wizard"))
        asyncio.run(wizard.enter_character())
        self.assertIsNone(wizard.database.get_quest(1, HUMAN_NECROMANCER_QUEST_KEY))

        class DwarfNecromancerSession(FakeSession):
            pass

        install_human_necromancer_runtime(DwarfNecromancerSession)
        dwarf = DwarfNecromancerSession(character=FakeCharacter(race="dwarf"))
        asyncio.run(dwarf.enter_character())
        self.assertIsNone(dwarf.database.get_quest(1, HUMAN_NECROMANCER_QUEST_KEY))

    def test_extension_waits_until_blackwall_opening_is_complete(self):
        class Session(FakeSession):
            pass

        install_human_necromancer_runtime(Session)
        session = Session(database=FakeDatabase(opening_complete=False))
        asyncio.run(session.enter_character())
        self.assertIsNone(session.database.get_quest(1, HUMAN_NECROMANCER_QUEST_KEY))

    def test_full_sequence_is_rescue_check_precise_lifetap_recovery_and_verification(self):
        class Session(FakeSession):
            pass

        install_human_necromancer_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = HUMAN_SUBSIDENCE_CUT_KEY

        sequence = (
            ("talk tamsin", "inspect_collapse"),
            ("examine collapse", "check_life"),
            ("check for life", "inspect_shoring"),
            ("examine shoring", "inspect_growth"),
            ("examine mortarvine", "tap_growth"),
            ("life tap mortarvine", "recover_remains"),
            ("recover remains", "verify_tunnel"),
            ("check tunnel", "return_tamsin"),
        )
        for command, expected_step in sequence:
            session.command = command
            asyncio.run(session.playing_prompt())
            quest = session.database.get_quest(1, HUMAN_NECROMANCER_QUEST_KEY)
            self.assertEqual(quest["current_step"], expected_step)

        self.assertIn(HUMAN_NECROMANCER_LIFE_CLEAR_FLAG, session.database.flags)
        self.assertIn(HUMAN_NECROMANCER_GROWTH_DRAINED_FLAG, session.database.flags)
        self.assertIn(HUMAN_NECROMANCER_REMAINS_RECOVERED_FLAG, session.database.flags)
        self.assertIn(HUMAN_NECROMANCER_TUNNEL_STABLE_FLAG, session.database.flags)
        self.assertIn(HUMAN_NECROMANCER_FIRST_LIFETAP_FLAG, session.database.flags)
        self.assertEqual(session.database.ability_uses, [(1, "minor_life_tap", 1)])

        session.command = "talk tamsin"
        asyncio.run(session.playing_prompt())
        quest = session.database.get_quest(1, HUMAN_NECROMANCER_QUEST_KEY)
        self.assertEqual(quest["status"], "completed")
        self.assertIn(HUMAN_NECROMANCER_COMPLETE_FLAG, session.database.flags)

        output = "".join(session.outputs).lower()
        self.assertIn("stone, timber, brass: salvage. a person is recovery", output)
        self.assertIn("death does not turn citizenship into inventory", output)
        self.assertIn("leave the wall safer than you found it", output)

    def test_dramatic_necromancy_and_early_lifetap_do_not_advance_work(self):
        class Session(FakeSession):
            pass

        install_human_necromancer_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = HUMAN_SUBSIDENCE_CUT_KEY
        session.command = "talk tamsin"
        asyncio.run(session.playing_prompt())

        session.command = "life tap mortarvine"
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.get_quest(1, HUMAN_NECROMANCER_QUEST_KEY)["current_step"], "inspect_collapse")
        self.assertEqual(session.database.ability_uses, [])

        session.command = "raise skeleton"
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.get_quest(1, HUMAN_NECROMANCER_QUEST_KEY)["current_step"], "inspect_collapse")
        self.assertEqual(session.database.ability_uses, [])
        output = "".join(session.outputs).lower()
        self.assertIn("spell is not a substitute", output)
        self.assertIn("not permission to turn the first dead thing", output)

    def test_lifetap_progress_cannot_be_farmed_by_replaying_step(self):
        class Session(FakeSession):
            pass

        install_human_necromancer_runtime(Session)
        session = Session()
        asyncio.run(session.enter_character())
        session.character.current_room = HUMAN_SUBSIDENCE_CUT_KEY
        session.database.advance_quest(1, HUMAN_NECROMANCER_QUEST_KEY, "tap_growth")
        session.command = "life tap mortarvine"
        asyncio.run(session.playing_prompt())
        session.database.advance_quest(1, HUMAN_NECROMANCER_QUEST_KEY, "tap_growth")
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.database.ability_uses, [(1, "minor_life_tap", 1)])


if __name__ == "__main__":
    unittest.main()
