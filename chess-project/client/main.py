import asyncio
import logging

from client.network.connection import ServerConnection
from shared.protocol import Envelope

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("client")

SERVER_URI = "ws://127.0.0.1:8000/ws"


async def main():
    connection = ServerConnection(SERVER_URI)
    await connection.connect()
    print(f"Connected to {SERVER_URI}. Type a message and press Enter (type 'exit' to quit).")
    try:
        while True:
            text = await asyncio.to_thread(input, "> ")
            if text.strip().lower() == "exit":
                break
            envelope = Envelope(type="echo", payload={"text": text})
            await connection.send(envelope)
            response = await connection.receive()
            print(f"echo: {response.payload}")
    except (KeyboardInterrupt, EOFError):
        print("\nexiting...")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
