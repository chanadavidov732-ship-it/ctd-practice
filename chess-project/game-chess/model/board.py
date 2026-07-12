class Board:
    def __init__(self, grid):
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0]) if grid else 0

    def get_piece(self, pos):
        col, row = pos
        return self.grid[row][col]

    def set_piece(self, pos, token):
        col, row = pos
        self.grid[row][col] = token

    def is_inside(self, pos):
        col, row = pos
        return 0 <= col < self.width and 0 <= row < self.height