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


class Game:
    def __init__(self, board):
        self.board = board
        self.height = len(board)
        self.width = len(board[0])
        self.square_size = 100
        self.speed = 200

        self.clock = 0
        self.selected = None
        self.pending_moves = []
        self.locked = set()

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

    def calculate_duration(self, from_pos, to_pos):
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)
        return distance * self.speed

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

        self.send_move_request(self.selected["pos"], pos)
        self.selected = None

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