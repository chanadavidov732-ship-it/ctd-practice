from client.cli.play import run_play_menu
from client.cli.room import run_room_menu
from client.network.connection import ServerConnection
from shared.protocol import Envelope

MENU_CHOICES = {
    "1": "play",
    "2": "room",
}


async def run_home_menu(connection: ServerConnection) -> None:
    while True:
        raw_choice = input("1) Play  2) Room  (or 'exit')\n> ").strip().lower()
        if raw_choice in ("exit", "quit"):
            return

        choice = MENU_CHOICES.get(raw_choice)
        if choice is None:
            print("invalid choice")
            continue

        await connection.send(Envelope(type="menu_select", payload={"choice": choice}))
        response = await connection.receive()
        print(f"server: {response.payload}")

        if choice == "room":
            await run_room_menu(connection)
        elif choice == "play":
            await run_play_menu(connection)
