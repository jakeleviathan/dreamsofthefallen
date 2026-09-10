from __future__ import annotations

from dataclasses import dataclass


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


@dataclass(frozen=True, slots=True)
class RummageNode:
    """An explicitly authored place where SEARCH/RUMMAGE may have special meaning.

    The node only identifies a room interaction. It intentionally contains no
    loot table, random reward, respawn timer, or inventory behavior. The caller
    owns eligibility and consequences so RUMMAGE does not become a universal
    free-loot button.
    """

    key: str
    room_key: str
    targets: tuple[str, ...]
    verbs: tuple[str, ...] = ("rummage", "search")

    def matches(self, command: str, room_key: str) -> bool:
        if room_key != self.room_key:
            return False
        normalized = _normalize(command)
        verb, separator, target = normalized.partition(" ")
        if not separator or verb not in self.verbs:
            return False
        aliases = {_normalize(value) for value in self.targets}
        return _normalize(target) in aliases


class RummageRegistry:
    """Small registry for authored rummage nodes.

    Registration is idempotent. Reusing a key for different authored content is
    rejected so one module cannot silently replace another module's room hook.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, RummageNode] = {}

    def register(self, node: RummageNode) -> None:
        existing = self._nodes.get(node.key)
        if existing is not None and existing != node:
            raise ValueError(f"Rummage node key already registered: {node.key}")
        self._nodes[node.key] = node

    def resolve(self, command: str, room_key: str) -> RummageNode | None:
        for node in self._nodes.values():
            if node.matches(command, room_key):
                return node
        return None

    def get(self, key: str) -> RummageNode | None:
        return self._nodes.get(key)

    def nodes_for_room(self, room_key: str) -> tuple[RummageNode, ...]:
        return tuple(node for node in self._nodes.values() if node.room_key == room_key)


RUMMAGE_NODES = RummageRegistry()
