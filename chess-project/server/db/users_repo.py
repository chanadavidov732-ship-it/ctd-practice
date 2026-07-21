import hashlib
import logging
import pathlib
import secrets
import sqlite3

logger = logging.getLogger("server")

DB_PATH = pathlib.Path(__file__).parent / "chess.db"
SCHEMA_PATH = pathlib.Path(__file__).parent / "schema.sql"

PBKDF2_ITERATIONS = 200_000


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
    logger.info("database initialized at %s", DB_PATH)


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS).hex()


def create_user(username: str, password: str) -> bool:
    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, password_hash, salt.hex()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(username: str, password: str) -> tuple[bool, int | None]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT password_hash, salt, rating FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if row is None:
        return False, None

    password_hash, salt_hex, rating = row
    if _hash_password(password, bytes.fromhex(salt_hex)) == password_hash:
        return True, rating
    return False, None
