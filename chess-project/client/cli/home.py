from client.cli.play import run_play_menu
from client.cli.room import run_room_menu
from client.network.connection import ServerConnection
from client.network.game_bridge import GameBridge
from shared.config import MENU_CHOICE_PLAY, MENU_CHOICE_ROOM, MSG_MENU_SELECT
from shared.protocol import Envelope

MENU_CHOICES = {
    "1": MENU_CHOICE_PLAY,
    "2": MENU_CHOICE_ROOM,
}


async def run_home_menu(connection: ServerConnection, bridge: GameBridge) -> None:
    while True:
        raw_choice = input("1) Play  2) Room  (or 'exit')\n> ").strip().lower()
        if raw_choice in ("exit", "quit"):
            return

        choice = MENU_CHOICES.get(raw_choice)
        if choice is None:
            print("invalid choice")
            continue

        await connection.send(Envelope(type=MSG_MENU_SELECT, payload={"choice": choice}))
        response = await connection.receive()
        print(f"server: {response.payload}")

        if choice == MENU_CHOICE_ROOM:
            await run_room_menu(connection, bridge)
        elif choice == MENU_CHOICE_PLAY:
            await run_play_menu(connection, bridge)
