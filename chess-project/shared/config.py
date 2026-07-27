from shared.rules.piece_rules import (
    _validate_king,
    _validate_queen,
    _validate_rook,
    _validate_bishop,
    _validate_knight,
)

# --- Piece registry -----------------------------------------------------
KING = "K"
QUEEN = "Q"
ROOK = "R"
BISHOP = "B"
KNIGHT = "N"
PAWN = "P"
PIECE_TYPES = {KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN}

WHITE = "w"
BLACK = "b"
COLORS = {WHITE, BLACK}

# --- Movement validators registry ----------------------------------------
MOVEMENT_VALIDATORS = {
    KING: _validate_king,
    QUEEN: _validate_queen,
    ROOK: _validate_rook,
    BISHOP: _validate_bishop,
    KNIGHT: _validate_knight,
}
