import asyncio
import getpass
import logging

from client.network.connection import ServerConnection
from shared.protocol import Envelope

logger = logging.getLogger("client")

SERVER_URI = "ws://127.0.0.1:8000/ws"


async def do_login(connection: ServerConnection) -> bool:
    choice = input("1) Login  2) Register\n> ").strip()
    action = "register" if choice == "2" else "login"

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    await connection.send(Envelope(type=action, payload={"username": username, "password": password}))
    response = await connection.receive()

    success = bool(response.payload.get("success"))
    if success:
        print(f"{action} succeeded: {response.payload.get('message')}")
        if "rating" in response.payload:
            print(f"rating: {response.payload['rating']}")
    else:
        print(f"{action} failed: {response.payload.get('message')}")

    return success


async def _standalone() -> None:
    connection = ServerConnection(SERVER_URI)
    await connection.connect()
    try:
        await do_login(connection)
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(_standalone())
