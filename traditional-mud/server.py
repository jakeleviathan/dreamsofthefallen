import asyncio

# Compatibility for an older Dwarf first-shift symbol typo that only appears
# when the fully assembled live WORLD is passed back through that installer.
# The unit content path never exercised it, but the canonical production server
# does. Keep the live entrypoint healthy while preserving the authored room key.
import mud.dwarf_first_shift as dwarf_first_shift

if not hasattr(dwarf_first_shift, "BELLOWSWORKS_SHIFT_FLOOR_KEY"):
    dwarf_first_shift.BELLOWSWORKS_SHIFT_FLOOR_KEY = dwarf_first_shift.DWARF_BELLOWSWORKS_FLOOR_KEY

from mud.server import MudServer, PlayerSession, WORLD
from mud.trade_experience import install_trade_experience_runtime
from mud.economy_loop import install_economy_loop_runtime
from mud.economy_balance import install_economy_balance_runtime
from mud.forest_elf_reading_forest import install_reading_forest_runtime
from mud.starter_signature_moments import install_signature_moment_runtime
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
from mud.mechanics import PRIEST_DEITY_ABILITIES
from mud.database import Database
from mud.character_options import RACES_BY_KEY
from mud.quests import QUESTS_BY_KEY
from mud.world import ROOMS_BY_KEY
from mud.starter_race_loops import (
    install_starter_room_database_hook,
    validate_starter_loop_contract,
)


# All eight launch races must have a real authored first room and first playable
# quest. Fail at startup rather than quietly dropping a new character into an
# unimplemented region if future content work accidentally breaks that promise.
validate_starter_loop_contract(
    rooms_by_key=ROOMS_BY_KEY,
    quests_by_key=QUESTS_BY_KEY,
    race_keys=set(RACES_BY_KEY),
)
# Character creation now persists the correct starter room and bind point for
# every race immediately. Race-specific runtimes still own quest initialization
# and first-arrival narration so their show-don't-tell openings remain intact.
install_starter_room_database_hook(Database)

# Deepen the existing Forest Elf Old River Path without replacing its authored
# home/Heartseed sequence: quiet birds become a real warning, the Barkjaw is an
# avoidable ambush, a trapped stag becomes a persistent choice, and that choice
# can pay off later when Hollowbacks appear deeper in the forest.
install_reading_forest_runtime(PlayerSession, WORLD)
# Give the other seven races one similarly compact signature beat on top of their
# existing starter arcs: a small action or choice where culture and mechanics are
# the same thing, rather than another lore speech or another full tutorial chain.
install_signature_moment_runtime(PlayerSession, WORLD)
# Waymeet is the first shared post-homeland zone. It gives level 2-5 characters a
# common social hub, repeatable hunting contracts, merchants, gathering/crafting,
# and a dangerous road problem that points toward the first dungeon.
install_waymeet_runtime(PlayerSession, WORLD)
# The Gloamworks turns that hint into the first real cooperative dungeon: 18
# industrial/alien rooms, perception splits, two minibosses, and a two-player
# witness seal guarding the Buried Regent encounter.
install_gloamworks_runtime(PlayerSession, WORLD)
# Greywake carries the shared world beyond the dungeon into levels 5-10 with
# three competing practical factions, a multi-quest regional arc, a shared
# Gloam Surge world event, and the road ending at Veyra's outer gate.
install_greywake_runtime(PlayerSession, WORLD)
# Blackreed is the quicker level 5-7 party dungeon branching off Greywake: a
# bandit-held road fort, readable trash pulls, a signal-runner focus-fire lesson,
# and a shield captain who rewards one player holding threat while another flanks.
install_blackreed_runtime(PlayerSession, WORLD)
# Veyra opens the first full shared capital: persistent vault storage, a real
# player barter exchange with escrow, class trainers, public boards, craft halls,
# bind services, and faction offices whose Greywake choices become useful perks.
install_veyra_runtime(PlayerSession, WORLD)
# Sablewater gives the midgame another direction entirely separate from Gloam:
# a level 6-10 river region and the Drowned Tollhouse, an old civic-machine
# dungeon whose problem is obsolete law and neglected waterworks, not anomaly.
install_sablewater_runtime(PlayerSession, WORLD)
# The city's living-core layer gives Veyra a calendar rhythm instead of static
# services: rotating daily material demand, weekly public contracts, and deeper
# faction ranks whose convenience perks come with small, explicit tradeoffs.
install_veyra_living_core_runtime(PlayerSession, WORLD)
# The Underclock is the next mechanically distinct level 8-10 dungeon. Players
# read a live four-beat municipal machine, time three hazardous crossings, pin
# pressure controls during specific phases, and fight the governor only after
# taking the room itself out of the fight.
install_underclock_runtime(PlayerSession, WORLD)
# Gravewatch is deliberately the palate-cleanser dungeon: a ruined riverside
# keep full of skeleton infantry, bone hounds, wight officers, readable patrol
# pulls, cramped chapel fighting, and one hard final commander with no hidden
# machine or metaphysical puzzle. Good fundamentals are the mechanic.
install_gravewatch_runtime(PlayerSession, WORLD)
# After the one-time Gravewatch clear, Sergeant Toma can issue fresh patrol
# slates that reset only the dungeon-run state. Rewards and story completion stay
# permanent while the keep remains useful as a repeatable traditional delve.
install_gravewatch_repeatable_runtime(PlayerSession)

