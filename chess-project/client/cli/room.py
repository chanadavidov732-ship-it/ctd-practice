import asyncio
import contextlib

from client.network.connection import ServerConnection
from shared.protocol import Envelope


async def run_room_menu(connection: ServerConnection) -> None:
    choice = input("1) Create  2) Join\n> ").strip()

    if choice == "2":
        room_id = input("Room ID: ").strip()
        await connection.send(Envelope(type="join_room", payload={"room_id": room_id}))
    else:
        await connection.send(Envelope(type="create_room", payload={}))

    response = await connection.receive()
    payload = response.payload

    if payload.get("success") is False:
        print(f"could not join room: {payload.get('message')}")
        return

    room_id = payload["room_id"]
    role = payload["role"]
    print(f"Room ID: {room_id}  (role: {role})")
    await _wait_in_room(connection, room_id)


async def _wait_in_room(connection: ServerConnection, room_id: str) -> None:
    print("Waiting for other participants... (type 'cancel' to leave)")

    async def listen_broadcasts() -> None:
        while True:
            envelope = await connection.receive()
            if envelope.type == "room_state":
                print(f"room update: {envelope.payload}")

    listen_task = asyncio.create_task(listen_broadcasts())
    try:
        while True:
            cmd = await asyncio.to_thread(input, "> ")
            if cmd.strip().lower() == "cancel":
                break
    finally:
        listen_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listen_task

    await connection.send(Envelope(type="cancel_room", payload={"room_id": room_id}))
    response = await connection.receive()
    print(f"server: {response.payload}")
