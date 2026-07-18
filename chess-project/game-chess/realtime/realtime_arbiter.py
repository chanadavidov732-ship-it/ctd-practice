from model.piece import token_type, token_color
from rules.piece_rules import pawn_promotion_row
from realtime.motion import JUMP_DURATION_MS, LONG_REST_MS, SHORT_REST_MS   

class RealTimeArbiter:
    def __init__(self, board, game_state):
        self.board = board
        self.game_state = game_state

    def start_motion(self, from_pos, to_pos, token, completion_time, duration):
        self.game_state.pending_moves.append({
            "from": from_pos,
            "to": to_pos,
            "token": token,
            "completion_time": completion_time,
            "duration": duration
        })
        self.game_state.locked.add(from_pos)

    def _settle_due_moves(self):
        due = [m for m in self.game_state.pending_moves
            if m["completion_time"] <= self.game_state.clock]
        due.sort(key=lambda m: m["completion_time"])

        settled = []
        for move in due:
            if move["to"] in self.game_state.airborne:
                defender_token = self.board.get_piece(move["to"])
                if token_color(defender_token) != token_color(move["token"]):
                    self.board.set_piece(move["from"], ".")
                    self.game_state.locked.discard(move["from"])
                    self.game_state.pending_moves.remove(move)
                    move["captured_token"] = move["token"]
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

            self.game_state.resting[move["to"]] = self.game_state.clock + LONG_REST_MS

            move["captured_token"] = captured_token
            settled.append(move)

        return settled
    
    def start_jump(self, pos):
        self.game_state.airborne[pos] = self.game_state.clock + JUMP_DURATION_MS

    def advance_time(self, ms):
        self.game_state.clock += ms
        settled = self._settle_due_moves()
        self._land_due_jumps()
        self._release_due_rests()
        return settled

    def _release_due_rests(self):
        due_positions = [pos for pos, t in self.game_state.resting.items()
                          if t <= self.game_state.clock]
        for pos in due_positions:
            del self.game_state.resting[pos]

    def _land_due_jumps(self):
        due_positions = [pos for pos, t in self.game_state.airborne.items()
                          if t <= self.game_state.clock]
        for pos in due_positions:
            del self.game_state.airborne[pos]
            self.game_state.resting[pos] = self.game_state.clock + SHORT_REST_MS   