# Product-level economy layers sit outside the authored race/quest runtimes.
# Base economy installs first, then the balance pass. Gravewatch's small party
# bridge sits above authored progression so officer/pull credit can be shared by
# characters who actually fought together without duplicating personal rewards.
install_economy_loop_runtime(PlayerSession, WORLD)
install_economy_balance_runtime(PlayerSession)
install_gravewatch_party_runtime(PlayerSession)
# Trade still owns its safety invalidation rules. Parties then sit outermost so a
# leader's movement can safely drive followers through the complete live movement
# stack, and shared combat sees the final loot/quest behavior beneath it.
install_trade_experience_runtime(PlayerSession)
install_party_runtime(PlayerSession)
# Existing common and uncommon monster drops obey party ROUNDROBIN/KILLER rules.
# Quest rewards remain personal and are intentionally not redirected.
install_party_loot_hooks()
# The clarity pass sits outermost: nearby-group discovery, ready checks, focus
# calls, a compact HUD, separation warnings, aggro/danger callouts, party-wide
# loot visibility, and explicit shared-victory participation summaries.
install_party_quality_runtime(PlayerSession)
# Death is the outermost lifecycle rule: fallen characters remain where they die
# until RELEASE applies the XP penalty and returns them to bind, while level-5+
# Priests can RESURRECT them in place before release and avoid that XP loss.
install_death_recovery_runtime(PlayerSession)
# Moon Elf Witnesses are a Priest path but deliberately are not a fourth deity.
# The inner world registers that path dynamically, so finish the shared Priest
# utility pass over every registered path after all authored content is loaded.
for _priest_path_key, _abilities in tuple(PRIEST_DEITY_ABILITIES.items()):
    if not any(_ability.key == RESURRECTION_ABILITY.key for _ability in _abilities):
        PRIEST_DEITY_ABILITIES[_priest_path_key] = _abilities + (RESURRECTION_ABILITY,)
# Class progression sits outside the assembled combat/equipment/death stack. It
# turns levels 1-9 into readable role growth, makes the early authored ability
# stubs executable, adds support targeting/group tools, and registers five
# craftable signature items whose affinities reinforce each class without
# reintroducing class-locked equipment.
install_class_progression_runtime(PlayerSession)
# Promote the older level-one session-only costs/cooldowns into ability data so
# the expanded runtime, CLASS display, and legacy direct commands all agree.
apply_inherited_class_tuning()


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
