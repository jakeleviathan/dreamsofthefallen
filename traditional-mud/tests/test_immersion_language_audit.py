from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path


FORBIDDEN_META_FRAGMENTS = (
    "the game",
    "game tells you",
    "quest update",
    "daily checklist",
    "power reward",
    "perfect build",
    "hidden parser",
    "menu-selected",
    "useful command",
    "room stops being forgiving",
    "dungeon's tone",
    "figure players will remember",
    "player trade",
    "first-ten racial arc",
    "used by everyone else",
    "the command demonstrates",
)


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def test_source_strings_do_not_contain_known_fourth_wall_phrases():
    """Guard authored prose against design/developer language leaking to players."""

    mud_root = Path(__file__).resolve().parents[1] / "mud"
    failures: list[str] = []

    for path in sorted(mud_root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            text = _normalized(node.value)
            for fragment in FORBIDDEN_META_FRAGMENTS:
                if fragment in text:
                    failures.append(
                        f"{path.name}:{getattr(node, 'lineno', '?')}: "
                        f"{fragment!r} in {node.value[:180]!r}"
                    )

    assert not failures, "Fourth-wall language audit failed:\n" + "\n".join(failures)


def test_assembled_world_content_stays_inside_the_fiction():
    """Audit final generated/augmented production content, not only source literals."""

    root = Path(__file__).resolve().parents[1]
    code = r'''
import server
import mud.combat as combat
import mud.crafting as crafting
import mud.quests as quests

forbidden = (
    "the game",
    "game tells you",
    "quest update",
    "daily checklist",
    "power reward",
    "perfect build",
    "hidden parser",
    "menu-selected",
    "useful command",
    "room stops being forgiving",
    "dungeon's tone",
    "figure players will remember",
    "player trade",
    "first-ten racial arc",
    "used by everyone else",
    "the command demonstrates",
)

def audit(label, value):
    text = " ".join(str(value or "").casefold().split())
    for fragment in forbidden:
        assert fragment not in text, f"{label}: {fragment!r} leaked into {value!r}"

for room_key in sorted(server.WORLD.legacy_rooms):
    scene = server.WORLD.scene(room_key)
    if scene is None:
        continue
    audit(f"room {room_key} name", scene.name)
    audit(f"room {room_key} description", scene.base_description)
    for layer in scene.description_layers:
        audit(f"room {room_key} layer {layer.key}", layer.text)
    for feature in scene.features:
        audit(f"feature {room_key}/{feature.key} name", feature.name)
        audit(f"feature {room_key}/{feature.key} summary", feature.summary)
        audit(f"feature {room_key}/{feature.key} examine", feature.examine_text)
        audit(f"feature {room_key}/{feature.key} search", feature.search_text)
        audit(f"feature {room_key}/{feature.key} touch", feature.touch_text)
        audit(f"feature {room_key}/{feature.key} listen", feature.listen_text)

for enemy in combat.ENEMIES:
    audit(f"enemy {enemy.key}", enemy.description)

for item in crafting.ITEMS:
    audit(f"item {item.key}", item.description)

for quest in quests.QUESTS:
    audit(f"quest {quest.key}", quest.description)
    for step_key, objective in quest.objective_steps:
        audit(f"quest {quest.key}/{step_key}", objective)

print("IMMERSION_LANGUAGE_OK")
'''
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(root)},
        timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "IMMERSION_LANGUAGE_OK" in result.stdout
