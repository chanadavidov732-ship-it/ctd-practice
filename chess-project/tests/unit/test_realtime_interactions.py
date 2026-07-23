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


# ---------- Enemy collision ----------

def test_enemy_collision_results_in_capture():
    rows = [ROW] * 7 + ["wR . . bN . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)  
    controller.handle_click(350, 750)
    engine.advance_time(3000)

    assert board.get_piece((3, 7)) == "wR" 

# ---------- Invalid premove ----------

def test_premove_onto_piece_still_mid_motion_is_rejected():
    """ניסיון לשלוח בקשת מהלך שנייה בזמן שכלי אחר עדיין 'באוויר' -
    נחסם ע"י המנעול הגלובלי, לא מגיע בכלל ל-Rule Engine."""
    rows = [ROW] * 6 + [". . . . . . . .", "wR . . . bN . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)  
    controller.handle_click(350, 750) 

    controller.handle_click(450, 750) 
    controller.handle_click(150, 750)

    engine.advance_time(3000)

    assert board.get_piece((3, 7)) == "wR"  
    assert board.get_piece((4, 7)) == "bN"   


# ---------- Friendly-piece landing ----------

def test_friendly_piece_landing_is_rejected():
    rows = [ROW] * 7 + ["wR wN . . . . . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 750)  
    controller.handle_click(150, 750)

    engine.advance_time(1000)

    assert board.get_piece((0, 7)) == "wR"  
    assert board.get_piece((1, 7)) == "wN" 


# ---------- Movement conflicts (global lock, same color) ----------

def test_same_color_second_piece_cannot_move_during_conflict():
    rows = ["wR . .", ". . .", "wN . ."]
    board, state, engine, controller = make_setup(rows)

    controller.handle_click(50, 50)   
    controller.handle_click(250, 50)  

    controller.handle_click(50, 250)   
    controller.handle_click(250, 250)  

    engine.advance_time(2000)

    assert board.get_piece((2, 0)) == "wR"  
    assert board.get_piece((0, 2)) == "wN" 