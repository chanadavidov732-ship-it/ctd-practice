VALID_TOKENS = {
    ".", "wK", "wQ", "wR", "wB", "wN", "wP",
    "bK", "bQ", "bR", "bB", "bN", "bP"
}


def read_board():
    grid = []
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if line == "Board:":
            continue
        if line == "Commands:":
            break
        if line:
            grid.append(line.split())
    return grid


def validate_board(grid):
    if not grid:
        return "ERROR EMPTY_BOARD"
    width = len(grid[0])
    for row in grid:
        if len(row) != width:
            return "ERROR ROW_WIDTH_MISMATCH"
        for cell in row:
            if cell not in VALID_TOKENS:
                return "ERROR UNKNOWN_TOKEN"
    return None