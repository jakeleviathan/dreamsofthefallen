import asyncio

# Compatibility for an older Dwarf first-shift symbol typo that only appears
# when the fully assembled live WORLD is passed back through that installer.
import mud.dwarf_first_shift as dwarf_first_shift
import mud.crafting as crafting
import mud.world as legacy_world

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
from mud.economy_loop import install_economy_loop_runtime, install_fresh_water_sources
from mud.economy_balance import install_economy_balance_runtime
from mud.sols import install_sols_runtime
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
from mud.corpse_loot import install_corpse_loot_runtime
from mud.content_loot import install_content_loot_tables
from mud.death_recovery import RESURRECTION_ABILITY, install_death_recovery_runtime
from mud.class_progression import install_class_progression_runtime
from mud.class_progression_tuning import apply_inherited_class_tuning
from mud.upper_class_progression import install_upper_class_progression_runtime
from mud.late_class_progression import install_late_class_progression_runtime
from mud.priest_early_progression import install_priest_early_progression_runtime
from mud.first_ten_progression import install_first_ten_runtime
from mud.first_ten_adventures import install_first_ten_adventures_runtime
from mud.first_ten_story_depth import install_first_ten_story_depth_runtime
from mud.class_world_integration import install_class_world_integration_runtime
from mud.launch_vertical_slice import install_launch_vertical_slice_runtime
from mud.living_world import install_living_world_runtime
from mud.player_mail import install_player_mail_runtime
from mud.living_world_depth import install_living_world_depth_runtime
from mud.living_world_depth_tuning import apply_living_world_depth_tuning
from mud.living_world_continuity import install_living_world_continuity_runtime
from mud.social_pastimes import install_social_pastimes_runtime
from mud.waymeet_adventure_runtime import install_waymeet_adventure_runtime
from mud.midgame_three_roads import install_midgame_12_20_runtime
from mud.midgame_three_roads_tuning import apply_midgame_three_roads_tuning
from mud.frontier_convergence import install_frontier_convergence_runtime
from mud.eight_roads_midgame import install_eight_roads_runtime
from mud.broken_reach_midgame import install_broken_reach_runtime
from mud.broken_reach_tuning import apply_broken_reach_route_tuning
from mud.salt_kingdoms_midgame import install_salt_kingdoms_runtime
from mud.midgame_depth import install_midgame_depth_runtime
from mud.crownfire_march_31_40 import install_crownfire_runtime
from mud.crownfire_tuning import apply_crownfire_room_field_tuning
from mud.roadside_discoveries import install_roadside_discoveries_runtime
from mud.style_collectibles import install_style_collectibles_runtime
from mud.style_collectibles_tuning import apply_style_collectibles_tuning
from mud.iconic_items import install_iconic_items
from mud.content_foundry import install_content_foundry_runtime
from mud.content_density import install_content_density_runtime
from mud.recipe_quality import apply_recipe_semantic_quality
from mud.profession_workshops import install_profession_workshops_runtime
from mud.profession_expansion import install_profession_expansion_content, install_profession_expansion_runtime
from mud.planar_realms import install_planar_realms_runtime
from mud.item_naming import install_authored_item_names
from mud.command_guide import install_command_guide_runtime
from mud.alpha_ux import install_alpha_ux_runtime
from mud.modern_client_experience import install_modern_client_runtime
from mud.production_hardening import install_production_hardening_runtime, install_production_server_runtime
from mud.production_operator import install_production_operator_runtime
from mud.room_presentation import install_room_presentation_runtime
from mud.npc_name_audit import validate_unique_npc_names
from mud.quest_npc_audit import validate_quest_talk_references
from mud.npc_conversation import validate_static_npc_talkability
import mud.npcs as mobile_npcs
from mud.casting import install_casting_runtime
from mud.enemy_targeting import install_enemy_targeting_runtime
from mud.health_regeneration import install_health_regeneration_runtime
from mud.mechanics import PRIEST_DEITY_ABILITIES
from mud.database import Database
from mud.character_options import RACES_BY_KEY
from mud.quests import QUESTS_BY_KEY
from mud.world import ROOMS_BY_KEY
from mud.starter_race_loops import install_starter_room_database_hook, validate_starter_loop_contract
from mud.location_safety import (
    install_universal_location_repair_runtime,
    live_rooms_for_world,
    validate_authored_exit_targets,
    validate_starter_route_walks,
)

