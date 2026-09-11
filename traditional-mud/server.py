import asyncio

from mud.server import MudServer, PlayerSession, WORLD
from mud.trade_experience import install_trade_experience_runtime
from mud.economy_loop import install_economy_loop_runtime


# Product-level economy layers sit outside the authored race/quest runtimes.
# Trade is installed first so the economy command shell remains the outer prompt
# while player movement still flows through trade and can invalidate open deals.
install_trade_experience_runtime(PlayerSession)
install_economy_loop_runtime(PlayerSession, WORLD)


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
