import pathlib

import cv2

from model.piece import token_color
from ui.img import Img
from ui.sprite_manager import SpriteManager

BOARD_IMAGE_PATH = pathlib.Path(__file__).parent / "game_snapshot" / "board.png"
WINDOW_NAME = "Image"
SELECTION_COLOR = (0, 255, 255, 255)
SELECTION_THICKNESS = 3
FRAME_DELAY_MS = 30
QUIT_KEYS = (27, ord("q"))
GAME_OVER_TEXT = "GAME OVER"
GAME_OVER_COLOR = (0, 0, 255, 255)
GAME_OVER_FONT_SIZE = 2

PANEL_WIDTH = 220
PANEL_BG_COLOR = (40, 40, 40, 255)
PANEL_TITLE_COLOR = (0, 255, 255, 255)
PANEL_TEXT_COLOR = (255, 255, 255, 255)
PANEL_TITLE_FONT_SIZE = 0.6
PANEL_LINE_FONT_SIZE = 0.45
PANEL_LINE_HEIGHT = 22
PANEL_FIRST_LINE_Y_OFFSET = 55

HEADER_HEIGHT = 60
FOOTER_HEIGHT = 60
NAME_COLOR = (255, 255, 255, 255)
NAME_FONT_SIZE = 0.8

DEFAULT_WHITE_NAME = "White"
DEFAULT_BLACK_NAME = "Black"
ENTER_KEYS = (13, 10)
BACKSPACE_KEY = 8


