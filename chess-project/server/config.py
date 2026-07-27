import pathlib
import string

from server.network.ws_routes import (
    handle_echo,
    handle_login,
    handle_register,
    handle_menu_select,
    handle_create_room,
    handle_join_room,
    handle_cancel_room,
    handle_play,
    handle_cancel_play,
    handle_move,
    handle_jump,
)

# --- Game session tick loop -------------------------------------------------
TICK_MS = 100
TICK_INTERVAL_SECONDS = TICK_MS / 1000
DISCONNECT_RESIGN_SECONDS = 20

# --- Rating (Elo) ------------------------------------------------------------
K_FACTOR = 32

# --- Matchmaking --------------------------------------------------------------
MATCH_ID_ALPHABET = string.ascii_uppercase + string.digits
MATCH_ID_LENGTH = 6
RATING_RANGE = 100

# --- Rooms ----------------------------------------------------------------------
ROOM_ID_ALPHABET = string.ascii_uppercase + string.digits
ROOM_ID_LENGTH = 6

# --- Database / auth ------------------------------------------------------------
DB_PATH = pathlib.Path(__file__).parent / "db" / "chess.db"
SCHEMA_PATH = pathlib.Path(__file__).parent / "db" / "schema.sql"
PBKDF2_ITERATIONS = 200_000

# --- WebSocket routing ------------------------------------------------------------
RESPONSE_TYPE = {
    "login": "login_result",
    "register": "register_result",
    "menu_select": "menu_ack",
    "create_room": "room_state",
    "cancel_room": "room_state",
    "cancel_play": "play_cancelled",
}

HANDLERS = {
    "echo": handle_echo,
    "login": handle_login,
    "register": handle_register,
    "menu_select": handle_menu_select,
    "create_room": handle_create_room,
    "join_room": handle_join_room,
    "cancel_room": handle_cancel_room,
    "play": handle_play,
    "cancel_play": handle_cancel_play,
    "move": handle_move,
    "jump": handle_jump,
}
