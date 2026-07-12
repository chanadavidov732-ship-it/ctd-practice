class GameState:
    def __init__(self):
        self.clock = 0
        self.pending_moves = []   # list of dicts: from, to, token, completion_time
        self.locked = set()       # positions (col, row) שנמצאים כרגע באמצע תנועה