# The advanced room service must use the same mutable registry that authored
# content installers populate. Pointing it at the canonical dictionary instead
# of a copied snapshot means Goblin rooms (and any later dynamically registered
# rooms) are immediately visible to LOOK, EXITS, movement, and validation.
WORLD.legacy_rooms = ROOMS_BY_KEY
WORLD._scene_cache.clear()

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
# Sols are the universal Astralis currency: sun-stamped coins stored in sparks,
# with embers and flames as display denominations. This layer also owns generic
# merchant BUY/SELL/VALUE, quest payouts, and humanoid coin drops.
install_sols_runtime(PlayerSession, Database)
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
# The physical world now carries players through level 30, so each class also
# receives an executable 21-30 progression pass. Identities deepen rather than
# branch into talent trees: Brutes hold lines, Wizards sequence spells, Druids
# blend terrain and recovery, Necromancers manage life/resources, and each Priest
# path earns its own level-30 culmination.
install_upper_class_progression_runtime(PlayerSession)
# Crownfire already carries the world through 40. This pass closes the mechanical
# gap with executable class abilities at 32, 35, 38, and 40 while preserving the
# fixed-class philosophy: Brutes hold the line, Wizards sequence, Druids shape
# terrain and recovery, Necromancers spend resources, and Priest paths diverge.
install_late_class_progression_runtime(PlayerSession)
# Priests own a complete executable foundation through level 10. The first-ten
# pass adds level-10 capstones and the three racial milestones. The adventure
# layer turns each milestone into a routed story; the story-depth layer then adds
# authored scenes, recurring two-person relationships, remembered dialogue, and
# room descriptions that change because of the player's discoveries and actions.
install_priest_early_progression_runtime(PlayerSession)
install_first_ten_runtime(PlayerSession)
install_first_ten_adventures_runtime(PlayerSession, WORLD)
install_first_ten_story_depth_runtime(PlayerSession, WORLD)
install_class_world_integration_runtime(PlayerSession)
install_launch_vertical_slice_runtime(PlayerSession)
install_living_world_runtime(PlayerSession)
apply_living_world_depth_tuning()
install_living_world_depth_runtime(PlayerSession)
install_living_world_continuity_runtime(PlayerSession)
install_social_pastimes_runtime(PlayerSession)
install_waymeet_adventure_runtime(PlayerSession, WORLD)
# The original Three Roads remain full regional stories: Troll politics and
# wilderness north, Dwarven industrial depth east, and the Moon Elf highroad.
install_midgame_12_20_runtime(PlayerSession, WORLD)
apply_midgame_three_roads_tuning()
# Ashcross and the Meridian Outerworks provide the shared 15-18 convergence.
install_frontier_convergence_runtime(PlayerSession, WORLD)
# Complete the cultural midgame matrix with five more level-12 approaches:
# Human Blackglass March, Forest Elf Alderwake, Goblin Rattlechain, Undead Pale
# Road, and Sporekin Rainroot. All eight roads remain open to every race. Any
# three independent witness threads, plus the mapped Outerworks, open Meridian.
install_eight_roads_runtime(PlayerSession, WORLD)
# Broken Reach is the broad shared 11-20 exploration region beyond Waymeet.
# It adds caravan disappearances, the morally gray Grinning Men, three competing
# regional claims, a full House Beneath the Hill dungeon, optional oddities, and
# a level-20 event that removes the old surface span and opens a buried bypass.
install_broken_reach_runtime(PlayerSession, WORLD)
# Preserve the existing level-2 Old Toll Road and Veyra->Sablewater SOUTH exits.
# Broken Reach continues south from the old toll road and approaches Veyra from
# the west, so adding the new region never steals an older player's route.
apply_broken_reach_route_tuning(WORLD)
# Whitewake and the Salt Kingdoms deliberately begin after the Broken Reach
# capstone. This layer owns levels 21-30: a major dry-harbor city, two very
# different dungeons, water politics, and a level-30 hydraulic choice that
# physically changes travel through the basin for that character.
install_salt_kingdoms_runtime(PlayerSession, WORLD)
# The depth pass gives the 17-30 boss band readable encounter mechanics, restrained
# named objects, and optional hidden rooms/side stories without replacing the
# main regional progression.
install_midgame_depth_runtime(PlayerSession, WORLD)
# Crownfire begins only after the Salt Kingdoms level-30 capstone. Unlike the
# previous ancient-system mysteries, its level 31-40 crisis is contemporary and
# intentional: Marshal Corven Dask manufactures raids, blockades, conscription,
# and protection revenue through the living Gilded Host.
install_crownfire_runtime(PlayerSession, WORLD)
# Normalize Crownfire's compact authored room helper into the legacy room field
# order before the final world safety audit.
apply_crownfire_room_field_tuning(WORLD)
# Add small places that are intentionally not another main story: a buried room
# of fifty chairs, a bell-less watchtower, a blue salt sink, and a civilian noon
# signal tower. They reward curiosity without becoming mandatory progression.
install_roadside_discoveries_runtime(PlayerSession, WORLD)
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
# The deep profession pass turns every crafting trade into a full progression
# rather than a thin starter catalog. It runs after regional content so its
# resource placements and recipe validation see the assembled production world.
_PROFESSION_RECIPE_COUNTS = install_profession_expansion_content()
# Final semantic pass: preserve stable recipe keys while correcting legacy
# ingredient combinations that existed only to force cross-region material use.
apply_recipe_semantic_quality()
install_profession_workshops_runtime(PlayerSession)
install_profession_expansion_runtime(PlayerSession)

# Regional installers above own their local gathering tables and may replace
# entries while registering content. Add common freshwater last so those local
# resources and the world-wide Spring Water layer coexist.
install_fresh_water_sources(legacy_world.ROOMS_BY_KEY)

