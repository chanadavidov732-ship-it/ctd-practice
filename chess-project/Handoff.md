# Kung Fu Chess — Handoff Document

> This document is meant to let a new developer (or a fresh Claude conversation) continue this project **without** access to the previous chat history. It summarizes purpose, architecture, decisions, current status, and constraints.
>
> **This is a full rewrite** (previous version described the pre-client/server `game-chess/` single-folder layout, which no longer exists). Everything below reflects the repo as it actually is today.

---

## 1. System Purpose

**Kung Fu Chess** is a **real-time** chess variant, unlike classic turn-based chess:

- **No turns** — both players can move pieces at any moment; only a piece's own lock/rest state blocks it (see section 7, decision #4).
- Every move has a **duration** computed from distance. During that time the piece is "in motion" and unavailable for further action.
- **Capture** only happens when a move actually arrives (Atomic Update), never while a piece is "in flight."
- There is no theoretical "check"/"checkmate" — the game ends **immediately** when a king is actually captured.
- A **"Jump"** mechanic — a piece can "jump" and stay on its logical cell; if an enemy moving piece arrives at that cell while it's airborne, the jumping piece captures it (Air Capture).

The project started as a text-only, single-process board (click/jump/wait scripted via stdin) and has since grown two more layers on top of the same rule engine, never changing it:

1. **A graphical board** (`client/ui/renderer.py` + `client/ui/sprite_manager.py`, OpenCV/`Img`-based) — reused, unmodified in its core drawing logic, by both the local single-machine mode and the networked mode.
2. **A client/server multiplayer layer** (FastAPI + WebSockets) — login/register with a persistent rating, matchmaking (rating-range queue) or private rooms (room-ID based, with spectators), real-time game sessions authoritative on the server, and a graphical wrapper-screen flow (Login → Home → Room/Matchmaking → game board → back to Home) that replaced the original textual menu as the default entry point.

---

## 2. Architecture

The project follows strict separation of concerns. **Core principle**: every layer knows only what it must, and nothing more.

