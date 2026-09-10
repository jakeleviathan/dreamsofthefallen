import unittest

from mud.scavenging import RummageNode, RummageRegistry


class RummageFrameworkTests(unittest.TestCase):
    def test_node_matches_only_authored_room_target_and_verbs(self):
        node = RummageNode(
            key="test_scrap_pile",
            room_key="test_room",
            targets=("scrap pile", "pile"),
        )
        self.assertTrue(node.matches("rummage scrap pile", "test_room"))
        self.assertTrue(node.matches("SEARCH PILE", "test_room"))
        self.assertFalse(node.matches("rummage scrap pile", "other_room"))
        self.assertFalse(node.matches("search room", "test_room"))
        self.assertFalse(node.matches("take scrap pile", "test_room"))

    def test_registry_is_idempotent_but_rejects_key_replacement(self):
        registry = RummageRegistry()
        node = RummageNode("node", "room", ("pile",))
        registry.register(node)
        registry.register(node)
        self.assertIs(registry.resolve("rummage pile", "room"), node)

        with self.assertRaises(ValueError):
            registry.register(RummageNode("node", "different_room", ("pile",)))

    def test_framework_contains_no_generic_loot_result(self):
        node = RummageNode("node", "room", ("pile",))
        self.assertFalse(hasattr(node, "loot"))
        self.assertFalse(hasattr(node, "item_key"))
        self.assertFalse(hasattr(node, "reward"))


if __name__ == "__main__":
    unittest.main()
