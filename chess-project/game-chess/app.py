import time

from model.board import Board
from model.game_state import GameState
from realtime.realtime_arbiter import RealTimeArbiter
from engine.game_engine import GameEngine
from input.board_mapper import BoardMapper
from input.controller import Controller
from io_options.board_parser import read_board, validate_board
from ui.renderer import Renderer

def main():
    grid = read_board()

    error = validate_board(grid)
    if error:
        print(error)
        return
    
    board = Board(grid)
    game_state = GameState()
    arbiter = RealTimeArbiter(board, game_state)
    game_engine = GameEngine(board, game_state, arbiter)
    board_mapper = BoardMapper(board)
    controller = Controller(board, board_mapper, game_engine)

    renderer = Renderer(board, controller, game_engine)

    last_time = time.perf_counter()
    running = True
    while running:
        now = time.perf_counter()
        elapsed_ms = (now - last_time) * 1000
        last_time = now

        game_engine.advance_time(elapsed_ms)
        running = renderer.render()
    

if __name__ == "__main__":
    main()