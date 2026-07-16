import pathlib

import cv2

from ui.img import Img

DEFAULT_BOARD_IMAGE = pathlib.Path(__file__).parent / "game_snapshot" / "board.png"
WINDOW_NAME = "Image"  # matches the window name Img.show() opens internally


class Renderer:
    """Draws the screen from a snapshot; owns mouse input but never calls the engine."""

    def __init__(self, sprite_manager, board_mapper, board_image_path=DEFAULT_BOARD_IMAGE, square_size=100):
        self.sprite_manager = sprite_manager
        self.board_mapper = board_mapper
        self.board_image_path = board_image_path
        self.square_size = square_size

        self._last_click = None

        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, self._on_mouse)

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self._last_click = self.board_mapper.pixel_to_cell(x, y)

    def get_click(self):
        click = self._last_click
        self._last_click = None
        return click

    def _cell_center(self, pos):
        col, row = pos
        return (col * self.square_size + self.square_size // 2,
                row * self.square_size + self.square_size // 2)

    def render(self, snapshot):
        board = self.board_mapper.board
        board_size = (board.width * self.square_size, board.height * self.square_size)
        frame = Img().read(self.board_image_path, size=board_size)

        for piece in snapshot.get("pieces", []):
            sprite = self.sprite_manager.get_sprite(
                piece["token"],
                piece.get("is_airborne", False),
                piece.get("is_moving", False),
                piece.get("rest_remaining_ms", 0),
                piece.get("elapsed_ms", 0),
            )
            sprite_h, sprite_w = sprite.img.shape[:2]
            cx, cy = self._cell_center(piece["pos"])
            x, y = cx - sprite_w // 2, cy - sprite_h // 2
            sprite.draw_on(frame, x, y)

        board_bottom = board.height * self.square_size
        board_right = board.width * self.square_size

        frame.put_text(snapshot.get("player_name", ""), 10, 20, 0.6)
        frame.put_text(snapshot.get("opponent_name", ""), 10, board_bottom + 20, 0.6)

        for i, entry in enumerate(snapshot.get("player_moves", [])):
            frame.put_text(entry, 10, 40 + i * 20, 0.5)

        for i, entry in enumerate(snapshot.get("opponent_moves", [])):
            frame.put_text(entry, board_right + 10, 40 + i * 20, 0.5)

        frame.show()
