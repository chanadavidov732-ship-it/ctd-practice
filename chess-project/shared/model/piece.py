from shared.config import EMPTY_CELL


def token_color(token):
    if token == EMPTY_CELL:
        return None
    return token[0]

def token_type(token):
    if token == EMPTY_CELL:
        return None
    return token[1]