import asyncio
import unittest
from types import SimpleNamespace

from mud.command_guide import install_command_guide_runtime
from mud.local_interactions import (
    PUMP_GALLERY_ROOM_KEY,
    contextual_action_hints,
    hidden_feature_verbs,
    normalize_local_interaction,
)


class LocalInteractionTests(unittest.TestCase):
    def test_pump_valves_accept_turn_open_and_use_phrasings(self):
        expected = {
            "turn black valve": "turn black valve",
            "turn drain": "turn black valve",
            "open black": "turn black valve",
            "open drain": "turn black valve",
            "use black valve": "turn black valve",
            "use drain valve": "turn black valve",
            "open blue valve": "turn blue valve",
            "use intake": "turn blue valve",
            "open red": "turn red valve",
            "use return valve": "turn red valve",
        }
        for command, canonical in expected.items():
            with self.subTest(command=command):
                self.assertEqual(
                    normalize_local_interaction(PUMP_GALLERY_ROOM_KEY, command),
                    canonical,
                )

    def test_local_aliases_do_not_steal_use_elsewhere(self):
        self.assertEqual(
            normalize_local_interaction("goblin_siltknife_boardwalk", "use black valve"),
            "use black valve",
        )
        self.assertEqual(
            normalize_local_interaction(PUMP_GALLERY_ROOM_KEY, "use pipe map"),
            "use pipe map",
        )

    def test_pump_gallery_context_help_prefers_turn_over_false_open_hint(self):
        self.assertEqual(hidden_feature_verbs(PUMP_GALLERY_ROOM_KEY), frozenset({"OPEN"}))
        hints = contextual_action_hints(PUMP_GALLERY_ROOM_KEY)
        self.assertEqual(hints[0][0], "TURN <valve>")
        self.assertIn("OPEN and USE", hints[0][1])

    def test_command_guide_routes_use_valve_before_inner_ability_parser(self):
        class Session:
            async def enter_character(self):
                return None

            async def playing_prompt(self):
                self.delegated_command = await self.prompt("legacy> ")

            def __init__(self):
                self.character = SimpleNamespace(current_room=PUMP_GALLERY_ROOM_KEY)
                self.active_enemy = None
                self.outputs = []
                self.delegated_command = None
                self.prompt = self._prompt

            async def _prompt(self, _text):
                return "use black valve"

            async def send(self, text):
                self.outputs.append(text)

        world = SimpleNamespace(legacy_rooms={}, augmentations={})
        install_command_guide_runtime(Session, world)
        session = Session()
        asyncio.run(session.playing_prompt())
        self.assertEqual(session.delegated_command, "turn black valve")

    def test_help_here_in_pump_gallery_explicitly_says_turn_valve(self):
        feature = SimpleNamespace(
            summary="blue, red, and black pump valves",
            examine_text="All three still move.",
            search_text="Opening blue or red during a flood adds pressure.",
            listen_text="",
            touch_text="",
        )
        room = SimpleNamespace(name="Pump Gallery", region_key="junk_city_and_swamps")
        world = SimpleNamespace(
            legacy_rooms={PUMP_GALLERY_ROOM_KEY: room},
            augmentations={PUMP_GALLERY_ROOM_KEY: SimpleNamespace(features=(feature,))},
        )

        class Session:
            async def enter_character(self):
                return None

            async def playing_prompt(self):
                self.delegated_command = await self.prompt("legacy> ")

            def __init__(self):
                self.character = SimpleNamespace(current_room=PUMP_GALLERY_ROOM_KEY)
                self.active_enemy = None
                self.outputs = []
                self.prompt = self._prompt

            async def _prompt(self, _text):
                return "help here"

            async def send(self, text):
                self.outputs.append(text)

        install_command_guide_runtime(Session, world)
        session = Session()
        asyncio.run(session.playing_prompt())
        output = "".join(session.outputs)
        self.assertIn("TURN <valve>", output)
        self.assertNotIn("OPEN <named feature>", output)
        self.assertIn("OPEN and USE work as aliases here", output)


if __name__ == "__main__":
    unittest.main()
