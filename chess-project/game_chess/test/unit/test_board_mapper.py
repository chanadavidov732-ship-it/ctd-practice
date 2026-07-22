from shared.model.board import Board
from client.input.board_mapper import BoardMapper

def make_mapper(rows):
    grid = [row.split() for row in rows]
    board = Board(grid)
    return BoardMapper(board)

def test_pixel_to_cell_top_left():
    mapper = make_mapper([". .", ". ."])
    assert mapper.pixel_to_cell(50, 50) == (0, 0)

def test_pixel_to_cell_next_cell():
    mapper = make_mapper([". .", ". ."])
    assert mapper.pixel_to_cell(150, 50) == (1, 0)

def test_pixel_to_cell_outside_board():
    mapper = make_mapper([". .", ". ."])
    assert mapper.pixel_to_cell(500, 500) is None