from shared.model.board import Board
from shared.model.game_state import GameState
from shared.realtime.realtime_arbiter import RealTimeArbiter
from shared.engine.game_engine import GameEngine
from client.input.board_mapper import BoardMapper
from client.input.controller import Controller


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


def test_capturing_enemy_king_ends_game():
    rows = [ROW] * 7 + ["wR . . bK . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)  
    controller.handle_click(350, 750)  
    engine.advance_time(3000)

    assert board.get_piece((3, 7)) == "wR"
    assert engine.is_over is True


def test_moves_after_game_over_are_ignored():
    rows = [ROW] * 6 + ["wN . . . . . . .", "wR . . bK . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)
    engine.advance_time(3000)

    assert engine.is_over is True

    controller.handle_click(50, 650)
    controller.handle_click(250, 650)

    engine.advance_time(3000)

    assert board.get_piece((0, 6)) == "wN"   


def test_non_king_capture_does_not_end_game():
    rows = [ROW] * 7 + ["wR . . bN . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)
    engine.advance_time(3000)

    assert engine.is_over is False