import asyncio
import logging

from bus.event_bus import event_bus
from bus.events import MatchFound, MatchTimeout, PlayerQueued
from server.logic.matchmaking import matchmaking
from shared.protocol import Envelope

logger = logging.getLogger("bus")

MATCH_TIMEOUT_SECONDS = 60


async def on_player_queued(event: PlayerQueued) -> None:
    logger.info(
        "event received: PlayerQueued(client_id=%s, username=%s, rating=%s)",
        event.client_id, event.username, event.rating,
    )

    player = matchmaking.get(event.client_id)
    if player is None:
        return

    opponent = matchmaking.find_opponent(player.rating, exclude_client_id=player.client_id)
    if opponent is None:
        player.timeout_task = asyncio.create_task(_expire_after_timeout(player.client_id))
        return

    matchmaking.remove(player.client_id)
    matchmaking.remove(opponent.client_id)
    if opponent.timeout_task is not None:
        opponent.timeout_task.cancel()

    match_id = matchmaking.generate_match_id()
    logger.info(
        "MatchFound: match_id=%s, client_id_a=%s, client_id_b=%s",
        match_id, opponent.client_id, player.client_id,
    )
    await event_bus.publish(MatchFound(match_id=match_id, client_id_a=opponent.client_id, client_id_b=player.client_id))

    for me, other in ((player, opponent), (opponent, player)):
        await me.websocket.send_json(Envelope(
            type="match_found",
            payload={
                "match_id": match_id,
                "opponent_username": other.username,
                "opponent_rating": other.rating,
            },
        ).to_dict())


async def _expire_after_timeout(client_id: str) -> None:
    await asyncio.sleep(MATCH_TIMEOUT_SECONDS)

    player = matchmaking.remove(client_id)
    if player is None:
        return

    logger.info("MatchTimeout: client_id=%s", client_id)
    await event_bus.publish(MatchTimeout(client_id=client_id))
    await player.websocket.send_json(Envelope(type="match_timeout", payload={}).to_dict())