| Layer | Folder | Responsibility | Must NOT know about |
|---|---|---|---|
| **Model** | `shared/model/` | Raw board/piece/position/game-state | Rendering, input, time, networking |
| **Rules** | `shared/rules/` | Move legality (shape, blocking, capture, ownership) | How to draw, how to actually move pieces, time |
| **Realtime** | `shared/realtime/` | Logical clock, active motions, jumps, Atomic Update | Move legality (that's Rules' job) |
| **Engine** | `shared/engine/` | Orchestrates the overall flow: move request → checks → trigger motion | Specific piece rules, drawing, pixel mapping, networking |
| **Protocol** | `shared/protocol.py` | The one message envelope shape client and server both speak | Any specific message's meaning |
| **Server logic** | `server/logic/`, `server/auth/`, `server/db/` | Auth, rating, matchmaking, rooms, authoritative game sessions | Rendering, input |
| **Event bus** | `bus/` | Decouples server subsystems (room/matchmaking/connection) via pub/sub | Business rules of the events it carries |
| **Server network** | `server/network/`, `server/engine_adapter/` | WebSocket routing, per-room broadcast fan-out, `shared/` composition root | Auth/DB details, rating math |
| **Client network** | `client/network/` | WebSocket connection, request/response + broadcast correlation, hands a started game off to the UI thread | Rendering, business rules |
| **Client UI** | `client/ui/` | Graphical wrapper screens + the game board renderer | Network protocol details (screens only see `AppBridge`'s already-parsed events) |
| **Client input** | `client/input/` | Click → logical position mapping, selection state | Move legality |
| **Client CLI / text_test** | `client/cli/`, `client/text_test/` | Legacy textual flow, kept alive only for scripted regression tests | Nothing production-relevant depends on it anymore |

**Key principle, unchanged since the very first iteration:** `shared/rules/rule_engine.py` **never** moves pieces or removes enemies — it only returns a result code (`OK`, `BLOCKED`, `ILLEGAL_SHAPE`, etc.). The actual board mutation happens **only** in `RealTimeArbiter`, and only at the moment of arrival (Atomic Update).

**Key principle, new since the client/server work:** the server is the **single source of truth** for game state. The client (`shared/rules/move_validator.py`) does its own legality pre-check before sending a move/jump, purely so the local board doesn't have to wait a round-trip to reject an obviously illegal click — but the server always re-validates independently (`server/logic/game_session.py::handle_move/handle_jump`, using the exact same `shared/rules` code) and its result is what actually gets broadcast. The client never mutates its board from a local guess; it only ever applies snapshots the server sends (`RemoteGameEngine.apply_snapshot`).

---

## 3. Technologies

- **Python 3.13**
- **pytest** (`pytest.ini` at repo root: `pythonpath = .`, `testpaths = tests`) — 123 tests passing as of this writing, all under `tests/unit/`.
- **Server** (`server/requirements.txt`): `fastapi`, `uvicorn[standard]`. Plus stdlib `sqlite3`, `hashlib`/`secrets` (PBKDF2-HMAC-SHA256 password hashing, 200,000 iterations, random per-user salt — real hashing, not plaintext).
- **Client** (`client/requirements.txt`): `websockets`. Plus `opencv-python` (`cv2`) and `numpy` for the graphical layer — **still not declared in any requirements file**, same open item as before the reorg (see section 10).
- I/O for the legacy text-mode path is via `stdin`/`stdout`, unchanged from the original design.
- Networking: plain WebSocket at `ws://127.0.0.1:8000/ws` (see `client/config.py::SERVER_URI`), one FastAPI route (`server/network/ws_routes.py`), one message envelope shape for everything (`shared/protocol.py::Envelope`).

---

## 4. Project Structure

```
chess-project/
├── Handoff.md                    # this file
├── pytest.ini
├── bus/                           # event bus (pub/sub) decoupling server subsystems
│   ├── event_bus.py                # EventBus: subscribe(type, handler), async publish(event) — sequential, no error isolation
│   ├── events.py                   # ClientConnected, RoomCreated, PlayerJoinedRoom, ViewerJoinedRoom, PlayerQueued, MatchFound, MatchTimeout
│   ├── listeners/                  # the actual event-handling logic
│   │   ├── connection_listener.py    # on_client_connected — currently logs only, no behavior (extension point)
│   │   ├── matchmaking_listener.py   # on_player_queued, _expire_after_timeout — MATCH_TIMEOUT_SECONDS=60
│   │   └── room_listener.py          # on_room_created, on_player_joined_room, on_viewer_joined_room
│   └── subscribers/                # registration glue (register_*_listeners()), called once from server/main.py
│       ├── connection_subscriber.py
│       ├── matchmaking_subscriber.py
│       └── room_subscriber.py
├── shared/                        # the ORIGINAL logic layers, unmodified in behavior, moved here in the reorg
│   ├── protocol.py                 # Envelope(type, payload, request_id, ts) — the one message shape used everywhere
│   ├── model/
│   │   ├── position.py               # Position namedtuple (row,col) — most code still uses raw tuples
│   │   ├── piece.py                  # token_color(), token_type()
│   │   ├── board.py                  # Board: grid, get/set_piece, is_inside, height/width
│   │   ├── game_state.py             # GameState: clock, pending_moves, locked, resting, resting_duration, airborne
│   │   └── standard_setup.py         # STANDARD_START_GRID — the 8x8 starting position
│   ├── rules/
│   │   ├── piece_rules.py            # MOVEMENT_VALIDATORS, is_legal_move, pawn_start_row/promotion_row/is_legal_pawn_* (PIECE_TYPES/COLORS themselves now live in shared/config.py, not a separate piece_registry.py)
│   │   ├── rule_engine.py            # check_move() — the central legality function (OK/OUT_OF_BOUNDS/ILLEGAL_SHAPE/BLOCKED/FRIENDLY_FIRE)
│   │   └── move_validator.py         # [new, server-flow only] validate_move/validate_jump — bounds+ownership pre-check, used by both server's authoritative check and RemoteGameEngine's client-side pre-check
│   ├── realtime/
│   │   ├── motion.py                 # calculate_duration() (Chebyshev), DEFAULT_SPEED=1000, JUMP_DURATION_MS=1000, LONG_REST_MS=1000, SHORT_REST_MS=500
│   │   └── realtime_arbiter.py       # RealTimeArbiter: start_motion, start_jump, advance_time (settle/land/release, in that order)
│   └── engine/
│       └── game_engine.py            # GameEngine: request_move, request_jump, advance_time, is_over, is_locked
├── server/
│   ├── main.py                     # FastAPI app; registers all bus listeners + init_db() at import time; uvicorn.run under __main__
│   ├── config.py                   # server-side constants: TICK_MS/TICK_INTERVAL_SECONDS, DISCONNECT_RESIGN_SECONDS, WIN_BONUS_POINTS/LOSS_PENALTY_POINTS/CAPTURE_BONUS_POINTS, RATING_RANGE, ID_ALPHABET/ID_LENGTH, DB_PATH/SCHEMA_PATH/PBKDF2_ITERATIONS, HANDLERS/RESPONSE_TYPE
│   ├── auth/
│   │   └── auth.py                   # async login(username,password)/register(username,password) -> {"success","message"[,"rating"]}
│   ├── db/
│   │   ├── schema.sql                 # users(id, username UNIQUE, password_hash, salt, rating DEFAULT 1200)
│   │   ├── users_repo.py              # init_db, create_user, verify_user, update_rating — PBKDF2, 200k iterations
│   │   └── chess.db                   # sqlite file (created by init_db, listed in .gitignore)
│   ├── logic/
│   │   ├── rating.py                  # Fixed-point rating: apply_match_result(winner, loser, captures_winner, captures_loser) — winner +WIN_BONUS_POINTS (100), loser -LOSS_PENALTY_POINTS (30), plus a flat capture_bonus(captures) = captures * CAPTURE_BONUS_POINTS added on top for each player, win or lose (no draw support — always a strict winner/loser)
│   │   ├── matchmaking.py             # Matchmaking: enqueue/find_opponent(±100 rating)/remove, QueuedPlayer, 6-char match IDs
│   │   ├── room_manager.py            # RoomManager: create_room/join_room/leave_room, 6-char room IDs, players[0]=white/[1]=black, 3rd+ joiner=viewer
│   │   ├── id_gen.py                  # generate_id(alphabet, length, is_taken=None) — shared random-ID generator; both matchmaking.py and room_manager.py call this instead of duplicating the logic
│   │   └── game_session.py            # GameSession: 100ms tick loop, DISCONNECT_RESIGN_SECONDS=20, broadcasts game_update/game_over/disconnect_countdown; tracks self.captures{WHITE,BLACK} per tick via _record_captures(settled), fed into rating.apply_match_result at game end
│   ├── engine_adapter/
│   │   └── adapter.py                 # create_engine() -> (board, game_state, arbiter, engine) — the one place server builds shared/ objects
│   └── network/
│       ├── ws_routes.py               # the single /ws route; HANDLERS dict (11 message types) + RESPONSE_TYPE remap; disconnect cleanup
│       ├── connection_registry.py     # room_id -> {websocket: client_id}, for broadcast fan-out
│       └── room_broadcaster.py        # broadcast_room_state(room_id, exclude_client_id)
└── client/
    ├── config.py                   # renderer/UI constants (colors, sizes, key codes) shared across client/ui files
    ├── game_setup.py                # build_game(grid) -> (board, game_state, arbiter, game_engine, board_mapper, controller) — LOCAL/hotseat composition root
    ├── main.py                      # graphical entry point: starts the network thread (AppBridge.serve()), runs ScreenManager(bridge, LoginScreen)
    ├── network/
    │   ├── connection.py              # ServerConnection: connect/send/receive/close over websockets
    │   ├── app_bridge.py              # AppBridge — the network-thread <-> main-thread bridge every graphical screen uses (see section 6b)
    │   ├── game_bridge.py             # GameBridge (legacy, used only by client/cli/*.py), build_remote_engine, apply_game_envelope, pump_game_messages
    │   └── remote_game_engine.py      # RemoteGameEngine — Renderer/Controller-compatible stand-in for GameEngine, server is authoritative
    ├── input/
    │   ├── board_mapper.py            # BoardMapper: pixel_to_cell() (square_size=100)
    │   └── controller.py              # Controller: handle_click/handle_jump, selection state
    ├── io_options/
    │   ├── board_parser.py            # read_board/validate_board (used by the local-hotseat text-board-input path)
    │   └── board_printer.py           # print_board()
    ├── cli/                         # LEGACY textual flow — not reachable from client/main.py anymore, kept alive only for client/text_test/script_runner.py
    │   ├── login.py                    # SERVER_URI = "ws://127.0.0.1:8000/ws", do_login()
    │   ├── home.py, play.py, room.py   # textual menu/matchmaking/room flows
    ├── text_test/
    │   ├── script_parser.py           # parse_command(): click/jump/wait/"print board"
    │   └── script_runner.py           # run_commands() — stdin-driven scripted local games, never real time.sleep()
    └── ui/
        ├── UI_DESIGN.md              # renderer/sprite internals for the LOCAL board — predates the client/server split; its own folder-structure section is stale, but the rendering/animation content is still accurate (see note below)
        ├── img.py                    # Img: OpenCV/numpy helper — read/resize, draw_on, put_text, show
        ├── keyboard_layout.py         # force_english_layout()/restore_layout() — Windows-only fix so cv2.waitKey() reliably captures plain ASCII when the OS's active input language isn't English (bugfix; called from screen_manager.py around the wrapper-screen loop)
        ├── renderer.py                # Renderer — draws the board+pieces+panels+game-over overlay; shared by local and networked play alike
        ├── sprite_manager.py          # SpriteManager.determine_state() — idle/move/jump/short_rest/long_rest, reads GameState fields only
        ├── widgets.py                 # Button/TextInput/Label/ErrorText — generic Img-based widgets, used by every wrapper screen
        ├── screen_manager.py          # ScreenManager — the graphical wrapper-screen main loop (see section 6b)
        ├── game_runner.py             # run_graphical_game(bridge, engine) — hands off from a wrapper screen into the Renderer game loop
        ├── app_ui.py                  # LOCAL/hotseat graphical entry point: `python -m client.ui.app_ui` — no networking at all, uses game_setup.build_game
        ├── screens/
        │   ├── base_screen.py          # Screen base class: on_enter/update/render/handle_click/handle_key, next_screen, should_quit
        │   ├── login_screen.py, home_screen.py, room_screen.py, matchmaking_screen.py
        └── game_snapshot/            # sprite/animation assets (board.png + pieces_mine/<color><type>/states/{idle,move,jump,short_rest,long_rest}/)
```

**Note on `.claude/CLIENT_SERVER_PLAN.md`**: the detailed, iteration-by-iteration client/server spec (auth/matchmaking/rooms/graphical-screens design, decisions, and per-iteration acceptance criteria — sections 5/6 below only summarize its conclusions) currently lives at `.claude/CLIENT_SERVER_PLAN.md`, **untracked**, while `CLIENT_SERVER_PLAN.md` at the repo root shows as deleted in `git status` (unstaged). This predates this document's rewrite — it's flagged here as an open item (section 10), not something this rewrite fixed.

**Note on `.claude/UI_IMPLEMENTATION_PLAN.md`**: the earlier, narrower plan (also untracked) for building the *local* graphical board on top of the already-working textual logic — iterations 1–12 covering the static board, sprite/animation states, click/jump handling, game-over overlay, move history, and the rest/lock verification pass. `CLIENT_SERVER_PLAN.md` picks up from where this one leaves off (it explicitly builds atop the finished local graphical board). Kept only for historical iteration rationale — everything it describes is already implemented and summarized in sections 5/6/8 below.

### Files critical to understanding the architecture (read these first)

1. **`shared/engine/game_engine.py`** — the operational heart of move/jump legality and game-over detection.
2. **`shared/realtime/realtime_arbiter.py`** — the only place that actually mutates the board; critical for Atomic Update, capture, promotion, air-capture.
3. **`server/logic/game_session.py`** — the authoritative per-game loop on the server: how a `GameEngine` becomes a live multiplayer session.
4. **`client/network/app_bridge.py`** — the single mechanism every graphical wrapper screen uses to talk to the network thread; understand this before touching any screen.
5. **`client/ui/game_runner.py`** — the hand-off point between "a screen waiting for a game to start" and "the actual board window running."
6. **`.claude/CLIENT_SERVER_PLAN.md`** — full design rationale and iteration history for everything client/server (see note above on its current location).

---

## 5. Components and Modules — Brief Description

### `shared/` (unchanged logic, moved from the old `game-chess/model|rules|realtime|engine/`)
- **`Board`**: wraps `grid`, exposes `get_piece`, `set_piece`, `is_inside`, `height`, `width`.
- **`GameState`**: `clock`, `pending_moves` (from/to/token/completion_time/duration), `locked` (set), `resting`/`resting_duration` (dicts), `airborne` (dict).
- **`piece.py`**: `token_color(token)`, `token_type(token)` — the sole place the `"{color}{type}"` token format is parsed.
- **`rule_engine.py`**: `check_move(board, piece_type, piece_color, from_pos, to_pos)` — pure legality, no mutation, no ownership check (that's `move_validator`'s job).
- **`move_validator.py`** *(new)*: `validate_move`/`validate_jump` — bounds + "is this your piece" checks, then delegates to `rule_engine`. Used identically on both sides of the network: `RemoteGameEngine.request_move` (client-side optimistic pre-check) and `server/logic/game_session.py::handle_move` (server-side authoritative check) call the exact same function — no duplicated legality logic between client and server.
- **`realtime_arbiter.py`**: `RealTimeArbiter.advance_time(ms)` — settles due moves (Atomic Update + air-capture-takes-priority + auto-promotion), lands due jumps (→ `SHORT_REST_MS`), releases due rests, in that fixed order.
- **`game_engine.py`**: `GameEngine.request_move/request_jump` gate on `is_over` then `is_locked(pos)` (locked OR resting) then rule legality; `advance_time` sets `is_over=True` the moment any settled move's `captured_token` is a king.

### `bus/` — event bus decoupling server subsystems
- **`EventBus`**: `subscribe(EventClass, handler)`, `async publish(event)` — iterates subscribers in registration order, awaits coroutine handlers; no error isolation (one handler raising stops the rest for that publish call — worth knowing if debugging a "downstream broadcast never arrived" bug).
- Events: `ClientConnected` (published, currently logged only — no functional subscriber yet), `RoomCreated`/`PlayerJoinedRoom`/`ViewerJoinedRoom` (room lifecycle → `bus/listeners/room_listener.py`, which also decides when a room's 2nd player triggers `game_session_manager.start_for_room`), `PlayerQueued`/`MatchFound`/`MatchTimeout` (matchmaking lifecycle → `bus/listeners/matchmaking_listener.py`).

### `server/` — auth, rating, matchmaking, rooms, authoritative sessions
- **`auth.py`**: `login`/`register` — real PBKDF2-HMAC-SHA256 hashing (200k iterations, random salt) via `users_repo.py`, run off the event loop with `asyncio.to_thread`. No username/password format validation beyond "not already taken."
- **`rating.py`**: fixed-point rating (not ELO) — the winner gains a flat `WIN_BONUS_POINTS=100`, the loser loses a flat `LOSS_PENALTY_POINTS=30`, plus a flat **capture bonus** (`CAPTURE_BONUS_POINTS=2` per piece captured, `capture_bonus(captures)`) added on top for *each* player independently, based on their own capture count for that game — win or lose. New players start at 1200 (`schema.sql` column default). **No draw support** — `apply_match_result` always takes a strict winner/loser, called once per finished game from `game_session.py::_finish_game`.
- **`matchmaking.py`**: in-memory queue, `find_opponent` matches within `RATING_RANGE=100`; the player already in queue becomes white, the newly-queued one black.
- **`room_manager.py`**: in-memory rooms keyed by a 6-char generated ID; first 2 joiners are `players` (joiner 0 = white), everyone after is a `viewer`.
- **`game_session.py`**: `GameSession` — one per active game (room- or matchmaking-based), owns a fresh `shared/` engine via `engine_adapter.create_engine()`, ticks every 100ms, only broadcasts `game_update` when something is actually active (not on fully-idle ticks), auto-resigns a disconnected player after a 20s countdown (`disconnect_countdown` broadcasts, once/second). Also tallies `self.captures[WHITE]`/`self.captures[BLACK]` every tick (`_record_captures`, reading each settled move's `captured_token`/`air_capture` fields), passed to `rating.apply_match_result` as `captures_winner`/`captures_loser` once the game ends. The resulting `new_ratings` dict is broadcast in the `game_over` payload; `RemoteGameEngine.mark_game_over` stores it, and `MatchmakingScreen`/`RoomScreen._enter_game` read the current user's entry out of it to refresh `self.rating` *before* navigating back to `HomeScreen`, so the home screen shows the post-game rating immediately without a reconnect/refresh.
- **`ws_routes.py`**: one `/ws` route. `HANDLERS` = `echo, login, register, menu_select, create_room, join_room, cancel_room, play, cancel_play, move, jump`. **Important asymmetry to know before touching client network code**: most handlers return a `dict` payload that the route wraps into a correlated response (matching `request_id`); a few (`join_room` on success, `play` on success) instead send their own envelope *directly*, with **no `request_id`** — these arrive client-side as an uncorrelated broadcast, not a request/response pair. Any new screen/handler that sends a request and expects a specific reply shape must check the actual handler code, not assume symmetry (see section 7, new decision on this).

### `client/network/` — the WebSocket layer
- **`ServerConnection`**: thin `connect`/`send`/`receive`/`close` wrapper over `websockets`.
- **`RemoteGameEngine`**: same public surface as the local `GameEngine` (`request_move`, `request_jump`, `advance_time`, `is_over`, `is_locked`) so `Controller`/`Renderer` don't know or care whether they're driving a local or networked game. Never mutates board/state from a local guess — `request_move`/`request_jump` only pre-validate (via `shared/rules/move_validator`) and forward to the server; `apply_snapshot` (driven by `game_update` envelopes) is the only thing that ever actually changes `self.board`/`self.game_state`.
- **`AppBridge`** *(the graphical wrapper-screen network layer, see section 6b)* vs. **`GameBridge`** *(older, narrower — only used by the legacy `client/cli/*.py` flow that `client/text_test/script_runner.py` still depends on)*. Don't confuse the two: `AppBridge` is what every current screen (`Login`/`Home`/`Room`/`Matchmaking`) actually uses.

### `client/ui/` — graphical board + wrapper screens
- **`Renderer`**: draws board/pieces/animations/rest-bars/move-history panels/player names/game-over overlay + (since the "back to menu" work) a "Back to Menu" button once `game_engine.is_over`. Opens one `cv2` window (`WINDOW_NAME = "Image"`, imported from here by `screen_manager.py` so the wrapper-screen flow and the in-game board never open two separate windows). `render()` returns `False` on any stop (quit key, window closed, or the menu button); callers that need to tell the difference check `self.wants_menu` afterward.
- **`ScreenManager`**: the wrapper-screen main loop (Login/Home/Room/Matchmaking) — see section 6b.
- **`game_runner.run_graphical_game(bridge, engine)`**: builds `BoardMapper`+`Controller`+`Renderer` from a `RemoteGameEngine` and blocks the calling (main) thread in a frame loop until the game window closes, draining `AppBridge.poll_events()` each frame to apply `game_update`/`game_over`/`disconnect_countdown`/`*_rejected` envelopes to the engine. Returns `True` if the user clicked "Back to Menu", `False` if they quit outright.
- **`screens/*.py`**: `LoginScreen` → `HomeScreen` → `RoomScreen` or `MatchmakingScreen` → (on `game_started`) `game_runner.run_graphical_game` → back to `HomeScreen` (if "Back to Menu") or process end (if quit). All screens follow the same `on_enter(payload)`/`update()`/`render(canvas)`/`handle_click(x,y)`/`handle_key(key)` contract (`base_screen.py::Screen`).

### `client/input/`
- **`BoardMapper.pixel_to_cell(x,y)`**, **`Controller.handle_click/handle_jump`** — unchanged from the original design; works identically against a local `GameEngine` or a `RemoteGameEngine`.

### `client/cli/` + `client/text_test/`
- The original textual login/home/play/room flow. **No longer reachable from `client/main.py`** (which now always opens the graphical `LoginScreen` first) — kept alive solely because `client/text_test/script_runner.py` still drives scripted regression scenarios through it. Don't delete without checking that dependency first.

---

## 6. Data Flow (End-to-End)

### 6a. Core move/jump logic (unchanged since before the client/server work, applies identically to local and networked play)

**Regular move (click → click):**
1. `Controller.handle_click` → `BoardMapper.pixel_to_cell` → if a piece is there and not locked → `selected = {pos, color}`.
2. Second click → same-color reselect, or `GameEngine.request_move(from_pos, to_pos)` (destination lock/rest state is irrelevant here — only the *mover*'s state matters; a locked/resting enemy piece is always a legal capture target).
3. `GameEngine` checks `is_over` → `is_locked(from_pos)` → `rule_engine`/`move_validator` legality.
4. If `OK` → `arbiter.start_motion` → registered in `pending_moves`, `locked.add(from_pos)`. **The board has not changed yet.**
5. Only once enough time has passed (`advance_time`) does `_settle_due_moves` perform the actual Atomic Update (promotion / air-capture / king-capture check), and start the destination's rest/cooldown (`LONG_REST_MS`).

**Jump:** `Controller.handle_jump` → `GameEngine.request_jump(pos)` → `arbiter.start_jump(pos)` → `airborne[pos] = clock + JUMP_DURATION_MS`. If an enemy move's destination lands on that cell while airborne, `_settle_due_moves` treats it as an air-capture (checked *before* the regular Atomic Update) instead of a normal capture. Landing safely starts a shorter rest (`SHORT_REST_MS`).

### 6b. Networked flow: connect → play → back to menu

1. **`client/main.py`** starts a background daemon thread running `asyncio.run(bridge.serve())` (`AppBridge`), then blocks the main thread in `ScreenManager(bridge, LoginScreen).run()`.
2. **`LoginScreen.on_enter`** calls `bridge.connect(SERVER_URI)`. Success/failure/each subsequent server reply surfaces as an `AppEvent` (`CONNECTED`/`CONNECTION_LOST`/`RESPONSE`/`BROADCAST`) via `bridge.poll_events()`, polled once per frame from each screen's `update()`. `RESPONSE` events are the ones whose `Envelope.request_id` matches the bridge's single in-flight `_pending_request_id` (set by `send_request`); everything else — including some *successful* replies that the server happens to send directly without a `request_id` (see the `ws_routes.py` asymmetry noted in section 5) — arrives as `BROADCAST`. **Screens must not assume a reply to their own request always comes back as `RESPONSE`** — check the actual handler in `ws_routes.py` for how a given message type replies.
3. Successful login/register → `HomeScreen` (username + rating carried as payload, never re-fetched). `HomeScreen`'s Play/Room buttons send `menu_select` (a client-side navigation ack only — it does **not** actually queue for a match or create/join a room) and move to `MatchmakingScreen`/`RoomScreen`.
4. **`MatchmakingScreen.on_enter`** immediately sends `play`; **`RoomScreen`** waits for a Create/Join click before sending `create_room`/`join_room`. Both screens funnel every subsequent bridge event through the same pattern: state-specific handling, **except** `game_started`/`match_timeout` (Matchmaking) which are always checked first, unconditionally, so a match found in the instant after the user clicks Cancel is still honored — mirrors the `resolved` flag the legacy `client/cli/play.py::_wait_for_match` already used.
5. On `game_started`, the screen calls `bridge.build_remote_engine(payload)` (constructs a `RemoteGameEngine` whose `send_move`/`send_jump` schedule onto `AppBridge`'s own captured event loop — **not** `asyncio.get_running_loop()`, since this runs on the main thread, which has no running loop of its own) and then blocks in `game_runner.run_graphical_game(bridge, engine)`.
6. When that returns, the screen first refreshes `self.rating` from `engine.new_ratings.get(self.username, self.rating)` (populated from the `game_over` payload — see decision #26) before transitioning back to `HomeScreen`, so the just-updated rating shows up on the home screen with no reconnect/refresh needed. It transitions back to `HomeScreen` (`username`/refreshed `rating` payload, **no re-login** — the WebSocket connection and `AppBridge` are untouched) if the user clicked "Back to Menu", or sets `self.should_quit = True` (ends `ScreenManager.run()` entirely) if they quit outright. Either way, `ScreenManager` re-creates the `cv2` window + mouse callback on the next screen transition, since `Renderer` always calls `cv2.destroyAllWindows()` on its own way out.
7. Server side, in parallel: `GameSession` ticks every 100ms, broadcasting `game_update` only when something is actually active, `game_over` once a king is captured (updates both players' rating via `rating.apply_match_result` — fixed win/loss points plus capture bonus, see decision #26), and `disconnect_countdown` if either player's socket drops (20s auto-resign).

---

## 7. Important Architectural/Business Decisions Made

*(Decisions #1–14 below predate the client/server work and concern only the core game logic in `shared/` — folder paths updated from the old `game-chess/model|rules|realtime|engine/` to their current `shared/` location; nothing about the decisions themselves changed in the move.)*

1. **`io` → `io_options`**: renamed because `io` clashes with a Python stdlib module.
2. **Entry points split by concern**: `client/ui/app_ui.py` is the local/hotseat graphical entry (no networking); `client/main.py` is the networked graphical entry (default since the client/server work); `client/cli/*.py` is the legacy textual flow, reachable today only via `client/text_test/script_runner.py`. `client/game_setup.py::build_game(grid)` is the shared local-mode composition root so `app_ui.py` doesn't duplicate wiring.
3. **`is_locked` as a query, checked only where it applies**: `GameEngine.is_locked(pos)`, queried by `Controller` only when picking up a piece or switching selection — never on the move/capture-destination branch (a locked/resting enemy piece is always a legal capture target, decision #13 below).
4. **Global Lock — removed, per-piece only.** `GameEngine.request_move`/`request_jump` gate on `self.is_locked(from_pos)` (that specific square's `locked`/`resting` state), not on any board-wide lock. Any number of pieces on either side can be mid-motion simultaneously.
5. **Move duration = Chebyshev distance** (`max(|dx|,|dy|)`), not Euclidean — matches real chess (diagonal costs the same as straight).
6. **`DEFAULT_SPEED = 1000`** ms/square.
7. **Pawn start row is board-height-dependent**: `height-2` for white, `1` for black (not the back rank).
8. **Promotion row**: `0` for white, `height-1` for black.
9. **Air capture takes priority over regular settlement** in `_settle_due_moves` — checked before the normal Atomic Update.
10. **Jump legality uses the same `is_locked(pos)` as regular moves** — a resting piece can't jump either.
11. **Pawns are handled via a separate path** in `rule_engine.check_move` (asymmetric move≠capture, color-dependent) rather than through `MOVEMENT_VALIDATORS`.
12. **Rest/cooldown after arrival**: `GameState.resting`, checked by `GameEngine.is_locked`. `LONG_REST_MS=1000` after a regular move settles, `SHORT_REST_MS=500` after a jump lands safely. Per-position, not global.
13. **A locked/resting piece can always be *captured* — only *picking one up* was ever meant to be blocked.** `request_move` only ever checks the mover's lock state, never the target's; `Controller.handle_click` was the actual (fixed) bug source, not the engine.
14. **Small additive exposures for the UI, no behavior change**: `start_motion(..., duration)` stored on the `pending_moves` entry; `GameState.resting_duration`; `GameEngine.advance_time` returning `settled`.

**New decisions from the client/server build (iterations 0–16 of `.claude/CLIENT_SERVER_PLAN.md`):**

15. **Server framework: FastAPI + plain WebSockets**, one `/ws` route, one `Envelope(type, payload, request_id, ts)` shape for every message in both directions — no per-message-type endpoint proliferation. `ts` is defined on `Envelope` but never actually populated by any current code (vestigial).
16. **DB access: raw `sqlite3`, no ORM** — `server/db/users_repo.py`, password hashing done with real PBKDF2 (not plaintext), off the event loop via `asyncio.to_thread`.
17. **Server-side subsystem decoupling via an event bus** (`bus/`), not direct cross-module calls — e.g. `room_manager`/`matchmaking` never call `game_session_manager` directly; a `bus` listener does, in response to a published event. Trade-off: no error isolation between handlers of the same event (one raising stops the rest).
18. **Client-side move validation is optimistic, server is authoritative** — both sides call the *same* `shared/rules/move_validator` functions rather than duplicating legality logic; the server's answer, not the client's guess, is what gets broadcast.
19. **Request/response correlation is not fully symmetric** — most handlers reply through the normal `request_id`-correlated path, but a couple (`join_room` success, `play` success) send their own envelope directly with no `request_id`, arriving client-side as an uncorrelated broadcast instead. Discovered while building `RoomScreen`/`MatchmakingScreen` (iterations 14–15) by probing the live server rather than assuming symmetry — **any new screen must verify this per message type, not assume it.**
20. **`AppBridge` generalizes the older `GameBridge` pattern** (queue-based cross-thread handoff) to every graphical wrapper screen, not just the game-start handoff — but `GameBridge` itself was kept, not replaced, since `client/cli/*.py` (needed by `client/text_test/script_runner.py`) still uses it directly.
21. **The legacy game loop (`_run_graphical_game`, originally in `client/main.py` before the graphical Login/Home rewrite) was resurrected as `client/ui/game_runner.py::run_graphical_game`**, adapted to pull game messages from `AppBridge.poll_events()` per frame instead of a separate `asyncio` task reading the connection directly — `AppBridge` already owns the one continuous receive loop on the network thread, so a second concurrent reader on the same connection was never an option once wrapper screens (not just the CLI) needed the connection too.
22. **"Back to Menu" is a button drawn inside the existing game window** (`Renderer`, once `is_over`), not a separate screen — the one deliberate, pre-approved touch to `renderer.py` in the whole 11–16 iteration batch. Returning to `HomeScreen` afterward reuses the same connection (no re-login). A consequence not anticipated by the original design doc: since `Renderer` always destroys its `cv2` window on any exit (quit or menu), `ScreenManager` has to explicitly recreate the window + mouse callback on every screen transition, or the resumed wrapper screen would render into a dead/uncallbacked window.
23. **Viewers who join a room mid-game stay on the room wait screen in "viewer" status** — no live spectator board rendering exists yet, in the graphical flow or the legacy CLI one. Explicitly deferred, not a regression (see section 9).
24. **Keyboard layout is forced to English (US) while any text-entry wrapper screen is open** (`client/ui/keyboard_layout.py::force_english_layout`/`restore_layout`, Windows-only, called around `ScreenManager`'s loop) — `cv2.waitKey()` has no IME/Unicode awareness and returns whatever the OS's *currently active* input language produces, so under a non-Latin layout the same physical letter keys were silently dropped by `TextInput.handle_key`'s plain-ASCII check. Fixed at the OS-input-language level since `cv2` itself never sees a layout-independent key code.
25. **Room/match ID generation was unified**: `server/logic/id_gen.py::generate_id(alphabet, length, is_taken)` is the one place that generates a random ID and retries on collision; both `Matchmaking.generate_match_id()` and `RoomManager`'s room-ID generator call it with the same `ID_ALPHABET`/`ID_LENGTH` now defined once in `server/config.py`, instead of duplicating the pattern (resolves the TODO item that used to be listed in section 10).
26. **Rating now rewards captures, not just win/loss**: `GameSession` counts each settled move's captured piece per color as it happens (`_record_captures`), crediting the *mover*'s color for a regular capture but the *defending* color for an air-capture (the airborne piece captures the arriving mover, per decision #9's air-capture-priority rule — see `shared/config.py::AIR_CAPTURE_KEY`, set by `RealTimeArbiter._settle_air_capture`). At game end, each player's own capture count adds a flat `CAPTURE_BONUS_POINTS` (`server/config.py`, currently 2) per capture on top of the win/loss result — independent of who won, so a losing player who traded material still gets partial credit.
27. **Rating switched from ELO to a fixed-point scheme, and the client-side "stale rating on Home" bug was fixed together**: `rating.py::apply_match_result` no longer computes an ELO delta — the winner always gains a flat `WIN_BONUS_POINTS=100` and the loser always loses a flat `LOSS_PENALTY_POINTS=30` (plus each side's capture bonus from decision #26), because the ELO formula made the point swing depend on the opponent's rating, which didn't match the product requirement of fixed, predictable point values. Separately, the `game_over` payload's `new_ratings` dict was previously computed correctly on the server but silently dropped on the client — `RemoteGameEngine.mark_game_over` only set `is_over = True` and never stored it, so `MatchmakingScreen`/`RoomScreen` kept navigating back to `HomeScreen` with the pre-game `self.rating`, which only became correct after a manual re-login. Fixed by having `mark_game_over` store `payload.get("new_ratings", {})` on the engine, and having each screen's `_enter_game` read `engine.new_ratings.get(self.username, self.rating)` right after `run_graphical_game` returns, before building the `HomeScreen` payload.

---

## 8. What Has Already Been Completed

**Core logic** (`shared/`, unchanged since before the client/server work):
1. ✅ Model (`Board`, `GameState`, `piece.py`), full legality rules (K/Q/R/B/N + full pawn rules incl. promotion), real-time arbiter (Atomic Update, logical `wait`, never real `sleep`), captures + game-over on king capture, jump + air-capture, per-piece lock/rest (no global lock).

**Client/server layer** (`.claude/CLIENT_SERVER_PLAN.md` iterations 0–16, all implemented):
2. ✅ WebSocket infra, `Envelope` protocol, auth with real password hashing + persistent rating.
3. ✅ Matchmaking (rating-range queue, 60s timeout) and Rooms (create/join by ID, player/viewer roles, cancel).
4. ✅ Authoritative server-side `GameSession` (100ms tick, disconnect auto-resign with countdown, fixed-point win/loss rating + per-capture bonus on finish — see decisions #26–27).
5. ✅ `RemoteGameEngine` + the existing `Renderer`/`Controller` reused unmodified for networked play.
6. ✅ Full graphical wrapper-screen flow replacing the textual menu as the default entry: `LoginScreen` → `HomeScreen` → `RoomScreen`/`MatchmakingScreen` → game board → "Back to Menu" → `HomeScreen` again (no re-login). `client/main.py` defaults to this graphical flow; `client/cli/*.py` untouched, still used by `client/text_test/script_runner.py`.

**Test coverage**: 117 unit tests passing (`pytest`), spanning `shared/` logic, `client/input/`, and (unlike the pre-reorg state) the graphical wrapper screens themselves (`test_app_bridge.py`, `test_base_screen.py`, `test_home_screen.py`, `test_login_screen.py`, `test_placeholder_screens.py` — the last covers `RoomScreen`/`MatchmakingScreen`'s `on_enter`/`render` via a stub bridge, `test_widgets.py`). The board-rendering/animation internals of `Renderer`/`SpriteManager` still have no automated tests — verified manually per iteration, same as before the reorg.

---

## 9. What Is Still Missing

- **Iteration 17 of `.claude/CLIENT_SERVER_PLAN.md`** — full manual end-to-end pass (Login → Home → Play/Room → game → Game Over → Home, with no textual fallback anywhere), confirming the disconnect/auto-resign countdown still renders correctly through the new graphical entry path, and a regression check that `client/text_test/script_runner.py`'s CLI-driven scenarios are unaffected. Not yet done as of this document.
- **Live spectator board rendering** for viewers who join a room mid-game — currently they just sit on the room wait screen in "viewer" status (both in the legacy CLI and the current graphical flow). Explicitly flagged as a future iteration (18+) in `.claude/CLIENT_SERVER_PLAN.md` §5, not a bug.
- **No draw/stalemate concept anywhere** — `rating.apply_match_result` only ever takes a strict winner (`score_a=1`); there is no path that produces a draw, in the rules layer or the rating layer.
- **`opencv-python`/`numpy` still not declared in any requirements file** — same open item as before the reorg, now arguably more pressing since `client/ui/renderer.py`, `game_runner.py`, and every `client/ui/screens/*.py` all depend on them, not just `img.py`.
- **`CLIENT_SERVER_PLAN.md` missing from the repo root** (see the note in section 4) — the only copy is an untracked file under `.claude/`.
- **En Passant, Castling** — not implemented (never required by any iteration so far, in either the old or new plan).
- **No formal error-feedback channel** for illegal moves in the local/text-mode path — `Controller`/`GameEngine` still just silently `return`.

---

## 10. TODO List

- [ ] Do the iteration-17 manual end-to-end pass + CLI regression check described in section 9.
- [ ] Decide whether to restore `CLIENT_SERVER_PLAN.md` at the repo root (from `.claude/CLIENT_SERVER_PLAN.md`) and commit it, or deliberately keep planning docs under `.claude/` going forward.
- [ ] Declare `opencv-python`/`numpy` as real dependencies somewhere (`client/requirements.txt` currently only lists `websockets`).
- [ ] Reconcile `speed_m_per_sec` (in `client/ui/game_snapshot/**/config.json`) against `shared/realtime/motion.py`'s `DEFAULT_SPEED`/Chebyshev distance — still unreconciled; the renderer ended up using `frames_per_sec` for animation timing instead, so this was never actually forced.
- [ ] If a live spectator board is ever needed (section 9), decide whether it reuses `Renderer` in a read-only mode or gets its own component.
- [ ] `bus/events.py`'s `ClientConnected` currently has no functional subscriber (logging only) — a natural extension point if presence-tracking or similar is ever needed, but nothing depends on it today.
- [ ] When adding custom piece types (future) — avoid hardcoded `if piece_type == "X"` branches; extend `shared/rules/piece_registry.py` into a real data-driven registry instead.
- [ ] Consider adding a feedback/error channel to `Controller`/`GameEngine` instead of silent `return` on illegal local-mode moves.
- [ ] Test coverage gap: `Renderer`/`SpriteManager` rendering/animation logic, En Passant, Castling — none exists.

---

## 11. Constraints and Principles That Must Not Be Violated

1. **`shared/rules/rule_engine.py` never moves pieces or removes enemies** — only returns a result code.
2. **The logical board only changes inside `RealTimeArbiter._settle_due_moves`** (Atomic Update) — never at the moment a request is sent.
3. **`GameEngine` contains no piece-specific rules, no drawing, no pixel mapping, no networking.**
4. **`Controller` does not check move legality** — only manages selection state and forwards requests.
5. **Tests never use real `time.sleep()`** — always `engine.advance_time(ms)`.
6. **No direct coupling to the token format (`"wR"`) outside `shared/model/piece.py`** — always go through `token_color`/`token_type`.
7. **Piece-type/movement-rule definitions stay data-centralized** (`shared/rules/piece_registry.py`/`piece_rules.py`), not burned into `rule_engine`/`game_engine`.
8. **Move speed = Chebyshev distance**, not Euclidean.
9. **The server is the single source of truth for game state** — the client only ever *requests* moves/jumps (after its own optimistic pre-check via `shared/rules/move_validator`) and *applies* snapshots the server sends; it never mutates its own board from a local guess.
10. **Legality logic is never duplicated between client and server** — both call the exact same `shared/rules` functions.
11. **`AppBridge`/`ScreenManager`/screens contain no game rules** — they only do network plumbing, navigation, and widget rendering; the moment a game actually starts, control passes entirely to the unmodified `Renderer`/`Controller`/`RemoteGameEngine` triplet.
12. **`client/ui/renderer.py`'s core drawing (board, pieces, animations, panels, rest bars, player names) does not change based on whether the game is local or networked** — the only engine-specific thing it reads is duck-typed (`GameEngine`/`RemoteGameEngine` both expose the same surface); don't special-case one mode inside `Renderer` if it can instead live in the engine object itself.

---

## 12. Working Assumptions

- The board can be of any size — code references `board.height`/`board.width` dynamically, never a hardcoded row number.
- `square_size = 100` pixels, fixed, independent of board size.
- A piece token is always `"{color}{type}"` or `"."` — never accessed as raw `token[0]`/`token[1]` outside `shared/model/piece.py`.
- `DEFAULT_SPEED=1000`, `JUMP_DURATION_MS=1000`, `LONG_REST_MS=1000`, `SHORT_REST_MS=500` — global constants in `shared/realtime/motion.py`.
- Server always listens at `ws://127.0.0.1:8000/ws` (`client/config.py::SERVER_URI` — also the value every graphical screen's `AppBridge.connect()` call uses).
- Starting rating is **1200**; win **+100**, loss **-30**, capture **+2** each (per player, regardless of who won — see decision #27); matchmaking rating range is **±100**; match/room IDs are 6-char `[A-Z0-9]` strings.
- The graphical board window and every wrapper screen share **one** `cv2` window (`WINDOW_NAME = "Image"`, defined in `client/ui/renderer.py`, imported — never redefined — by `client/ui/screen_manager.py`).

---

## 13. Additional Important Information for Continuing the Work

- **Iteration workflow**: both the original core-logic project and the client/server layer were built one small, explicitly-scoped iteration at a time, each verified before moving to the next. For the client/server layer specifically, the full iteration list (with locked-in decisions and acceptance criteria per iteration) lives in `.claude/CLIENT_SERVER_PLAN.md` — read the exact iteration's section before touching anything, don't implement ahead of what's been asked for.
- **Any touch to an existing, already-working file requires showing the exact diff and getting it approved before writing it** — this applies even when the general direction was already agreed on elsewhere (e.g. in the plan doc itself). This came up concretely during the "Back to Menu" work (section 7, decision #22): the plan doc pre-approved touching `renderer.py`/`main.py` in principle, but the exact diff — including a consequence the plan hadn't anticipated (`ScreenManager` needing to recreate its window/callback) — was still shown and approved before being written.
- **Don't assume server response symmetry** — verify the actual handler in `server/network/ws_routes.py` for any new message type before writing client code against it; probe the live server if in doubt (see decision #19). A wrong assumption here silently drops messages into the wrong event-kind bucket rather than crashing.
- **The bug-discovery process for the core game logic** relied mainly on external tests (input/expected-output) rather than only internal unit tests — when they conflicted, the external spec won and internal tests were updated (happened with `pawn_start_row` and `DEFAULT_SPEED`). When a test failure comes in, always ask first: is this a real regression, or is the test itself now outdated relative to a deliberate recent change?
- Keep two future extensions in mind for the core logic: binary board representation, and custom user-defined pieces — evaluate every change to `piece.py`/`piece_rules.py`/`rule_engine.py` against "does this make either harder?"
- No formal, consolidated commit message convention is enforced, but Conventional Commits style is what's been used so far.
- **Code style: no explanatory comments or docstrings that just restate what the code does.** The codebase was swept clean of these (module/function docstrings describing behavior, inline "why this branch" comments, circular-import explanations, etc.) — well-named identifiers carry that job instead. Only add a comment when it captures something a reader truly couldn't infer from the code (a hidden constraint, a workaround for a specific external bug) — and even then, keep it to one line.
