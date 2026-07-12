def solve():
    board = []
    
    while True:
        try:
            line = input().strip()
        except EOFError:
            break

        if line == "Board:":
            continue
        if line == "Commands:":
            break
        if line:
            board.append(line.split())

    width = len(board[0])

    valid = {
        ".", "wK", "wQ", "wR", "wB", "wN", "wP",
        "bK", "bQ", "bR", "bB", "bN", "bP"
    }

    for row in board:
        if len(row) != width:
            print("ERROR ROW_WIDTH_MISMATCH")
            return
        for cell in row:
            if cell not in valid:
                print("ERROR UNKNOWN_TOKEN")
                return

    try:
        command = input().strip()
    except EOFError:
        command = ""

    if command == "print board":
        for row in board:
            print(" ".join(row))


solve()