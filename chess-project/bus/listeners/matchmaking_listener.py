import asyncio
import logging

from bus.event_bus import event_bus
from bus.events import MatchFound, MatchTimeout, PlayerQueued
from server.logic.game_session import game_session_manager
from server.logic.matchmaking import QueuedPlayer, matchmaking
from shared.config import MATCH_TIMEOUT_SECONDS, MSG_MATCH_FOUND, MSG_MATCH_TIMEOUT
from shared.protocol import Envelope

logger = logging.getLogger("bus")


async def on_player_queued(event: PlayerQueued) -> None:
    logger.info(
        "event received: PlayerQueued(client_id=%s, username=%s, rating=%s)",
        event.client_id, event.username, event.rating,
    )

    match = _try_match(event.client_id)
    if match is None:
        return
    player, opponent, match_id = match

    await event_bus.publish(MatchFound(match_id=match_id, client_id_a=opponent.client_id, client_id_b=player.client_id))
    await _notify_players_matched(match_id, player, opponent)

    await game_session_manager.start_for_match(match_id, opponent, player)


def _try_match(client_id: str) -> tuple[QueuedPlayer, QueuedPlayer, str] | None:
    player = matchmaking.get(client_id)
    if player is None:
        return None

    opponent = matchmaking.find_opponent(player.rating, exclude_client_id=player.client_id)
    if opponent is None:
        player.timeout_task = asyncio.create_task(_expire_after_timeout(player.client_id))
        return None

    matchmaking.remove_and_cancel_timeout(player.client_id)
    matchmaking.remove_and_cancel_timeout(opponent.client_id)

    match_id = matchmaking.generate_match_id()
    logger.info(
        "MatchFound: match_id=%s, client_id_a=%s, client_id_b=%s",
        match_id, opponent.client_id, player.client_id,
    )
    return player, opponent, match_id


async def _notify_players_matched(match_id: str, player: QueuedPlayer, opponent: QueuedPlayer) -> None:
    for me, other in ((player, opponent), (opponent, player)):
        await me.websocket.send_json(Envelope(
            type=MSG_MATCH_FOUND,
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
    await player.websocket.send_json(Envelope(type=MSG_MATCH_TIMEOUT, payload={}).to_dict())
