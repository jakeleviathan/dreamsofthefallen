from __future__ import annotations

import unittest
from types import SimpleNamespace

from mud.reflection_opportunities import (
    find_reflection_opportunity,
    reflection_opportunities,
    render_reflection,
)


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
        starts = (
            ("human_demon_gate", "The Demon Gate", "human_kingdom"),
            ("forest_elf_circle_clearing", "Circle Clearing", "great_elf_forest"),
            ("moon_elf_high_horizon_plaza", "High Horizon Plaza", "moon_peaks"),
            ("dwarf_foundry_concourse", "Foundry Concourse", "dwarven_mountain_industry"),
            ("goblin_clattergate", "Clattergate", "junk_city_and_swamps"),
            ("troll_frostroot_camp", "Frostroot Camp", "troll_strongholds"),
            ("undead_reclamation_vault", "Reclamation Vault", "desert_necropolis"),
            ("sporekin_lumen_hollow", "Lumen Hollow", "sporekin_underways"),
        )
        for room_key, name, region in starts:
            with self.subTest(room_key=room_key):
                sources = reflection_opportunities(
                    scene(room_key, name, region),
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
