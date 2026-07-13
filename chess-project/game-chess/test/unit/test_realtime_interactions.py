from model.board import Board
from model.game_state import GameState
from realtime.realtime_arbiter import RealTimeArbiter
from engine.game_engine import GameEngine
from input.board_mapper import BoardMapper
from input.controller import Controller


def make_setup(rows):
    grid = [row.split() for row in rows]
    board = Board(grid)
    game_state = GameState()
    arbiter = RealTimeArbiter(board, game_state)
    engine = GameEngine(board, game_state, arbiter)
    mapper = BoardMapper(board)
    controller = Controller(board, mapper, engine)
    return board, game_state, engine, controller


ROW = ". . . . . . . ."


# ---------- Enemy collision ----------

def test_enemy_collision_results_in_capture():
    rows = [ROW] * 7 + ["wR . . bN . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)   # select wR at (0,7)
    controller.handle_click(350, 750)  # move to (3,7), collides with enemy bN
    engine.advance_time(3000)

    assert board.get_piece((3, 7)) == "wR"  # enemy captured, wR occupies square


# ---------- Invalid premove ----------

def test_premove_onto_piece_still_mid_motion_is_rejected():
    """ניסיון לשלוח בקשת מהלך שנייה בזמן שכלי אחר עדיין 'באוויר' -
    נחסם ע"י המנעול הגלובלי, לא מגיע בכלל ל-Rule Engine."""
    rows = [ROW] * 6 + [". . . . . . . .", "wR . . . bN . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)   # select wR at (0,7)
    controller.handle_click(350, 750)  # request move to (3,7), now locked, duration=3000ms

    # פרימוב לא חוקי: ניסיון לבחור ולזוז עם כלי אחר בזמן שהראשון עדיין בתנועה
    controller.handle_click(450, 750)  # attempt select bN at (4,7) - blocked by global lock? 
    # bN is not the moving piece, but engine still rejects any new motion while one is active
    controller.handle_click(150, 750)

    engine.advance_time(3000)

    assert board.get_piece((3, 7)) == "wR"   # only original move completed
    assert board.get_piece((4, 7)) == "bN"   # untouched, premove rejected


# ---------- Friendly-piece landing ----------

def test_friendly_piece_landing_is_rejected():
    rows = [ROW] * 7 + ["wR wN . . . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)   # select wR at (0,7)
    controller.handle_click(150, 750)  # attempt move onto wN at (1,7) - friendly fire

    engine.advance_time(1000)

    assert board.get_piece((0, 7)) == "wR"   # wR never moved
    assert board.get_piece((1, 7)) == "wN"   # wN untouched


# ---------- Movement conflicts (global lock, same color) ----------

def test_same_color_second_piece_cannot_move_during_conflict():
    rows = ["wR . .", ". . .", "wN . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 50)    # select wR at (0,0)
    controller.handle_click(250, 50)   # move wR to (2,0), 2000ms, global lock active

    controller.handle_click(50, 250)   # select wN at (0,2)
    controller.handle_click(250, 250)  # attempt move - rejected, lock still active

    engine.advance_time(2000)

    assert board.get_piece((2, 0)) == "wR"  # first move completed
    assert board.get_piece((0, 2)) == "wN"  # second piece never moved