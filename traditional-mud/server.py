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

# Product-level economy layers sit outside the authored race/quest runtimes.
# Base economy installs first, the balance/incentive pass sits above it, and trade
# remains outermost so movement, combat, and disconnects always invalidate deals.
install_economy_loop_runtime(PlayerSession, WORLD)
install_economy_balance_runtime(PlayerSession)
install_trade_experience_runtime(PlayerSession)


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
