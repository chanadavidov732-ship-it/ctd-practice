import asyncio
import logging

from client.config import SERVER_URI
from client.network.connection import ServerConnection
from shared.config import MSG_LOGIN, MSG_REGISTER
from shared.protocol import Envelope

logger = logging.getLogger("client")


async def do_login(connection: ServerConnection) -> bool:
    choice = input("1) Login  2) Register\n> ").strip()
    action = MSG_REGISTER if choice == "2" else MSG_LOGIN

    username = input("Username: ").strip()
    password = input("Password: ").strip()

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
