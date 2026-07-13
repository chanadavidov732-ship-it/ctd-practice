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

def test_legal_move_completes_after_wait():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wR . . . . . . ."])

    controller.handle_click(50, 750)   # select rook at (0,7)
    controller.handle_click(350, 750)  # move to (3,7)

    assert board.get_piece((0, 7)) == "wR"
    assert board.get_piece((3, 7)) == "."

    engine.advance_time(3000)  # 3 squares * 1000ms  ← שונה מ-600

    assert board.get_piece((0, 7)) == "."
    assert board.get_piece((3, 7)) == "wR"

def test_illegal_move_is_ignored():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wK . . . . . . ."])

    controller.handle_click(50, 750)   # select king at (0,7)
    controller.handle_click(350, 750)  # illegal: 3 squares straight

    engine.advance_time(1000)

    assert board.get_piece((0, 7)) == "wK"
    assert board.get_piece((3, 7)) == "."
    assert controller.selected is None


def test_capture_enemy_piece():
    rows = [ROW] * 7 + ["wR . . bN . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)   # select rook at (0,7)
    controller.handle_click(350, 750)  # move to (3,7), enemy knight there
    engine.advance_time(3000)  # ← שונה מ-600

    assert board.get_piece((3, 7)) == "wR"


def test_locked_piece_click_is_ignored():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wR . . . . . . ."])

    controller.handle_click(50, 750)   # select rook
    controller.handle_click(350, 750)  # send move request, rook now locked

    controller.handle_click(50, 750)   # click origin while mid-move: ignored
    assert controller.selected is None


def test_reselect_friendly_piece():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wR wN . . . . . ."])

    controller.handle_click(50, 750)   # select rook at (0,7)
    controller.handle_click(150, 750)  # click friendly knight: replace selection

    assert controller.selected == {"pos": (1, 7), "color": "w"}


def test_piece_cannot_be_redirected_while_moving():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wR . . . . . . ."])

    controller.handle_click(50, 750)   # select rook at (0,7)
    controller.handle_click(350, 750)  # move to (3,7), rook now locked, duration=3000ms

    # ניסיון להפנות מחדש תוך כדי תנועה: קליק על מקור הכלי (נעול) - מתעלם
    controller.handle_click(50, 750)
    # קליק על יעד אחר תוך כדי תנועה - אין בחירה פעילה, כלום לא קורה
    controller.handle_click(550, 750)

    engine.advance_time(3000)  # 3 squares * 1000ms

    # הכלי הגיע ליעד המקורי בלבד, לא הוסט
    assert board.get_piece((3, 7)) == "wR"
    assert board.get_piece((5, 7)) == "."


def test_piece_can_move_again_immediately_after_arrival_no_cooldown():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wR . . . . . . ."])

    controller.handle_click(50, 750)   # select rook at (0,7)
    controller.handle_click(350, 750)  # move to (3,7)
    engine.advance_time(3000)          # arrival, locked cleared immediately

    assert board.get_piece((3, 7)) == "wR"

    # מיד לאחר ההגעה - מהלך נוסף, ללא המתנה נוספת (no cooldown)
    controller.handle_click(350, 750)  # select rook at new position (3,7)
    controller.handle_click(650, 750)  # move to (6,7)

    assert (3, 7) in state.locked  # הכלי שוב בתנועה, המהלך השני התקבל


def test_second_piece_cannot_move_while_another_is_in_motion():
    rows = ["wR . .", ". . .", "bR . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 50)    # select wR at (0,0)
    controller.handle_click(250, 50)   # move wR to (2,0), 2000ms, locked={(0,0)}

    controller.handle_click(50, 250)   # select bR at (0,2)
    controller.handle_click(250, 250)  # attempt move bR to (2,2) - rejected, global lock active

    engine.advance_time(2000)

    assert board.get_piece((2, 0)) == "wR"   # wR arrived
    assert board.get_piece((0, 2)) == "bR"   # bR never moved
    assert board.get_piece((2, 2)) == "."