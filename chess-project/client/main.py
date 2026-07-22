import asyncio
import logging

from client.cli.home import run_home_menu
from client.cli.login import SERVER_URI, do_login
from client.network.connection import ServerConnection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main() -> None:
    connection = ServerConnection(SERVER_URI)
    await connection.connect()
    try:
        if await do_login(connection):
            await run_home_menu(connection)
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