class Renderer:
    def __init__(self, board, controller, game_engine, move_history, square_size=100):
        self.board = board
        self.controller = controller
        self.game_engine = game_engine
        self.move_history = move_history
        self.square_size = square_size
        self.board_offset_x = PANEL_WIDTH
        self.board_offset_y = HEADER_HEIGHT
        self.player_name_white = DEFAULT_WHITE_NAME
        self.player_name_black = DEFAULT_BLACK_NAME
        self.sprite_manager = SpriteManager(square_size)
        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, self._on_mouse)

    def _on_mouse(self, event, x, y, flags, param):
        board_x = x - self.board_offset_x
        board_y = y - self.board_offset_y
        if event == cv2.EVENT_LBUTTONDOWN:
            self.controller.handle_click(board_x, board_y)
        elif event == cv2.EVENT_LBUTTONDBLCLK:
            self.controller.handle_jump(board_x, board_y)

    def prompt_player_names(self):
        """Blocks on this window, letting the user type each player's name before the game starts."""
        self.player_name_white = self._prompt_text(
            "Enter White player's name (Enter to confirm):", DEFAULT_WHITE_NAME
        )
        self.player_name_black = self._prompt_text(
            "Enter Black player's name (Enter to confirm):", DEFAULT_BLACK_NAME
        )

    def _prompt_text(self, prompt, default):
        canvas_width, canvas_height = self._canvas_size()
        text = ""
        while True:
            frame = Img().read(BOARD_IMAGE_PATH, size=(canvas_width, canvas_height))
            cv2.rectangle(frame.img, (0, 0), (canvas_width, canvas_height), PANEL_BG_COLOR, -1)
            frame.put_text(prompt, 40, canvas_height // 2 - 30, 0.7, NAME_COLOR, thickness=2)
            frame.put_text(text + "_", 40, canvas_height // 2 + 20, 0.9, NAME_COLOR, thickness=2)
            cv2.imshow(WINDOW_NAME, frame.img)

            key = cv2.waitKey(FRAME_DELAY_MS)
            if key in ENTER_KEYS:
                break
            elif key == BACKSPACE_KEY:
                text = text[:-1]
            elif key != -1 and 32 <= key <= 126:
                text += chr(key)

        return text.strip() or default

    def render(self):
        """Draws one frame. Returns False once the user asked to quit (window closed)."""
        key = self._draw_frame()
        if key in QUIT_KEYS:
            cv2.destroyAllWindows()
            return False
        return True

    def _canvas_size(self):
        board_width = self.board.width * self.square_size
        board_height = self.board.height * self.square_size
        canvas_width = self.board_offset_x + board_width + PANEL_WIDTH
        canvas_height = self.board_offset_y + board_height + FOOTER_HEIGHT
        return canvas_width, canvas_height

    def _draw_frame(self):
        board_width = self.board.width * self.square_size
        board_height = self.board.height * self.square_size
        canvas_width, canvas_height = self._canvas_size()

        canvas_img = Img().read(BOARD_IMAGE_PATH, size=(canvas_width, canvas_height))
        board_patch = Img().read(BOARD_IMAGE_PATH, size=(board_width, board_height))
        board_patch.draw_on(canvas_img, self.board_offset_x, self.board_offset_y)

        self._draw_pieces(canvas_img)
        self._draw_selection(canvas_img)
        self._draw_game_over(canvas_img)
        self._draw_history_panels(canvas_img)
        self._draw_names(canvas_img)
        cv2.imshow(WINDOW_NAME, canvas_img.img)
        return cv2.waitKey(FRAME_DELAY_MS)

    def _draw_pieces(self, canvas_img):
        game_state = self.game_engine.game_state
        moves_by_from = {move["from"]: move for move in game_state.pending_moves}

        for row in range(self.board.height):
            for col in range(self.board.width):
                pos = (col, row)
                token = self.board.get_piece(pos)
                if token == ".":
                    continue

                move = moves_by_from.get(pos)
                if move is not None:
                    sprite = self.sprite_manager.get_sprite_for_move(move, game_state)
                    x, y = self._interpolated_pixel(move, game_state)
                else:
                    sprite = self.sprite_manager.get_sprite_for_piece(token, pos, game_state)
                    x, y = col * self.square_size, row * self.square_size

                sprite.draw_on(canvas_img, self.board_offset_x + x, self.board_offset_y + y)

    def _interpolated_pixel(self, move, game_state):
        duration = move["duration"]
        elapsed = duration - (move["completion_time"] - game_state.clock)
        progress = 0.0 if duration <= 0 else max(0.0, min(1.0, elapsed / duration))

        from_x, from_y = move["from"][0] * self.square_size, move["from"][1] * self.square_size
        to_x, to_y = move["to"][0] * self.square_size, move["to"][1] * self.square_size

        x = from_x + (to_x - from_x) * progress
        y = from_y + (to_y - from_y) * progress
        return int(x), int(y)

    def _draw_game_over(self, canvas_img):
        if not self.game_engine.is_over:
            return
        board_width = self.board.width * self.square_size
        board_height = self.board.height * self.square_size
        canvas_img.put_text(
            GAME_OVER_TEXT,
            self.board_offset_x + board_width // 2 - 130,
            self.board_offset_y + board_height // 2,
            GAME_OVER_FONT_SIZE,
            GAME_OVER_COLOR,
            thickness=3,
        )

    def _draw_selection(self, canvas_img):
        if self.controller.selected is None:
            return
        col, row = self.controller.selected["pos"]
        x = self.board_offset_x + col * self.square_size
        y = self.board_offset_y + row * self.square_size
        cv2.rectangle(
            canvas_img.img,
            (x, y),
            (x + self.square_size, y + self.square_size),
            SELECTION_COLOR,
            SELECTION_THICKNESS,
        )

    def _draw_history_panels(self, canvas_img):
        board_width = self.board.width * self.square_size
        white_moves = [m for m in self.move_history if token_color(m["token"]) == "w"]
        black_moves = [m for m in self.move_history if token_color(m["token"]) == "b"]
        self._draw_panel(canvas_img, white_moves, 0, "White")
        self._draw_panel(canvas_img, black_moves, self.board_offset_x + board_width, "Black")

    def _draw_panel(self, canvas_img, moves, x_start, title):
        board_height = self.board.height * self.square_size
        y_start = self.board_offset_y
        y_end = self.board_offset_y + board_height
        cv2.rectangle(
            canvas_img.img,
            (x_start, y_start),
            (x_start + PANEL_WIDTH, y_end),
            PANEL_BG_COLOR,
            -1,
        )
        canvas_img.put_text(
            title, x_start + 10, y_start + 25, PANEL_TITLE_FONT_SIZE, PANEL_TITLE_COLOR, thickness=2
        )

        max_lines = max(0, (board_height - PANEL_FIRST_LINE_Y_OFFSET) // PANEL_LINE_HEIGHT)
        visible_moves = moves[-max_lines:] if max_lines else []

        y = y_start + PANEL_FIRST_LINE_Y_OFFSET
        for move in visible_moves:
            canvas_img.put_text(
                self._format_move(move),
                x_start + 10,
                y,
                PANEL_LINE_FONT_SIZE,
                PANEL_TEXT_COLOR,
            )
            y += PANEL_LINE_HEIGHT

    def _format_move(self, move):
        from_col, from_row = move["from"]
        to_col, to_row = move["to"]
        text = f"{move['token']} ({from_col},{from_row})->({to_col},{to_row})"
        if move.get("captured_token", ".") != ".":
            text += " x"
        return text

    def _draw_names(self, canvas_img):
        canvas_width, canvas_height = self._canvas_size()
        board_height = self.board.height * self.square_size
        footer_y = self.board_offset_y + board_height

        cv2.rectangle(canvas_img.img, (0, 0), (canvas_width, self.board_offset_y), PANEL_BG_COLOR, -1)
        cv2.rectangle(canvas_img.img, (0, footer_y), (canvas_width, canvas_height), PANEL_BG_COLOR, -1)

        self._draw_centered_text(canvas_img, self.player_name_white, canvas_width, self.board_offset_y - 18)
        self._draw_centered_text(canvas_img, self.player_name_black, canvas_width, footer_y + FOOTER_HEIGHT - 18)

    def _draw_centered_text(self, canvas_img, text, canvas_width, y):
        (text_width, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, NAME_FONT_SIZE, 2)
        x = (canvas_width - text_width) // 2
        canvas_img.put_text(text, x, y, NAME_FONT_SIZE, NAME_COLOR, thickness=2)
