
import math

VALID_TOKENS = {
    ".", "wK", "wQ", "wR", "wB", "wN", "wP",
    "bK", "bQ", "bR", "bB", "bN", "bP"
}


def read_board():
    board = []
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
            board.append(line.split())
    return board


def validate_board(board):
    if not board:
        return "ERROR EMPTY_BOARD"
    width = len(board[0])
    for row in board:
        if len(row) != width:
            return "ERROR ROW_WIDTH_MISMATCH"
        for cell in row:
            if cell not in VALID_TOKENS:
                return "ERROR UNKNOWN_TOKEN"
    return None


def print_board(board):
    for row in board:
        print(" ".join(row))


# ---------- movement shape validation (Strategy per piece type) ----------

def _is_straight_line(dx, dy):
    return (dx == 0) != (dy == 0)  # exactly one of them is zero


def _is_diagonal(dx, dy):
    return dx != 0 and abs(dx) == abs(dy)


def _validate_king(dx, dy):
    return max(abs(dx), abs(dy)) == 1


def _validate_rook(dx, dy):
    return _is_straight_line(dx, dy)


def _validate_bishop(dx, dy):
    return _is_diagonal(dx, dy)


def _validate_queen(dx, dy):
    return _is_straight_line(dx, dy) or _is_diagonal(dx, dy)


def _validate_knight(dx, dy):
    return (abs(dx), abs(dy)) in {(1, 2), (2, 1)}


def _validate_pawn(dx, dy):
    return True


MOVEMENT_VALIDATORS = {
    "K": _validate_king,
    "Q": _validate_queen,
    "R": _validate_rook,
    "B": _validate_bishop,
    "N": _validate_knight,
    "P": _validate_pawn,
}


def is_legal_move(piece_type, from_pos, to_pos):
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    validator = MOVEMENT_VALIDATORS.get(piece_type)
    if validator is None:
        return False
    return validator(dx, dy)


class Game:
    def __init__(self, board):
        self.board = board
        self.height = len(board)
        self.width = len(board[0])
        self.square_size = 100
        self.speed = 200  # ms per square (euclidean distance)

        self.clock = 0
        self.selected = None  # {"pos": (col, row), "color": "w"/"b"}
        self.pending_moves = []  # list of dicts: from, to, token, completion_time
        self.locked = set()  # positions (col, row) currently mid-move

    # ---------- helpers ----------

    def get_piece(self, pos):
        col, row = pos
        return self.board[row][col]

    def set_piece(self, pos, token):
        col, row = pos
        self.board[row][col] = token

    def is_inside(self, pos):
        col, row = pos
        return 0 <= col < self.width and 0 <= row < self.height

    def pixel_to_cell(self, x, y):
        col = x // self.square_size
        row = y // self.square_size
        pos = (col, row)
        if not self.is_inside(pos):
            return None
        return pos

    @staticmethod
    def token_color(token):
        if token == ".":
            return None
        return token[0]

    @staticmethod
    def token_type(token):
        if token == ".":
            return None
        return token[1]

    def calculate_duration(self, from_pos, to_pos):
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)
        return distance * self.speed

    # ---------- commands ----------

    def handle_click(self, x, y):
        pos = self.pixel_to_cell(x, y)
        if pos is None:
            return

        if pos in self.locked:
            return

        token = self.get_piece(pos)
        color = self.token_color(token)

        if self.selected is None:
            if color is not None:
                self.selected = {"pos": pos, "color": color}
            return

        if color is not None and color == self.selected["color"]:
            self.selected = {"pos": pos, "color": color}
            return

        from_pos = self.selected["pos"]
        piece_type = self.token_type(self.get_piece(from_pos))
        self.selected = None

        if is_legal_move(piece_type, from_pos, pos):
            self.send_move_request(from_pos, pos)

    def handle_wait(self, ms):
        self.clock += ms
        self.settle_due_moves()

    def send_move_request(self, from_pos, to_pos):
        token = self.get_piece(from_pos)
        duration = self.calculate_duration(from_pos, to_pos)
        completion_time = self.clock + duration

        self.pending_moves.append({
            "from": from_pos,
            "to": to_pos,
            "token": token,
            "completion_time": completion_time
        })
        self.locked.add(from_pos)

    def settle_due_moves(self):
        due = [m for m in self.pending_moves if m["completion_time"] <= self.clock]
        due.sort(key=lambda m: m["completion_time"])

        for move in due:
            self.set_piece(move["from"], ".")
            self.set_piece(move["to"], move["token"])
            self.locked.discard(move["from"])
            self.pending_moves.remove(move)

    def print_board(self):
        print_board(self.board)


def run_commands(game):
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if not line:
            continue

        parts = line.split()
        cmd = parts[0]

        if cmd == "click" and len(parts) == 3:
            x, y = int(parts[1]), int(parts[2])
            game.handle_click(x, y)
        elif cmd == "wait" and len(parts) == 2:
            ms = int(parts[1])
            game.handle_wait(ms)
        elif line == "print board":
            game.print_board()