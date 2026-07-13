from model.piece import token_type
from rules import rule_engine
from realtime.motion import calculate_duration, DEFAULT_SPEED
from model.piece import token_type, token_color
from model.piece import token_type, token_color   # token_type כבר בשימוש; ודא ששניהם מיובאים
from realtime.motion import calculate_duration, DEFAULT_SPEED, JUMP_DURATION_MS   # CHANGED: added JUMP_DURATION_MS import

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

        # 2. האם קיימת כבר תנועה פעילה כלשהי על הלוח? (משאב "route" משותף)
        if self.game_state.locked:          # CHANGED: היה "if from_pos in self.game_state.locked:"
            return

        # 2. האם יש כבר תנועה פעילה על הכלי הזה?
        if from_pos in self.game_state.locked:
            return

        # 3. האם ה-Rule Engine מאשר?
        token = self.board.get_piece(from_pos)
        piece_type = token_type(token)
        piece_color = token_color(token)
        result = rule_engine.check_move(self.board, piece_type, piece_color, from_pos, to_pos)
        if result != rule_engine.OK:
            return

        # 4. התחלת Motion
        token = self.board.get_piece(from_pos)
        duration = calculate_duration(from_pos, to_pos, self.speed)
        completion_time = self.game_state.clock + duration
        self.arbiter.start_motion(from_pos, to_pos, token, completion_time)

    def advance_time(self, ms):
        settled = self.arbiter.advance_time(ms)   # CHANGED: כעת משתמשים בערך המוחזר
        for move in settled:
            if token_type(move["captured_token"]) == "K":   # ADDED: בדיקת לכידת מלך
                self.is_over = True
    
    def request_jump(self, pos):                              # ADDED
        if self.is_over:
            return
        if pos in self.game_state.locked:                      # ADDED: כלל 5 - כלי בתנועה לא יכול לקפוץ
            return
        if pos in self.game_state.airborne:                     # ADDED: כלי שכבר באוויר לא קופץ שוב
            return
        if self.board.get_piece(pos) == ".":                    # ADDED: כלל 6 - אין כלי לקפוץ (כבר נלכד/ריק)
            return
        self.arbiter.start_jump(pos)                            # ADDED