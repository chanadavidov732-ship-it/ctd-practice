import secrets
from typing import Callable, Optional


def generate_id(alphabet: str, length: int, is_taken: Optional[Callable[[str], bool]] = None) -> str:
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if is_taken is None or not is_taken(candidate):
            return candidate
