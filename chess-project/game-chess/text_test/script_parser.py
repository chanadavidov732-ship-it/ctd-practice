def parse_command(line):
    parts = line.split()
    if not parts:
        return None

    cmd = parts[0]

    if cmd == "click" and len(parts) == 3:
        return ("click", int(parts[1]), int(parts[2]))

    if cmd == "wait" and len(parts) == 2:
        return ("wait", int(parts[1]))

    if line == "print board":
        return ("print_board",)
    
    if cmd == "jump" and len(parts) == 3:                       # ADDED
        return ("jump", int(parts[1]), int(parts[2]))

    return None