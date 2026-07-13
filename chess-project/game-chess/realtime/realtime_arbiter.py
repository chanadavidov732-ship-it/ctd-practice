from model.piece import token_type, token_color
from rules.piece_rules import pawn_promotion_row
from realtime.motion import JUMP_DURATION_MS   # ADDED

class RealTimeArbiter:
    def __init__(self, board, game_state):
        self.board = board
        self.game_state = game_state

    def start_motion(self, from_pos, to_pos, token, completion_time):
        self.game_state.pending_moves.append({
            "from": from_pos,
            "to": to_pos,
            "token": token,
            "completion_time": completion_time
        })
        self.game_state.locked.add(from_pos)

    def advance_time(self, ms):
        """מקדם את הזמן הלוגי ומיישב תנועות שהגיעו ליעדן."""
        self.game_state.clock += ms
        return self._settle_due_moves()
     
    def _settle_due_moves(self):
        due = [m for m in self.game_state.pending_moves
               if m["completion_time"] <= self.game_state.clock]
        due.sort(key=lambda m: m["completion_time"])

        settled = []
        for move in due:
            # ADDED: כלל 3 - תפיסה באוויר, קודמת ליישוב הרגיל
            if move["to"] in self.game_state.airborne:
                defender_token = self.board.get_piece(move["to"])
                if token_color(defender_token) != token_color(move["token"]):
                    self.board.set_piece(move["from"], ".")     # הכלי התוקף מוסר מהמקור
                    # אין עדכון ל-move["to"] - הכלי שבאוויר נשאר במקומו, לא זז
                    self.game_state.locked.discard(move["from"])
                    self.game_state.pending_moves.remove(move)
                    move["captured_token"] = move["token"]       # הכלי שהגיע הוא זה שנלכד
                    move["air_capture"] = True
                    settled.append(move)
                    continue

            captured_token = self.board.get_piece(move["to"])

            arriving_token = move["token"]
            piece_type = token_type(arriving_token)
            piece_color = token_color(arriving_token)
            dest_row = move["to"][1]
            if piece_type == "P" and dest_row == pawn_promotion_row(piece_color, self.board.height):
                arriving_token = piece_color + "Q"

            self.board.set_piece(move["from"], ".")
            self.board.set_piece(move["to"], arriving_token)
            self.game_state.locked.discard(move["from"])
            self.game_state.pending_moves.remove(move)

            move["captured_token"] = captured_token
            settled.append(move)

        return settled
    
    def start_jump(self, pos):                                  # ADDED
        self.game_state.airborne[pos] = self.game_state.clock + JUMP_DURATION_MS

    def advance_time(self, ms):
        self.game_state.clock += ms
        settled = self._settle_due_moves()
        self._land_due_jumps()                                  # ADDED: נחיתה מתבצעת אחרי יישוב המהלכים
        return settled

    def _land_due_jumps(self):                                  # ADDED
        due_positions = [pos for pos, t in self.game_state.airborne.items()
                          if t <= self.game_state.clock]
        for pos in due_positions:
            del self.game_state.airborne[pos]                   # כלל 4: נחיתה רגילה - הכלי כבר במקומו, אין שינוי בלוח