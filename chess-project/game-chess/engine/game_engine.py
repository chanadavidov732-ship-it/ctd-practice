from model.piece import token_type
from rules import rule_engine
from realtime.motion import calculate_duration, DEFAULT_SPEED


class GameEngine:

    def __init__(self, board, game_state, arbiter, speed=DEFAULT_SPEED):
        self.board = board
        self.game_state = game_state
        self.arbiter = arbiter
        self.speed = speed
        self.is_over = False

    def is_locked(self, pos):
        return pos in self.game_state.locked

    def request_move(self, from_pos, to_pos):
        # 1. האם המשחק נגמר?
        if self.is_over:
            return

        # 2. האם יש כבר תנועה פעילה על הכלי הזה?
        if from_pos in self.game_state.locked:
            return

        # 3. האם ה-Rule Engine מאשר?
        piece_type = token_type(self.board.get_piece(from_pos))
        result = rule_engine.check_move(self.board, piece_type, from_pos, to_pos)
        if result != rule_engine.OK:
            return

        # 4. התחלת Motion
        token = self.board.get_piece(from_pos)
        duration = calculate_duration(from_pos, to_pos, self.speed)
        completion_time = self.game_state.clock + duration
        self.arbiter.start_motion(from_pos, to_pos, token, completion_time)

    def advance_time(self, ms):
        self.arbiter.advance_time(ms)

