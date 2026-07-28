import asyncio

from server.db.users_repo import update_rating


def capture_bonus(captures: int) -> int:
    from server.config import CAPTURE_BONUS_POINTS

    return captures * CAPTURE_BONUS_POINTS


async def apply_match_result(
    winner_username: str, winner_rating: int, loser_username: str, loser_rating: int,
    captures_winner: int = 0, captures_loser: int = 0,
) -> tuple[int, int]:
    from server.config import LOSS_PENALTY_POINTS, WIN_BONUS_POINTS

    updated_winner = winner_rating + WIN_BONUS_POINTS + capture_bonus(captures_winner)
    updated_loser = loser_rating - LOSS_PENALTY_POINTS + capture_bonus(captures_loser)
    await asyncio.to_thread(update_rating, winner_username, updated_winner)
    await asyncio.to_thread(update_rating, loser_username, updated_loser)
    return updated_winner, updated_loser
