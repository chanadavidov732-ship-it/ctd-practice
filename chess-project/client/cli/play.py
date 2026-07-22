import asyncio
import contextlib

from client.network.connection import ServerConnection
from shared.protocol import Envelope


async def run_play_menu(connection: ServerConnection) -> None:
    await connection.send(Envelope(type="play", payload={}))
    response = await connection.receive()
    payload = response.payload

    if payload.get("success") is False:
        print(f"could not queue for a match: {payload.get('message')}")
        return

    print(f"Queued for a match (rating: {payload.get('rating')})... (type 'cancel' to leave)")
    await _wait_for_match(connection)


async def _wait_for_match(connection: ServerConnection) -> None:
    matched = False

    async def listen_for_match() -> None:
        nonlocal matched
        while True:
            envelope = await connection.receive()
            if envelope.type == "match_found":
                opponent = envelope.payload
                print(
                    f"Match found! Opponent: {opponent.get('opponent_username')} "
                    f"(rating: {opponent.get('opponent_rating')})"
                )
                matched = True
                return
            if envelope.type == "match_timeout":
                print("No opponent found within 60 seconds.")
                matched = True
                return

    listen_task = asyncio.create_task(listen_for_match())
    try:
        while not matched:
            cmd = await asyncio.to_thread(input, "> ")
            if matched:
                break
            if cmd.strip().lower() == "cancel":
                break
    finally:
        listen_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listen_task

    if matched:
        return

    await connection.send(Envelope(type="cancel_play", payload={}))
    response = await connection.receive()
    print(f"server: {response.payload}")
