import asyncio

# Compatibility for an older Dwarf first-shift symbol typo that only appears
# when the fully assembled live WORLD is passed back through that installer.
import mud.dwarf_first_shift as dwarf_first_shift
import mud.crafting as crafting

if not hasattr(dwarf_first_shift, "BELLOWSWORKS_SHIFT_FLOOR_KEY"):
    dwarf_first_shift.BELLOWSWORKS_SHIFT_FLOOR_KEY = dwarf_first_shift.DWARF_BELLOWSWORKS_FLOOR_KEY

# Newer content modules use one small registration helper rather than duplicating
# the tuple/dictionary mutation needed by the legacy crafting registry. Keep the
# helper here for backwards-compatible production assembly until crafting itself
# owns this API.
if not hasattr(crafting, "register_item"):
    def _register_item(item) -> None:
        if item.key not in crafting.ITEMS_BY_KEY:
            crafting.ITEMS = crafting.ITEMS + (item,)
        crafting.ITEMS_BY_KEY[item.key] = item
    crafting.register_item = _register_item

from mud.server import MudServer, PlayerSession, WORLD
from mud.trade_experience import install_trade_experience_runtime
from mud.economy_loop import install_economy_loop_runtime
from mud.economy_balance import install_economy_balance_runtime
from mud.forest_elf_reading_forest import install_reading_forest_runtime
from mud.starter_signature_moments import install_signature_moment_runtime
from mud.starter_class_moments import install_starter_class_moment_runtime
from mud.starter_matrix_quality import validate_starter_matrix_contract
from mud.waymeet_frontier import install_waymeet_runtime
from mud.gloamworks_dungeon import install_gloamworks_runtime
from mud.greywake_march import install_greywake_runtime
from mud.blackreed_holdfast import install_blackreed_runtime
from mud.veyra_city import install_veyra_runtime
from mud.sablewater_reach import install_sablewater_runtime
from mud.veyra_living_core import install_veyra_living_core_runtime
from mud.veyra_underclock import install_underclock_runtime
from mud.gravewatch_keep import install_gravewatch_runtime
from mud.gravewatch_repeatable import install_gravewatch_repeatable_runtime
from mud.gravewatch_party import install_gravewatch_party_runtime
from mud.party_system import install_party_runtime
from mud.party_loot import install_party_loot_hooks
from mud.party_quality import install_party_quality_runtime
from mud.death_recovery import RESURRECTION_ABILITY, install_death_recovery_runtime
from mud.class_progression import install_class_progression_runtime
from mud.class_progression_tuning import apply_inherited_class_tuning
from mud.class_world_integration import install_class_world_integration_runtime
from mud.launch_vertical_slice import install_launch_vertical_slice_runtime
from mud.living_world import install_living_world_runtime
from mud.living_world_depth import install_living_world_depth_runtime
from mud.living_world_depth_tuning import apply_living_world_depth_tuning
from mud.living_world_continuity import install_living_world_continuity_runtime
from mud.social_pastimes import install_social_pastimes_runtime
from mud.waymeet_adventure_runtime import install_waymeet_adventure_runtime
from mud.midgame_three_roads import install_midgame_12_20_runtime
from mud.midgame_three_roads_tuning import apply_midgame_three_roads_tuning
from mud.style_collectibles import install_style_collectibles_runtime
from mud.style_collectibles_tuning import apply_style_collectibles_tuning
from mud.iconic_items import install_iconic_items
from mud.content_foundry import install_content_foundry_runtime
from mud.content_density import install_content_density_runtime
from mud.planar_realms import install_planar_realms_runtime
from mud.command_guide import install_command_guide_runtime
from mud.alpha_ux import install_alpha_ux_runtime
from mud.modern_client_experience import install_modern_client_runtime
from mud.production_hardening import install_production_hardening_runtime, install_production_server_runtime
from mud.production_operator import install_production_operator_runtime
from mud.mechanics import PRIEST_DEITY_ABILITIES
from mud.database import Database
from mud.character_options import RACES_BY_KEY
from mud.quests import QUESTS_BY_KEY
from mud.world import ROOMS_BY_KEY
from mud.starter_race_loops import install_starter_room_database_hook, validate_starter_loop_contract

validate_starter_loop_contract(rooms_by_key=ROOMS_BY_KEY, quests_by_key=QUESTS_BY_KEY, race_keys=set(RACES_BY_KEY))
validate_starter_matrix_contract(quests_by_key=QUESTS_BY_KEY)
install_starter_room_database_hook(Database)

