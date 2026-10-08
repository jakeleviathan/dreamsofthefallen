"""Run the Lanternkeeper billing listener separately from the game server.

Use the Stripe-enabled virtual environment and the same MUD_DB_PATH as the game.
The listener must only bind to 127.0.0.1 and be exposed through Caddy.
"""
import os
import signal
import threading

from mud.lanternkeeper_http import start_lanternkeeper_http


def main():
    # An isolated staging worker can bind a different local port.
    # Production defaults to 8766, which is the existing Caddy upstream.
    port = int(os.environ.get("DOTF_BILLING_PORT", "8766"))
    if not 1 <= port <= 65535:
        raise ValueError("DOTF_BILLING_PORT must be between 1 and 65535")
    server = start_lanternkeeper_http(host="127.0.0.1", port=port)
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
