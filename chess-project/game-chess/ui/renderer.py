import pathlib

import cv2

from ui.img import Img
from ui.sprite_manager import SpriteManager

BOARD_IMAGE_PATH = pathlib.Path(__file__).parent / "game_snapshot" / "board.png"
WINDOW_NAME = "Image"
SELECTION_COLOR = (0, 255, 255)
SELECTION_THICKNESS = 3
FRAME_DELAY_MS = 30
QUIT_KEYS = (27, ord("q"))


class Renderer:
    def __init__(self, board, controller, game_engine, square_size=100):
        self.board = board
        self.controller = controller
        self.game_engine = game_engine
        self.square_size = square_size
        self.sprite_manager = SpriteManager(square_size)
        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, self._on_mouse)

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.controller.handle_click(x, y)
        elif event == cv2.EVENT_LBUTTONDBLCLK:
            self.controller.handle_jump(x, y)

    def render(self):
        """Draws one frame. Returns False once the user asked to quit (window closed)."""
        key = self._draw_frame()
        if key in QUIT_KEYS:
            cv2.destroyAllWindows()
            return False
        return True

    def _draw_frame(self):
        width = self.board.width * self.square_size
        height = self.board.height * self.square_size
        board_img = Img().read(BOARD_IMAGE_PATH, size=(width, height))
        self._draw_pieces(board_img)
        self._draw_selection(board_img)
        cv2.imshow(WINDOW_NAME, board_img.img)
        return cv2.waitKey(FRAME_DELAY_MS)

    def _draw_pieces(self, board_img):
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

                sprite.draw_on(board_img, x, y)

    def _interpolated_pixel(self, move, game_state):
        duration = move["duration"]
        elapsed = duration - (move["completion_time"] - game_state.clock)
        progress = 0.0 if duration <= 0 else max(0.0, min(1.0, elapsed / duration))

        from_x, from_y = move["from"][0] * self.square_size, move["from"][1] * self.square_size
        to_x, to_y = move["to"][0] * self.square_size, move["to"][1] * self.square_size

        x = from_x + (to_x - from_x) * progress
        y = from_y + (to_y - from_y) * progress
        return int(x), int(y)

    def _draw_selection(self, board_img):
        if self.controller.selected is None:
            return
        col, row = self.controller.selected["pos"]
        x = col * self.square_size
        y = row * self.square_size
        cv2.rectangle(
            board_img.img,
            (x, y),
            (x + self.square_size, y + self.square_size),
            SELECTION_COLOR,
            SELECTION_THICKNESS,
        )
