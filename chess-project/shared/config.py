from shared.rules.piece_rules import (
    _validate_king,
    _validate_queen,
    _validate_rook,
    _validate_bishop,
    _validate_knight,
)

# --- Piece registry -----------------------------------------------------
KING = "K"
QUEEN = "Q"
ROOK = "R"
BISHOP = "B"
KNIGHT = "N"
PAWN = "P"
PIECE_TYPES = {KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN}

WHITE = "w"
BLACK = "b"
COLORS = {WHITE, BLACK}

# --- Movement validators registry ----------------------------------------
MOVEMENT_VALIDATORS = {
    KING: _validate_king,
    QUEEN: _validate_queen,
    ROOK: _validate_rook,
    BISHOP: _validate_bishop,
    KNIGHT: _validate_knight,
}

# --- Board -------------------------------------------------------------
EMPTY_CELL = "."

# --- Move dict field names -------------------------------------------------
MOVE_FROM_KEY = "from"
MOVE_TO_KEY = "to"
MOVE_TOKEN_KEY = "token"
MOVE_COMPLETION_TIME_KEY = "completion_time"
MOVE_DURATION_KEY = "duration"
CAPTURED_TOKEN_KEY = "captured_token"

# --- Game snapshot field names (server<->client wire payload) --------------
CLOCK_KEY = "clock"
LOCKED_KEY = "locked"
PENDING_MOVES_KEY = "pending_moves"
RESTING_KEY = "resting"
RESTING_DURATION_KEY = "duration"
RESTING_UNTIL_KEY = "until"
AIRBORNE_KEY = "airborne"
SETTLED_MOVES_KEY = "settled_moves"
CAPTURED_KEY = "captured"
POS_KEY = "pos"
WHITE_USERNAME_KEY = "white_username"
BLACK_USERNAME_KEY = "black_username"
YOUR_COLOR_KEY = "your_color"

# --- Envelope message types -------------------------------------------------
MSG_ECHO = "echo"
MSG_LOGIN = "login"
MSG_REGISTER = "register"
MSG_MENU_SELECT = "menu_select"
MSG_CREATE_ROOM = "create_room"
MSG_JOIN_ROOM = "join_room"
MSG_CANCEL_ROOM = "cancel_room"
MSG_PLAY = "play"
MSG_CANCEL_PLAY = "cancel_play"
MSG_MOVE = "move"
MSG_JUMP = "jump"
MSG_ROOM_STATE = "room_state"
MSG_GAME_STARTED = "game_started"
MSG_GAME_UPDATE = "game_update"
MSG_GAME_OVER = "game_over"
MSG_DISCONNECT_COUNTDOWN = "disconnect_countdown"
MSG_MOVE_REJECTED = "move_rejected"
MSG_JUMP_REJECTED = "jump_rejected"
MSG_MATCH_FOUND = "match_found"
MSG_MATCH_TIMEOUT = "match_timeout"
MSG_PLAY_CANCELLED = "play_cancelled"
MSG_PLAY_QUEUED = "play_queued"

# --- Home-menu choices (menu_select payload's "choice" value) ---------------
MENU_CHOICE_PLAY = "play"
MENU_CHOICE_ROOM = "room"

# --- Matchmaking -------------------------------------------------------------
MATCH_TIMEOUT_SECONDS = 60

# --- Rooms ---------------------------------------------------------------
MAX_ROOM_PLAYERS = 2
