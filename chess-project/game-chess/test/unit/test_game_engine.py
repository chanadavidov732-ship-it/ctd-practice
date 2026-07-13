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

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)

    assert board.get_piece((0, 7)) == "wR"
    assert board.get_piece((3, 7)) == "."

    engine.advance_time(3000)

    assert board.get_piece((0, 7)) == "."
    assert board.get_piece((3, 7)) == "wR"

def test_illegal_move_is_ignored():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wK . . . . . . ."])

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)

    engine.advance_time(1000)

    assert board.get_piece((0, 7)) == "wK"
    assert board.get_piece((3, 7)) == "."
    assert controller.selected is None


def test_capture_enemy_piece():
    rows = [ROW] * 7 + ["wR . . bN . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)
    engine.advance_time(3000)

    assert board.get_piece((3, 7)) == "wR"


def test_locked_piece_click_is_ignored():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wR . . . . . . ."])

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)

    controller.handle_click(50, 750)
    assert controller.selected is None


def test_reselect_friendly_piece():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wR wN . . . . . ."])

    controller.handle_click(50, 750)
    controller.handle_click(150, 750)

    assert controller.selected == {"pos": (1, 7), "color": "w"}


def test_piece_cannot_be_redirected_while_moving():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wR . . . . . . ."])

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)

    controller.handle_click(50, 750)
    controller.handle_click(550, 750)

    engine.advance_time(3000)

    assert board.get_piece((3, 7)) == "wR"
    assert board.get_piece((5, 7)) == "."


def test_piece_can_move_again_immediately_after_arrival_no_cooldown():
    board, state, engine, controller = make_setup([ROW] * 7 + ["wR . . . . . . ."])

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)
    engine.advance_time(3000)

    assert board.get_piece((3, 7)) == "wR"

    controller.handle_click(350, 750)
    controller.handle_click(650, 750)

    assert (3, 7) in state.locked


def test_second_piece_cannot_move_while_another_is_in_motion():
    rows = ["wR . .", ". . .", "bR . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 50)
    controller.handle_click(250, 50)

    controller.handle_click(50, 250)
    controller.handle_click(250, 250)

    engine.advance_time(2000)

    assert board.get_piece((2, 0)) == "wR"
    assert board.get_piece((0, 2)) == "bR"
    assert board.get_piece((2, 2)) == "."

def test_pawn_promotes_to_queen_on_last_row():
    rows = ["wP . . . . . . ."] + [ROW] * 7
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 50)


def test_pawn_promotes_to_queen_on_last_row():
    rows = [ROW, "wP . . . . . . ."] + [ROW] * 6
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 150)
    controller.handle_click(50, 50)
    engine.advance_time(1000)

    assert board.get_piece((0, 0)) == "wQ"


def test_jump_captures_arriving_enemy_and_stays_in_place():
    rows = [ROW] * 5 + ["bR . . . . . . .", ". . . . . . . .", "wR . . . . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_jump(50, 550)
    controller.handle_click(50, 750)
    controller.handle_click(50, 550)

    engine.advance_time(2000)

    assert board.get_piece((0, 5)) == "bR"
    assert board.get_piece((0, 7)) == "."
