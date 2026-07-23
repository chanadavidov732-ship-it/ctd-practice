from shared.model.board import Board
from shared.model.game_state import GameState
from shared.realtime.realtime_arbiter import RealTimeArbiter
from shared.engine.game_engine import GameEngine
from client.input.board_mapper import BoardMapper
from client.input.controller import Controller
from client.io_options.board_printer import print_board


def make_setup(rows):
    grid = [row.split() for row in rows]
    board = Board(grid)
    game_state = GameState()
    arbiter = RealTimeArbiter(board, game_state)
    engine = GameEngine(board, game_state, arbiter)
    mapper = BoardMapper(board)
    controller = Controller(board, mapper, engine)
    return board, engine, controller


ROW = ". . . . . . . ."


def test_piece_stays_in_place_before_arrival(capsys):
    board, engine, controller = make_setup([ROW] * 7 + ["wR . . . . . . ."])

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)

    engine.advance_time(500)      
    print_board(board)
    captured = capsys.readouterr()

    last_row = captured.out.strip().splitlines()[-1]
    assert last_row == "wR . . . . . . ."   # עדיין במקום המקורי


def test_piece_arrives_after_enough_wait(capsys):
    board, engine, controller = make_setup([ROW] * 7 + ["wR . . . . . . ."])

    controller.handle_click(50, 750)
    controller.handle_click(350, 750)

    engine.advance_time(3000)       
    print_board(board)
    captured = capsys.readouterr()

    last_row = captured.out.strip().splitlines()[-1]
    assert last_row == ". . . wR . . . ."  # הגיע ליעד