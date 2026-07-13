from model.piece import token_color

class Controller:
    def __init__(self, board, board_mapper, game_engine):
        self.board = board
        self.board_mapper = board_mapper
        self.game_engine = game_engine
        self.selected = None 

    def handle_click(self, x, y):
        pos = self.board_mapper.pixel_to_cell(x, y)

        if pos is None:
            self.selected = None
            return

        if self.game_engine.is_locked(pos):
            return    

        token = self.board.get_piece(pos)
        color = token_color(token)

        if self.selected is None:
            if color is not None:
                self.selected = {"pos": pos, "color": color}
            return

        if color is not None and color == self.selected["color"]:
            self.selected = {"pos": pos, "color": color}
            return

        from_pos = self.selected["pos"]
        self.selected = None
        self.game_engine.request_move(from_pos, pos)

    def handle_jump(self, x, y):
        pos = self.board_mapper.pixel_to_cell(x, y)
        if pos is None:
            return
        self.game_engine.request_jump(pos)