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
            captured_token = self.board.get_piece(move["to"])   # ADDED: תפיסת הטוקן לפני הדריסה

            # Atomic Update - עדכון הלוח מתבצע רק כאן, ברגע ההגעה בפועל
            self.board.set_piece(move["from"], ".")
            self.board.set_piece(move["to"], move["token"])
            self.game_state.locked.discard(move["from"])
            self.game_state.pending_moves.remove(move)

            move["captured_token"] = captured_token             # ADDED: מצורף לתוצאה המדווחת
            settled.append(move)

        return settled