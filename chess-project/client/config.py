import pathlib

# --- Network ------------------------------------------------------------
SERVER_URI = "ws://127.0.0.1:8000/ws"

# --- Renderer: window / canvas -------------------------------------------
BOARD_IMAGE_PATH = pathlib.Path(__file__).parent / "ui" / "game_snapshot" / "board.png"
WINDOW_NAME = "Image"
FRAME_DELAY_MS = 30
ESC_KEY = 27
QUIT_KEYS = (ESC_KEY, ord("q"))

# --- Renderer: selection highlight ---------------------------------------
SELECTION_COLOR = (0, 255, 255, 255)
SELECTION_THICKNESS = 3

# --- Renderer: game-over overlay -----------------------------------------
GAME_OVER_TEXT = "GAME OVER"
GAME_OVER_COLOR = (0, 0, 255, 255)
GAME_OVER_FONT_SIZE = 2
GAME_OVER_TEXT_X_OFFSET = 130

BACK_TO_MENU_TEXT = "Back to Menu"
BACK_TO_MENU_BUTTON_WIDTH = 220
BACK_TO_MENU_BUTTON_HEIGHT = 50
BACK_TO_MENU_BUTTON_Y_OFFSET = 40

# --- Renderer: disconnect countdown --------------------------------------
DISCONNECT_TEXT_COLOR = (0, 165, 255, 255)
DISCONNECT_FONT_SIZE = 0.55

# --- Renderer: move-history side panels -----------------------------------
PANEL_WIDTH = 220
PANEL_BG_COLOR = (40, 40, 40, 255)
PANEL_TITLE_COLOR = (0, 255, 255, 255)
PANEL_TEXT_COLOR = (255, 255, 255, 255)
PANEL_TITLE_FONT_SIZE = 0.6
PANEL_LINE_FONT_SIZE = 0.45
PANEL_LINE_HEIGHT = 22
PANEL_FIRST_LINE_Y_OFFSET = 55

# --- Renderer: header / footer name bars ----------------------------------
HEADER_HEIGHT = 60
FOOTER_HEIGHT = 60
NAME_COLOR = (255, 255, 255, 255)
NAME_FONT_SIZE = 0.8

# --- Renderer: player-name prompt -----------------------------------------
DEFAULT_WHITE_NAME = "White"
DEFAULT_BLACK_NAME = "Black"
CARRIAGE_RETURN_KEY = 13
LINE_FEED_KEY = 10
ENTER_KEYS = (CARRIAGE_RETURN_KEY, LINE_FEED_KEY)
BACKSPACE_KEY = 8

# --- Renderer: rest countdown bar -----------------------------------------
REST_BAR_HEIGHT = 8
REST_BAR_BG_COLOR = (20, 20, 20, 255)
REST_BAR_FULL_COLOR = (0, 0, 255, 255)
REST_BAR_EMPTY_COLOR = (0, 255, 0, 255)

# --- Renderer: jump animation ----------------------------------------------
JUMP_LIFT_PX = 40
