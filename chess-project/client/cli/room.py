import asyncio
import contextlib

from client.network.connection import ServerConnection
from client.network.game_bridge import GameBridge, build_remote_engine, pump_game_messages
from shared.protocol import Envelope


async def run_room_menu(connection: ServerConnection, bridge: GameBridge) -> None:
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
    await _wait_in_room(connection, room_id, bridge)


async def _wait_in_room(connection: ServerConnection, room_id: str, bridge: GameBridge) -> None:
    print("Waiting for other participants... (type 'cancel' to leave)")

    resolved = False
    game_started_payload = None

    async def listen_broadcasts() -> None:
        nonlocal resolved, game_started_payload
        while True:
            envelope = await connection.receive()
            if envelope.type == "room_state":
                print(f"room update: {envelope.payload}")
            elif envelope.type == "game_started":
                # Only players (the 2 that fill the room) get "game_started";
                # viewers stay on the CLI room screen for this iteration.
                game_started_payload = envelope.payload
                resolved = True
                return

    listen_task = asyncio.create_task(listen_broadcasts())
    try:
        while not resolved:
            cmd = await asyncio.to_thread(input, "> ")
            if resolved:
                break
            if cmd.strip().lower() == "cancel":
                break
    finally:
        listen_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listen_task

    if game_started_payload is not None:
        print("Game started -- opening the board window...")
        engine = build_remote_engine(connection, game_started_payload)
        bridge.notify_game_started(engine)
        await pump_game_messages(connection, engine)
        return

    await connection.send(Envelope(type="cancel_room", payload={"room_id": room_id}))
    response = await connection.receive()
    print(f"server: {response.payload}")
