from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mud.room_player_presence import room_player_entries
from mud.waymeet_frontier import WAYMEET_TAVERN_KEY, WAYMEET_TAVERN_LOFT_KEY


def character(character_id: int, name: str, room: str = WAYMEET_TAVERN_KEY):
    return SimpleNamespace(
        id=character_id,
        name=name,
        race="goblin" if character_id == 1 else "dwarf",
        character_class="priest" if character_id == 1 else "brute",
        current_room=room,
    )


def session_for(member):
    return SimpleNamespace(
        character=member,
        _movement_resting=False,
        active_enemy=None,
        state=SimpleNamespace(name="PLAYING"),
    )


class RoomPlayerPresenceTests(unittest.TestCase):
    def setUp(self):
        self.viewer = session_for(character(1, "Prime"))
        self.neighbor = session_for(character(2, "Brom"))
        self.viewer.room_players_callback = lambda room, exclude: (
            self.neighbor.character,
        )

    def entries(self):
        with patch("mud.room_player_presence._ACTIVE_SESSIONS", [self.neighbor]):
            return room_player_entries(self.viewer)

    def test_shows_self_and_other_online_player(self):
        self.assertEqual(
            self.entries(),
            [
                ("Prime (you)", "a Goblin Priest standing nearby"),
                ("Brom", "a Dwarf Brute standing nearby"),
            ],
        )

    def test_resting_is_visible_to_everyone_and_changes_with_stand(self):
        self.viewer._movement_resting = True
        self.neighbor._movement_resting = True
        self.assertEqual(
            self.entries(),
            [
                ("Prime (you)", "a Goblin Priest resting beside the gearwheel hearth"),
                ("Brom", "a Dwarf Brute resting beside the gearwheel hearth"),
            ],
        )
        self.neighbor._movement_resting = False
        self.assertEqual(self.entries()[1], ("Brom", "a Dwarf Brute standing nearby"))

    def test_guest_loft_uses_room_specific_rest_description(self):
        self.viewer.character.current_room = WAYMEET_TAVERN_LOFT_KEY
        self.viewer._movement_resting = True
        self.assertEqual(
            self.entries(),
            [("Prime (you)", "a Goblin Priest resting in the guest loft")],
        )

    def test_combat_takes_priority_and_updates_immediately(self):
        self.neighbor._movement_resting = True
        self.neighbor.active_enemy = SimpleNamespace(
            alive=True, definition=SimpleNamespace(name="Cellar Rat")
        )
        self.assertEqual(self.entries()[1], ("Brom", "a Dwarf Brute fighting Cellar Rat"))
        self.neighbor.active_enemy = None
        self.assertIn("resting", self.entries()[1][1])

    def test_only_the_room_callback_decides_who_is_visible(self):
        self.viewer.room_players_callback = lambda _room, _exclude: ()
        self.assertEqual(len(self.entries()), 1)
        self.viewer.room_players_callback = lambda _room, _exclude: (
            self.viewer.character, self.neighbor.character, self.neighbor.character
        )
        self.assertEqual(len(self.entries()), 2)

    def test_missing_or_failing_callback_still_shows_own_state(self):
        self.viewer._movement_resting = True
        self.viewer.room_players_callback = lambda *_args: (_ for _ in ()).throw(
            RuntimeError("unavailable")
        )
        self.assertEqual(len(self.entries()), 1)
        del self.viewer.room_players_callback
        self.assertIn("resting", self.entries()[0][1])

    def test_disconnected_or_moved_player_does_not_supply_stale_activity(self):
        self.neighbor._movement_resting = True
        self.neighbor.state.name = "DISCONNECTED"
        self.assertEqual(self.entries()[1], ("Brom", "a Dwarf Brute standing nearby"))
        self.neighbor.state.name = "PLAYING"
        self.neighbor.character.current_room = "another_room"
        self.assertEqual(self.entries()[1], ("Brom", "a Dwarf Brute standing nearby"))


if __name__ == "__main__":
    unittest.main()
