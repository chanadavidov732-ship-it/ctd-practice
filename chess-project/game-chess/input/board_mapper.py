class BoardMapper:
    def __init__(self, board, square_size=100):
        self.board = board
        self.square_size = square_size

    def pixel_to_cell(self, x, y):
        col = x // self.square_size
        row = y // self.square_size
        pos = (col, row)
        if not self.board.is_inside(pos):
            return None
        return pos