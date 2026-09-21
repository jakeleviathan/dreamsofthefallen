from __future__ import annotations

import unittest
from types import SimpleNamespace

from mud.reflection_opportunities import (
    find_reflection_opportunity,
    reflection_opportunities,
    render_reflection,
)
from mud.starter_race_loops import STARTER_RACE_LOOPS


def scene(
    key: str,
    name: str,
    region_key: str,
    tags: tuple[str, ...] = (),
):
    return SimpleNamespace(
        key=key,
        name=name,
        region_key=region_key,
        tags=tags,
    )


class ReflectionOpportunityTests(unittest.TestCase):
    def test_every_racial_start_has_a_permanent_reflective_source(self):
        self.assertEqual(len(STARTER_RACE_LOOPS), 8)
        for loop in STARTER_RACE_LOOPS:
            with self.subTest(race=loop.race_key, room_key=loop.starting_room_key):
                sources = reflection_opportunities(
                    scene(
                        loop.starting_room_key,
                        loop.starting_room_key.replace("_", " ").title(),
                        loop.region_key,
                    ),
                    "clear",
                    exposed=True,
                )
                self.assertTrue(sources)
                self.assertNotEqual(sources[0].key, "rain_puddle")

    def test_rain_creates_puddles_in_any_exposed_room(self):
        sources = reflection_opportunities(
            scene(
                "brand_new_exposed_road",
                "Brand New Exposed Road",
                "human_kingdom",
                ("road", "surface"),
            ),
            "rain",
            exposed=True,
        )
        self.assertTrue(any(source.key == "rain_puddle" for source in sources))

    def test_rain_does_not_create_puddle_under_solid_cover(self):
        sources = reflection_opportunities(
            scene(
                "covered_tunnel",
                "Covered Tunnel",
                "human_kingdom",
                ("tunnel", "interior"),
            ),
            "storm",
            exposed=False,
        )
        self.assertFalse(any(source.key == "rain_puddle" for source in sources))

    def test_social_hubs_get_region_specific_public_reflection_fixtures(self):
        dwarf_sources = reflection_opportunities(
            scene(
                "deepwheel_lower_exchange",
                "Lower Exchange",
                "deepwheel_dwarf_corridor",
                ("safe", "trade"),
            ),
            "clear",
            exposed=False,
        )
        self.assertTrue(any("Brass" in source.name for source in dwarf_sources))

        goblin_sources = reflection_opportunities(
            scene(
                "rattlechain_trade_yard",
                "Trade Yard",
                "junk_city_and_swamps",
                ("merchant", "safe"),
            ),
            "humid",
            exposed=True,
        )
        self.assertTrue(any("Salvaged" in source.name for source in goblin_sources))

    def test_existing_water_and_mirror_rooms_become_reflective_without_special_case_commands(self):
        water_sources = reflection_opportunities(
            scene(
                "scar_flooded_shaft",
                "Flooded Shaft",
                "kings_scar",
                ("dungeon",),
            ),
            "clear",
            exposed=False,
        )
        self.assertTrue(any(source.source_kind == "water" for source in water_sources))

        mirror_sources = reflection_opportunities(
            scene(
                "counterstar_mirrored_cut",
                "Mirrored Cut",
                "counterstar_highroad",
                ("observation",),
            ),
            "clear",
            exposed=True,
        )
        self.assertTrue(any("Mirror" in source.name for source in mirror_sources))

    def test_generic_reflection_target_resolves_to_first_available_source(self):
        test_scene = scene(
            "waymeet_crossroads",
            "Waymeet Crossroads",
            "waymeet_frontier",
            ("social_hub", "safe"),
        )
        source = find_reflection_opportunity(
            test_scene,
            "clear",
            "reflection",
            exposed=True,
        )
        self.assertIsNotNone(source)
        assert source is not None
        self.assertEqual(source.name, "Wayfarer's Looking Glass")

    def test_rendered_reflection_uses_saved_character_appearance(self):
        source = reflection_opportunities(
            scene("dwarf_foundry_concourse", "Foundry Concourse", "dwarven_mountain_industry"),
            "clear",
            exposed=False,
        )[0]
        text = render_reflection(
            "Brom",
            "dwarf",
            {
                "build": "broad",
                "complexion": "ruddy",
                "hair_color": "brown",
                "beard_style": "braided",
                "beard_adornment": "iron rings",
                "eye_color": "green",
            },
            source,
        )
        self.assertIn("Brom is a Dwarf", text)
        self.assertIn("braided brown beard", text)
        self.assertIn(source.name.lower().split()[0], source.name.lower())


if __name__ == "__main__":
    unittest.main()
