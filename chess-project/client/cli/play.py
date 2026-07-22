import asyncio
import contextlib

from client.network.connection import ServerConnection
from client.network.game_bridge import GameBridge, build_remote_engine, pump_game_messages
from shared.protocol import Envelope


async def run_play_menu(connection: ServerConnection, bridge: GameBridge) -> None:
    await connection.send(Envelope(type="play", payload={}))
    response = await connection.receive()
    payload = response.payload

    if payload.get("success") is False:
        print(f"could not queue for a match: {payload.get('message')}")
        return

    print(f"Queued for a match (rating: {payload.get('rating')})... (type 'cancel' to leave)")
    await _wait_for_match(connection, bridge)


async def _wait_for_match(connection: ServerConnection, bridge: GameBridge) -> None:
    resolved = False
    game_started_payload = None

    async def listen_for_match() -> None:
        nonlocal resolved, game_started_payload
        while True:
            envelope = await connection.receive()
            if envelope.type == "match_found":
                opponent = envelope.payload
                print(
                    f"Match found! Opponent: {opponent.get('opponent_username')} "
                    f"(rating: {opponent.get('opponent_rating')})"
                )
            elif envelope.type == "game_started":
                game_started_payload = envelope.payload
                resolved = True
                return
            elif envelope.type == "match_timeout":
                print("No opponent found within 60 seconds.")
                resolved = True
                return

    listen_task = asyncio.create_task(listen_for_match())
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

    if resolved:
        return  # match_timeout

    await connection.send(Envelope(type="cancel_play", payload={}))
    response = await connection.receive()
    print(f"server: {response.payload}")
