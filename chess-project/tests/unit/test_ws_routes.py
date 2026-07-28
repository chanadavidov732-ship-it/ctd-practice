import asyncio

import server.network.ws_routes as ws_routes
from server.network.ws_routes import ConnectionContext, handle_register


def _ctx() -> ConnectionContext:
    return ConnectionContext(websocket=None, client_id="c1")


def test_handle_register_logs_in_the_connection_on_success(monkeypatch):
    async def fake_register(username, password):
        return {"success": True, "message": "user registered", "rating": 1200}

    monkeypatch.setattr(ws_routes, "auth_register", fake_register)
    ctx = _ctx()

    result = asyncio.run(handle_register({"username": "alice", "password": "secret"}, ctx))

    assert result["success"] is True
    assert ctx.username == "alice"
    assert ctx.rating == 1200


def test_handle_register_leaves_connection_logged_out_on_failure(monkeypatch):
    async def fake_register(username, password):
        return {"success": False, "message": "username already exists"}

    monkeypatch.setattr(ws_routes, "auth_register", fake_register)
    ctx = _ctx()

    result = asyncio.run(handle_register({"username": "alice", "password": "secret"}, ctx))

    assert result["success"] is False
    assert ctx.username is None
    assert ctx.rating is None
