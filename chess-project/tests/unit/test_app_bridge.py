import asyncio
import contextlib

import pytest
import websockets

from client.network.app_bridge import AppBridge, BROADCAST, CONNECTED, CONNECTION_LOST, RESPONSE
from shared.protocol import Envelope


class FakeConnection:
    """Stands in for ServerConnection: yields a fixed sequence of envelopes,
    then raises ConnectionClosed, exactly like a real socket dropping."""

    def __init__(self, envelopes):
        self._envelopes = list(envelopes)
        self.sent: list[Envelope] = []

    async def receive(self) -> Envelope:
        if not self._envelopes:
            raise websockets.ConnectionClosed(None, None)
        return self._envelopes.pop(0)

    async def send(self, envelope: Envelope) -> None:
        self.sent.append(envelope)


def test_send_request_before_run_raises():
    bridge = AppBridge()
    with pytest.raises(RuntimeError):
        bridge.send_request(Envelope(type="login", payload={}))


def test_run_classifies_unmatched_envelope_as_broadcast_then_connection_lost():
    async def scenario():
        bridge = AppBridge()
        connection = FakeConnection([Envelope(type="room_state", payload={"room_id": "abc"})])
        await bridge.run(connection)
        return bridge.poll_events()

    events = asyncio.run(scenario())
    assert [e.kind for e in events] == [BROADCAST, CONNECTION_LOST]
    assert events[0].envelope.payload == {"room_id": "abc"}


def test_run_classifies_matching_request_id_as_response():
    async def scenario():
        bridge = AppBridge()
        bridge._pending_request_id = "req-1"
        connection = FakeConnection(
            [Envelope(type="login_result", payload={"success": True}, request_id="req-1")]
        )
        await bridge.run(connection)
        return bridge

    bridge = asyncio.run(scenario())
    events = bridge.poll_events()
    assert [e.kind for e in events] == [RESPONSE, CONNECTION_LOST]
    assert events[0].envelope.payload == {"success": True}
    assert bridge._pending_request_id is None


def test_poll_events_drains_the_queue():
    async def scenario():
        bridge = AppBridge()
        connection = FakeConnection(
            [Envelope(type="room_state", payload={"n": 1}), Envelope(type="room_state", payload={"n": 2})]
        )
        await bridge.run(connection)
        return bridge

    bridge = asyncio.run(scenario())
    first_poll = bridge.poll_events()
    second_poll = bridge.poll_events()
    assert len(first_poll) == 3  # 2 broadcasts + connection_lost
    assert second_poll == []


def test_send_request_assigns_request_id_and_sends_on_the_loop():
    async def scenario():
        bridge = AppBridge()
        connection = FakeConnection([])
        bridge._loop = asyncio.get_running_loop()
        bridge._connection = connection

        bridge.send_request(Envelope(type="login", payload={"username": "alice"}))
        await asyncio.sleep(0)  # let the scheduled coroutine run on this same loop

        return bridge, connection

    bridge, connection = asyncio.run(scenario())
    assert len(connection.sent) == 1
    sent_envelope = connection.sent[0]
    assert sent_envelope.request_id is not None
    assert bridge._pending_request_id == sent_envelope.request_id


def test_send_request_keeps_caller_supplied_request_id():
    async def scenario():
        bridge = AppBridge()
        connection = FakeConnection([])
        bridge._loop = asyncio.get_running_loop()
        bridge._connection = connection

        bridge.send_request(Envelope(type="login", payload={}, request_id="my-id"))
        await asyncio.sleep(0)

        return connection

    connection = asyncio.run(scenario())
    assert connection.sent[0].request_id == "my-id"


def test_connect_before_serve_raises():
    bridge = AppBridge()
    with pytest.raises(RuntimeError):
        bridge.connect("ws://127.0.0.1:59999/ws")


def test_serve_captures_the_running_loop():
    async def scenario():
        bridge = AppBridge()
        task = asyncio.create_task(bridge.serve())
        await asyncio.sleep(0)  # let serve() start and capture the loop
        loop = bridge._loop
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return loop

    loop = asyncio.run(scenario())
    assert loop is not None


def test_connect_reports_connection_lost_when_nothing_is_listening():
    # Nothing listens on this loopback port, so the handshake fails fast
    # (ECONNREFUSED) without needing a real server for this test.
    async def scenario():
        bridge = AppBridge()
        bridge._loop = asyncio.get_running_loop()
        bridge.connect("ws://127.0.0.1:59999/ws")
        for _ in range(50):  # up to ~5s for the refused-connection error to surface
            if not bridge._events.empty():
                break
            await asyncio.sleep(0.1)
        return bridge

    bridge = asyncio.run(scenario())
    events = bridge.poll_events()
    assert [e.kind for e in events] == [CONNECTION_LOST]


def test_connect_pushes_connected_before_starting_the_receive_loop():
    """Exercises _connect_and_run's CONNECTED signal without a real socket by
    monkeypatching ServerConnection with a fake that "connects" instantly."""

    async def scenario(monkeypatch):
        import client.network.app_bridge as app_bridge_module

        fake_connection = FakeConnection([])
        fake_connection.connect = lambda: asyncio.sleep(0)  # no-op "success"
        monkeypatch.setattr(app_bridge_module, "ServerConnection", lambda uri: fake_connection)

        bridge = AppBridge()
        bridge._loop = asyncio.get_running_loop()
        bridge.connect("ws://ignored/ws")
        await asyncio.sleep(0.05)
        return bridge

    with pytest.MonkeyPatch.context() as monkeypatch:
        bridge = asyncio.run(scenario(monkeypatch))

    events = bridge.poll_events()
    assert [e.kind for e in events] == [CONNECTED, CONNECTION_LOST]
