import asyncio

from server.db.users_repo import create_user, verify_user


async def register(username: str, password: str) -> dict:
    created = await asyncio.to_thread(create_user, username, password)
    if created:
        return {"success": True, "message": "user registered"}
    return {"success": False, "message": "username already exists"}


async def login(username: str, password: str) -> dict:
    ok, rating = await asyncio.to_thread(verify_user, username, password)
    if ok:
        return {"success": True, "message": "login successful", "rating": rating}
    return {"success": False, "message": "invalid username or password"}