install_reading_forest_runtime(PlayerSession, WORLD)
install_signature_moment_runtime(PlayerSession, WORLD)
# The class-specific opening beat is a real production runtime, not merely a
# catalog/test fixture. Every one of the 8 races now receives the appropriate
# Brute, Wizard, Druid, Priest, or Necromancer practice inside its authored start.
install_starter_class_moment_runtime(PlayerSession)
install_waymeet_runtime(PlayerSession, WORLD)
install_gloamworks_runtime(PlayerSession, WORLD)
install_greywake_runtime(PlayerSession, WORLD)
install_blackreed_runtime(PlayerSession, WORLD)
install_veyra_runtime(PlayerSession, WORLD)
install_sablewater_runtime(PlayerSession, WORLD)
install_veyra_living_core_runtime(PlayerSession, WORLD)
install_underclock_runtime(PlayerSession, WORLD)
install_gravewatch_runtime(PlayerSession, WORLD)
install_gravewatch_repeatable_runtime(PlayerSession)

install_economy_loop_runtime(PlayerSession, WORLD)
install_economy_balance_runtime(PlayerSession)
install_gravewatch_party_runtime(PlayerSession)
install_trade_experience_runtime(PlayerSession)
install_party_runtime(PlayerSession)
install_party_loot_hooks()
install_party_quality_runtime(PlayerSession)
install_death_recovery_runtime(PlayerSession)
for _priest_path_key, _abilities in tuple(PRIEST_DEITY_ABILITIES.items()):
    if not any(_ability.key == RESURRECTION_ABILITY.key for _ability in _abilities):
        PRIEST_DEITY_ABILITIES[_priest_path_key] = _abilities + (RESURRECTION_ABILITY,)
install_class_progression_runtime(PlayerSession)
apply_inherited_class_tuning()
install_class_world_integration_runtime(PlayerSession)
install_launch_vertical_slice_runtime(PlayerSession)
install_living_world_runtime(PlayerSession)
apply_living_world_depth_tuning()
install_living_world_depth_runtime(PlayerSession)
install_living_world_continuity_runtime(PlayerSession)
install_social_pastimes_runtime(PlayerSession)
install_waymeet_adventure_runtime(PlayerSession, WORLD)
# Levels 12-20 deliberately branch after Veyra instead of extending one corridor:
# Troll politics and wilderness north, Dwarven industrial depth east, and the
# Moon Elf highroad above. Their three witness threads reconverge only at the
# level 19-20 Meridian Vault, where level 20 becomes a real class milestone.
install_midgame_12_20_runtime(PlayerSession, WORLD)
apply_midgame_three_roads_tuning()
install_style_collectibles_runtime(PlayerSession, WORLD)
apply_style_collectibles_tuning()

# The large content pass is layered rather than monolithic. The 90-item identity
# catalog establishes objects worth talking about; the foundry adds the first
# three authored delves and oddities; density then expands that pattern to ten
# new-delve identities total, twenty memorable bosses, 100 ordinary gear pieces,
# cross-region recipes, unscheduled rare encounters, curios, tiny errands, item-
# aware gossip, and Chronicle records generated by real player history.
install_iconic_items()
install_content_foundry_runtime(PlayerSession, WORLD)
install_content_density_runtime(PlayerSession, WORLD)

# Planar content is installed after the physical world is complete but before
# help/GMCP presentation. Its entrances remain contextual and undisclosed: there
# is intentionally no seven-plane checklist for players to complete.
install_planar_realms_runtime(PlayerSession, WORLD)

# Discovery/help, alpha friction telemetry, and modern-client presentation sit
# outside the assembled content stack. The alpha layer wraps the command guide so
# HELP HERE and ordinary actions can be measured without revealing hidden content.
install_command_guide_runtime(PlayerSession, WORLD)
install_alpha_ux_runtime(PlayerSession)
install_modern_client_runtime(PlayerSession, WORLD)
install_production_hardening_runtime(PlayerSession)
install_production_operator_runtime(PlayerSession)
install_production_server_runtime(MudServer)

HOST = "0.0.0.0"
PORT = 4000

async def main() -> None:
    mud = MudServer(host=HOST, port=PORT)
    await mud.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMUD server stopped.")