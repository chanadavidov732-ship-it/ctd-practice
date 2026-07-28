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
from shared.config import (
    MSG_CANCEL_PLAY,
    MSG_CANCEL_ROOM,
    MSG_CREATE_ROOM,
    MSG_ECHO,
    MSG_JOIN_ROOM,
    MSG_JUMP,
    MSG_LOGIN,
    MSG_MENU_SELECT,
    MSG_MOVE,
    MSG_PLAY,
    MSG_PLAY_CANCELLED,
    MSG_REGISTER,
    MSG_ROOM_STATE,
)

# --- Game session tick loop -------------------------------------------------
TICK_MS = 100
TICK_INTERVAL_SECONDS = TICK_MS / 1000
DISCONNECT_RESIGN_SECONDS = 20

# --- Rating -------------------------------------------------------------
DEFAULT_RATING = 1200
WIN_BONUS_POINTS = 100
LOSS_PENALTY_POINTS = 30
CAPTURE_BONUS_POINTS = 2

# --- Matchmaking --------------------------------------------------------------
RATING_RANGE = 100

# --- Short random IDs (matches and rooms share the same shape) -------------
ID_ALPHABET = string.ascii_uppercase + string.digits
ID_LENGTH = 6

# --- Database / auth ------------------------------------------------------------
DB_PATH = pathlib.Path(__file__).parent / "db" / "chess.db"
SCHEMA_PATH = pathlib.Path(__file__).parent / "db" / "schema.sql"
PBKDF2_ITERATIONS = 200_000

# --- WebSocket routing ------------------------------------------------------------
RESPONSE_TYPE = {
    MSG_LOGIN: "login_result",
    MSG_REGISTER: "register_result",
    MSG_MENU_SELECT: "menu_ack",
    MSG_CREATE_ROOM: MSG_ROOM_STATE,
    MSG_CANCEL_ROOM: MSG_ROOM_STATE,
    MSG_CANCEL_PLAY: MSG_PLAY_CANCELLED,
}

HANDLERS = {
    MSG_ECHO: handle_echo,
    MSG_LOGIN: handle_login,
    MSG_REGISTER: handle_register,
    MSG_MENU_SELECT: handle_menu_select,
    MSG_CREATE_ROOM: handle_create_room,
    MSG_JOIN_ROOM: handle_join_room,
    MSG_CANCEL_ROOM: handle_cancel_room,
    MSG_PLAY: handle_play,
    MSG_CANCEL_PLAY: handle_cancel_play,
    MSG_MOVE: handle_move,
    MSG_JUMP: handle_jump,
}
