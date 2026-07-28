import asyncio

import server.auth.auth as auth_module
from server.auth.auth import register


def test_register_success_returns_the_default_rating(monkeypatch):
    monkeypatch.setattr(auth_module, "create_user", lambda username, password: True)

    result = asyncio.run(register("alice", "secret"))

    assert result == {"success": True, "message": "user registered", "rating": 1200}


def test_register_failure_omits_rating(monkeypatch):
    monkeypatch.setattr(auth_module, "create_user", lambda username, password: False)

    result = asyncio.run(register("alice", "secret"))

    assert result == {"success": False, "message": "username already exists"}
