import asyncio

from mud.server import MudServer, PlayerSession, WORLD
from mud.trade_experience import install_trade_experience_runtime
from mud.economy_loop import install_economy_loop_runtime


# Product-level economy layers sit outside the authored race/quest runtimes.
# Economy installs first; trade remains the outermost command layer so movement,
# combat, and disconnects always get a chance to invalidate an open deal.
install_economy_loop_runtime(PlayerSession, WORLD)
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
