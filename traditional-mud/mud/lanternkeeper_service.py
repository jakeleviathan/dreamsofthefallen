"""Run the Lanternkeeper billing listener separately from the game server.

Use the Stripe-enabled virtual environment and the same MUD_DB_PATH as the game.
The listener must only bind to 127.0.0.1 and be exposed through Caddy.
"""
import signal
import threading

from mud.lanternkeeper_http import start_lanternkeeper_http


def main():
    server = start_lanternkeeper_http(host="127.0.0.1", port=8766)
    stopping = threading.Event()

    def stop(_signum, _frame):
        stopping.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        stopping.wait()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
