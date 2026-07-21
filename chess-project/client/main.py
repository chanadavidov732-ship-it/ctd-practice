import asyncio
import logging

from client.cli.login import run_login

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


if __name__ == "__main__":
    asyncio.run(run_login())
