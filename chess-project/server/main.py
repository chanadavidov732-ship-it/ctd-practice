import logging

from fastapi import FastAPI

from bus.subscribers.connection_subscriber import register_connection_listeners
from bus.subscribers.matchmaking_subscriber import register_matchmaking_listeners
from bus.subscribers.room_subscriber import register_room_listeners
from server.db.users_repo import init_db
from server.network.ws_routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

register_connection_listeners()
register_room_listeners()
register_matchmaking_listeners()
init_db()

app = FastAPI()
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
