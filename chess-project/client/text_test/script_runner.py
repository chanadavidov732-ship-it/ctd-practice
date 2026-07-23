from client.text_test.script_parser import parse_command
from client.io_options.board_printer import print_board


def run_commands(controller, game_engine, board):
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if not line:
            continue

        command = parse_command(line)
        if command is None:
            continue

        if command[0] == "click":
            _, x, y = command
            controller.handle_click(x, y)
        elif command[0] == "wait":
            _, ms = command
            game_engine.advance_time(ms)
        elif command[0] == "print_board":
            print_board(board)
        elif command[0] == "jump":
            _, x, y = command
            controller.handle_jump(x, y)