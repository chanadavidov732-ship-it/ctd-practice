import asyncio
import getpass
import logging

from client.network.connection import ServerConnection
from shared.protocol import Envelope

logger = logging.getLogger("client")

SERVER_URI = "ws://127.0.0.1:8000/ws"


async def run_login() -> None:
    connection = ServerConnection(SERVER_URI)
    await connection.connect()
    try:
        choice = input("1) Login  2) Register\n> ").strip()
        action = "register" if choice == "2" else "login"

        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")

        await connection.send(Envelope(type=action, payload={"username": username, "password": password}))
        response = await connection.receive()

        if response.payload.get("success"):
            print(f"{action} succeeded: {response.payload.get('message')}")
            if "rating" in response.payload:
                print(f"rating: {response.payload['rating']}")
        else:
            print(f"{action} failed: {response.payload.get('message')}")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run_login())
