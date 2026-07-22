import asyncio

from server.db.users_repo import update_rating

K_FACTOR = 32


def expected_score(rating_a: int, rating_b: int) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def new_rating(rating_a: int, rating_b: int, score_a: float) -> int:
    return round(rating_a + K_FACTOR * (score_a - expected_score(rating_a, rating_b)))


async def apply_match_result(
    username_a: str, rating_a: int, username_b: str, rating_b: int, score_a: float,
) -> tuple[int, int]:
    updated_a = new_rating(rating_a, rating_b, score_a)
    updated_b = new_rating(rating_b, rating_a, 1 - score_a)
    await asyncio.to_thread(update_rating, username_a, updated_a)
    await asyncio.to_thread(update_rating, username_b, updated_b)
    return updated_a, updated_b