# Expand the daily living-world pulse only after every physical region above is
# registered. This yields hundreds of concrete regional events while preserving
# the original twelve authored anchors and all existing living-world mechanics.
from mud.living_world_variety import apply_living_world_event_variety
apply_living_world_event_variety(PlayerSession)
# Planar content is installed after the physical world is complete but before
# help/GMCP presentation. Its entrances remain contextual and undisclosed: there
# is intentionally no seven-plane checklist for players to complete.
install_planar_realms_runtime(PlayerSession, WORLD)

# NPC names are part of the player-facing command namespace: TALK commonly accepts
# a given name, and two authored people sharing one makes rooms and quests
# needlessly ambiguous. Validate the final assembled static + mobile population
# after all content installers have run. A future duplicate proper name now fails
# production startup and CI instead of reaching players.
_NPC_NAME_RECORD_COUNT = validate_unique_npc_names(legacy_world, mobile_npcs)
_QUEST_TALK_REFERENCE_COUNT = validate_quest_talk_references(QUESTS_BY_KEY, legacy_world.NPCS_BY_KEY)
# Every static person shown in a room's [ People ] section must be addressable
# by full name and, when applicable, unique given name. This closes the gap
# where content existed visually but TALK fell through to the base error.
_NPC_TALKABILITY_COUNT = validate_static_npc_talkability(WORLD, legacy_world.NPCS_BY_KEY)

# Replace any surviving development-era item labels only after every item-producing
# content installer has run. Stable item keys remain untouched, so old characters,
# recipes, loot tables, and equipped rows immediately inherit the authored names.
install_authored_item_names()

# Compile one physical loot table for every killable enemy currently registered
# by the assembled world. Existing hand-authored drops remain authoritative; the
# family profiles only fill gaps left by older content modules. Production refuses
# to start if a new killable enemy somehow reaches this point without a table.
_CONTENT_LOOT_COVERAGE = install_content_loot_tables()
if _CONTENT_LOOT_COVERAGE.missing_tables:
    raise RuntimeError(
        "Missing physical loot tables for: " + ", ".join(_CONTENT_LOOT_COVERAGE.missing_tables)
    )

# Monster rewards now become physical, persistent room corpses. Installing this
# after all content and party loot hooks means every existing drop table feeds the
# same corpse system while XP/quest credit remains on the normal kill path.
install_corpse_loot_runtime(PlayerSession)

# Discovery/help, alpha friction telemetry, and modern-client presentation sit
# outside the assembled content stack. The alpha layer wraps the command guide so
# HELP HERE and ordinary actions can be measured without revealing hidden content.
install_command_guide_runtime(PlayerSession, WORLD)
install_alpha_ux_runtime(PlayerSession)
# Health recovery is an always-on session system like movement and mana recovery:
# 1 HP/6s out of combat, 2 while resting, 3 while resting somewhere restful,
# with Troll/Sporekin racial regeneration layered on top.
install_health_regeneration_runtime(PlayerSession, WORLD)
install_modern_client_runtime(PlayerSession, WORLD)
install_production_hardening_runtime(PlayerSession)
install_production_operator_runtime(PlayerSession)
install_production_server_runtime(MudServer)

# Final world safety is deliberately installed last. Every authored exit in the
# assembled live world must resolve, every racial start must support a real walk,
# and stale saved locations for any race are repaired before the rest of the
# enter-character stack can inspect them. The live registry is the union of the
# legacy global registry and the room service because both registration paths are
# still used by production content.
_LIVE_ROOMS = live_rooms_for_world(WORLD)
validate_authored_exit_targets(_LIVE_ROOMS)
validate_starter_route_walks(_LIVE_ROOMS)
# Direction labels are spatial grammar, not decorative metadata. Older content
# passes occasionally connected the same two rooms with incompatible labels
# (for example EAST one way and EAST again on the return). Normalize the final
# assembled physical graph once, preserving already-correct roads and richer
# exit metadata, then fail startup if any reciprocal mismatch survives.
_RECIPROCAL_EXIT_REPAIRS = WORLD.normalize_reciprocal_topology()
# Audit the fully assembled room service after every content installer has run
# so duplicate directions and impossible reverse routes never reach players.
WORLD.validate_exit_integrity()
install_universal_location_repair_runtime(PlayerSession, WORLD)

# Keep room presentation outside the authored gameplay stack so every area gets
# the same readable visual hierarchy without requiring per-room markup.
install_room_presentation_runtime(PlayerSession, WORLD)

# Enemy targeting sits immediately outside the complete authored ability stack.
# TARGET selects without aggro; an enemy-targeted hotbar ability promotes that
# selection into combat as the ability resolves.
install_enemy_targeting_runtime(PlayerSession, WORLD)

# Casting is installed after every ability wrapper so CAST always passes through
# the same interruptible timing layer, regardless of which progression module
# owns the eventual spell effect. Because targeting is installed first, cast-time
# spells retain the selected enemy and engage it when the cast completes.
install_casting_runtime(PlayerSession)

# Post is intentionally the final command wrapper. Its subject/body editor and
# destructive-action confirmations are modal input: they must see the player's
# next real line before any inner command wrapper can replay or consume it.
install_player_mail_runtime(PlayerSession)

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
