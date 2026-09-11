import asyncio

from mud.server import MudServer, PlayerSession, WORLD
from mud.trade_experience import install_trade_experience_runtime
from mud.economy_loop import install_economy_loop_runtime
from mud.economy_balance import install_economy_balance_runtime


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
