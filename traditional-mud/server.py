import asyncio

from mud.server import MudServer, PlayerSession, WORLD
from mud.trade_experience import install_trade_experience_runtime
from mud.economy_loop import install_economy_loop_runtime
from mud.economy_balance import install_economy_balance_runtime
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
