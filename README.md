# Kung Fu Chess

A **real-time, multiplayer chess variant** written in Python. There are no turns: both players move their pieces whenever they want. Each move takes time to complete, and a piece that has just moved must rest before it can act again. The game ends the moment a king is captured.

The project has three parts:

- **Shared game engine**: pure Python rules, real-time movement and capture logic. Used by both the client and the server.
- **Authoritative game server**: FastAPI + WebSockets. Handles accounts, ratings, matchmaking, private rooms and live game sessions.
- **Graphical client**: OpenCV. Covers login, the main menu, matchmaking and rooms, and an animated game board.

---

## Table of Contents

1. [Game Rules](#game-rules)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Project Structure](#project-structure)
5. [Getting Started](#getting-started)
6. [How to Play](#how-to-play)
7. [Network Protocol](#network-protocol)
8. [Rating System](#rating-system)
9. [Configuration](#configuration)
10. [Testing](#testing)
11. [Design Principles](#design-principles)
12. [Known Limitations](#known-limitations)

---

## Game Rules

Kung Fu Chess uses the standard chess pieces and starting position, but plays in real time.

| Concept | Behavior |
|---|---|
| **No turns** | Either player can move any of their available pieces at any moment. Many pieces can be in motion at once. |
| **Move duration** | A move takes `1000 ms × distance`. Distance is the Chebyshev distance `max(|Δrow|, |Δcol|)`, so diagonal steps cost the same as straight ones. |
| **In-flight pieces** | While a piece is moving it is *locked* and can't be selected again. The board doesn't change until the move arrives. |
| **Atomic arrival** | Captures happen only when a moving piece **arrives** at its destination. A piece in flight can't be captured mid-path. |
| **Rest (cooldown)** | After arriving, a piece rests for **4 s** (long rest). It can't move or jump until the rest ends, but enemies can still capture it. |
| **Jump** | A piece can jump in place for **1 s**. If an enemy piece arrives on that square while it's airborne, the *jumping* piece wins and the attacker is removed (**air capture**). After landing safely, the piece rests for **2 s** (short rest). |
| **Promotion** | A pawn that reaches the last rank becomes a queen automatically. |
| **Game end** | There is no check or checkmate. The game ends **immediately** when a king is captured. A player who disconnects and doesn't return within **20 s** forfeits. |

Standard piece movement applies: king, queen, rook, bishop and knight move as usual; sliding pieces (queen, rook, bishop) are blocked by pieces in their path. Pawns move one square forward, two from their starting row, and capture diagonally. Castling and en passant are not implemented.

---

## Features

- **Accounts**: registration and login, with passwords hashed using PBKDF2-HMAC-SHA256 (200,000 iterations, random per-user salt). Data is stored in SQLite.
- **Persistent rating**: every player starts at 1200. Ratings update after each game.
- **Matchmaking**: a queue that pairs players whose ratings are within ±100 of each other. The search times out after 60 s.
- **Private rooms**: create a room and share its 6-character ID. The first two people to join are the players; anyone after that joins as a spectator.
- **Server-authoritative games**: the server runs the game loop (one tick every 100 ms), checks every move, and sends state snapshots to all participants.
- **Disconnect handling**: if a player drops mid-game, everyone sees a 20-second countdown, after which that player forfeits.
- **Animated board**: sprite animations per piece state (idle, move, jump, long rest, short rest), smooth movement between squares, rest-progress bars, a move history panel per player, player names, and a game-over screen with a "Back to Menu" button.
- **Local hotseat mode**: two players on one computer, with no server.

---

## Architecture

```
┌─────────────────────────── Client (per player) ───────────────────────────┐
│                                                                            │
│   Main thread (OpenCV window)                 Network thread (asyncio)     │
│   ┌──────────────────────────────┐            ┌────────────────────────┐   │
│   │ ScreenManager                │  events    │ AppBridge              │   │
│   │  Login → Home → Room /       │◄───queue───│  WebSocket receive loop│   │
│   │  Matchmaking → Game board    │───send────►│  request/response      │   │
│   │                              │            │  correlation           │   │
│   │ Renderer + Controller        │            └───────────┬────────────┘   │
│   │ RemoteGameEngine (mirror)    │                        │                │
│   └──────────────────────────────┘                        │                │
└───────────────────────────────────────────────────────────┼────────────────┘
                                                            │  WebSocket (JSON Envelopes)
┌───────────────────────────── Server ──────────────────────┼────────────────┐
│                                                           ▼                │
│   ws_routes (/ws) ──► handlers ──► auth / matchmaking / room_manager       │
│                           │                                                │
│                           ▼                                                │
│                     Event Bus (pub/sub) ──► listeners ──► GameSessionManager│
│                                                               │            │
│                                                               ▼            │
│                                     GameSession (100 ms tick loop)         │
│                                       └─ shared GameEngine                 │
│                                                                            │
│   SQLite (users, ratings)                                                  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Layers

| Layer | Location | Responsibility |
|---|---|---|
| **Model** | `shared/model/` | Board grid, piece tokens, game state (clock, moving, resting and airborne pieces). |
| **Rules** | `shared/rules/` | Move legality only: piece shape, blocking, friendly fire, ownership. Never changes the board. |
| **Real-time** | `shared/realtime/` | Logical clock, move durations, settling moves on arrival, jumps, rests, promotion, air captures. The only code that changes the board. |
| **Engine** | `shared/engine/` | Coordinates a move or jump request: checks, then starts the motion; detects game over. |
| **Protocol** | `shared/protocol.py` | `Envelope(type, payload, request_id, ts)`, the single message format used in both directions. |
| **Server logic** | `server/auth`, `server/db`, `server/logic` | Authentication, ratings, matchmaking, rooms, live game sessions. |
| **Event bus** | `bus/` | Publish/subscribe layer that keeps server parts decoupled (e.g. a full room triggers a game start through an event). |
| **Server network** | `server/network`, `server/engine_adapter` | The WebSocket route, message dispatch, room broadcasts, engine construction. |
| **Client network** | `client/network` | WebSocket connection, the thread bridge, and the server-driven game engine mirror. |
| **Client UI** | `client/ui` | Menu screens, widgets, board renderer, sprite animation. |
| **Client input** | `client/input` | Converts pixel clicks into board squares and tracks the selected piece. |

### Key design ideas

- **The server is the source of truth.** The client checks a move locally (with the same `shared/rules` code) only to skip obviously illegal requests. The server checks every move again on its own, and the client changes its board **only** by applying snapshots from the server (`RemoteGameEngine.apply_snapshot`).
- **No duplicated rules.** Client and server both call `shared/rules/move_validator.py`.
- **Same board UI for every mode.** `Renderer` and `Controller` work with any engine that has the `GameEngine` interface (`request_move`, `request_jump`, `advance_time`, `is_locked`, `is_over`), so the same board code runs local games (`GameEngine`) and network games (`RemoteGameEngine`).
- **Separate threads.** OpenCV's window loop runs on the main thread. All WebSocket I/O runs on a background asyncio thread inside `AppBridge`, and results come back through a thread-safe queue that each screen reads once per frame.

---

## Project Structure

```
chess-project/
├── shared/                         # Game logic used by both client and server
│   ├── config.py                   # Piece/color constants, message types, payload keys
│   ├── protocol.py                 # Envelope message format
│   ├── model/
│   │   ├── board.py                # Board: grid access, bounds checks
│   │   ├── game_state.py           # Clock, pending moves, locked/resting/airborne pieces
│   │   ├── piece.py                # Token parsing ("wK" → color "w", type "K")
│   │   ├── position.py             # Position(row, col)
│   │   └── standard_setup.py       # Standard 8×8 starting position
│   ├── rules/
│   │   ├── piece_rules.py          # Per-piece movement shapes, pawn rules, promotion
│   │   ├── rule_engine.py          # check_move() → OK / ILLEGAL_SHAPE / BLOCKED / FRIENDLY_FIRE / OUT_OF_BOUNDS
│   │   └── move_validator.py       # Bounds + ownership checks, then rule_engine
│   ├── realtime/
│   │   ├── motion.py               # Move duration and timing constants
│   │   └── realtime_arbiter.py     # Settles arrivals, air captures, jumps, rests
│   └── engine/
│       └── game_engine.py          # GameEngine: request_move / request_jump / advance_time
│
├── server/
│   ├── main.py                     # FastAPI app entry point (uvicorn, 127.0.0.1:8000)
│   ├── config.py                   # Tick rate, rating values, ID format, DB paths, message routing
│   ├── auth/auth.py                # login / register
│   ├── db/
│   │   ├── schema.sql              # users table
│   │   └── users_repo.py           # SQLite access, PBKDF2 password hashing
│   ├── logic/
│   │   ├── game_session.py         # GameSession tick loop + GameSessionManager
│   │   ├── matchmaking.py          # Rating-based matchmaking queue
│   │   ├── room_manager.py         # Private rooms, players and spectators
│   │   ├── rating.py               # Rating updates after a game
│   │   └── id_gen.py               # Random 6-character room/match IDs
│   ├── engine_adapter/adapter.py   # Builds a fresh shared engine per game
│   └── network/
│       ├── ws_routes.py            # /ws endpoint and message handlers
│       ├── connection_registry.py  # Room → connected sockets
│       └── room_broadcaster.py     # Sends room_state updates
│
├── bus/
│   ├── event_bus.py                # EventBus: subscribe / async publish
│   ├── events.py                   # Event dataclasses
│   ├── listeners/                  # What happens on each event
│   └── subscribers/                # Connects listeners to events at server startup
│
├── client/
│   ├── main.py                     # Graphical network client entry point
│   ├── config.py                   # Server URI, window, colors, layout constants
│   ├── game_setup.py               # Builds a local (offline) game
│   ├── network/
│   │   ├── connection.py           # ServerConnection (websockets wrapper)
│   │   ├── app_bridge.py           # Bridge between the network thread and the UI thread
│   │   ├── remote_game_engine.py   # Client copy of the game, updated from server snapshots
│   │   └── game_bridge.py          # Game-message helpers (also used by the legacy CLI)
│   ├── input/
│   │   ├── board_mapper.py         # Pixel → board square
│   │   └── controller.py           # Selection state, click / double-click handling
│   ├── ui/
│   │   ├── screen_manager.py       # Main loop for the menu screens
│   │   ├── screens/                # Login, Home, Room, Matchmaking screens
│   │   ├── widgets.py              # Button, TextInput, Label, ErrorText
│   │   ├── renderer.py             # Game board drawing
│   │   ├── sprite_manager.py       # Animation state and frame selection
│   │   ├── game_runner.py          # Runs a network game inside the board window
│   │   ├── app_ui.py               # Local hotseat entry point
│   │   ├── img.py                  # OpenCV image helper
│   │   ├── keyboard_layout.py      # Windows: switches to English keyboard while typing
│   │   └── game_snapshot/          # board.png + per-piece, per-state sprite frames
│   ├── io_options/                 # Text board reading / printing
│   ├── text_test/                  # Command-script runner (click / jump / wait / print board)
│   └── cli/                        # Legacy text-based client flow
│
├── tests/unit/                     # pytest unit tests
├── pytest.ini
└── Handoff.md                      # Detailed design notes and decision log
```

---

## Getting Started

### Requirements

- Python **3.12+** (developed on 3.13)
- Server packages: `fastapi`, `uvicorn[standard]`
- Client packages: `websockets`, `opencv-python`, `numpy`

> **Note:** `client/requirements.txt` lists only `websockets`. You also need to install `opencv-python` and `numpy` for the graphical client and the UI tests.

### Installation

```bash
cd chess-project
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r server/requirements.txt
pip install -r client/requirements.txt
pip install opencv-python numpy pytest
```

### Running the server

Run all commands from the `chess-project/` directory:

```bash
python -m server.main
```

The server listens on `ws://127.0.0.1:8000/ws`. On first start it creates the SQLite database at `server/db/chess.db` (this file is git-ignored).

### Running the client

```bash
python -m client.main
```

Start two clients (in two terminals, or on two machines after changing `SERVER_URI` in `client/config.py`) to play against each other.

### Local hotseat mode (no server)

```bash
python -m client.ui.app_ui
```

Two players share one window. The game asks for both player names, then opens the board. If you pipe a board into stdin, it is used instead of the standard position (format: `Board:` line, rows of space-separated tokens such as `wK` or `.`, then a `Commands:` line).

---

## How to Play

### Menu flow

```
Login / Register ──► Home ──► Play  ──► Matchmaking ──► Game ──► Back to Menu ──► Home
                           └► Room  ──► Create / Join ──► Wait for opponent ──► Game
```

1. **Login screen**: choose *Login* or *Register*, enter a username and password, then press *Submit* (or Enter). Registering also logs you in.
2. **Home screen**: shows your username and current rating. Choose **Play** (matchmaking) or **Room** (private room).
3. **Matchmaking**: the client joins the queue right away and shows a search timer. You can cancel at any time. If no opponent is found within 60 s, you return to the menu.
4. **Room**: *Create* gives you a 6-character room ID to share. *Join* asks for a room ID. The game starts when the second player joins.
5. **Game over**: click **Back to Menu** to return to Home with your updated rating, without logging in again.

### Board controls

| Action | Input |
|---|---|
| Select a piece | Left-click one of your pieces (it must not be moving or resting) |
| Move | Left-click the destination square after selecting a piece |
| Change selection | Left-click another of your pieces |
| Jump | Double-click a piece |
| Quit | `Esc` or `q` (in game), `Esc` (in menus), or close the window |

The board shows **White's name above** and **Black's name below**. Each player's moves are listed in the side panel on their side. A colored bar under a resting piece shows how much rest time is left.

---

## Network Protocol

All messages are JSON objects in a single envelope format:

```json
{ "type": "move", "payload": { "from": [6, 4], "to": [4, 4] }, "request_id": "a1b2..." }
```

`request_id` is optional. When a client includes it, the direct reply carries the same `request_id`. Server-initiated messages (broadcasts) have none.

### Client → Server

| Type | Payload | Reply |
|---|---|---|
| `login` | `username`, `password` | `login_result` → `success`, `message`, `rating` |
| `register` | `username`, `password` | `register_result` → `success`, `message`, `rating` |
| `menu_select` | `choice`: `"play"` \| `"room"` | `menu_ack` |
| `play` | — | `play_queued` (no `request_id`), or an error reply if not logged in |
| `cancel_play` | — | `play_cancelled` |
| `create_room` | — | `room_state` → `room_id`, `role`, `player_count`, `viewer_count` |
| `join_room` | `room_id` | `room_state` with `success`, `role` (no `request_id`), or an error reply if the room isn't found |
| `cancel_room` | `room_id` | `room_state` → `success`, `message` |
| `move` | `from: [row, col]`, `to: [row, col]` | none on success; `move_rejected` with a `reason` if illegal |
| `jump` | `pos: [row, col]` | none on success; `jump_rejected` with a `reason` if illegal |
| `echo` | any | the same payload (for debugging) |

An unknown `type` returns an `error` envelope.

### Server → Client (broadcasts)

| Type | When | Main payload fields |
|---|---|---|
| `room_state` | Someone joins or leaves your room | `room_id`, `player_count`, `viewer_count` |
| `match_found` | Matchmaking paired you | `match_id`, `opponent_username`, `opponent_rating` |
| `match_timeout` | No opponent within 60 s | — |
| `game_started` | A game begins | Full snapshot + `your_color` (`"w"`, `"b"`, or `null` for spectators) |
| `game_update` | A server tick in which anything changed | `board`, `clock`, `locked`, `pending_moves`, `resting`, `airborne`, `settled_moves`, player usernames |
| `disconnect_countdown` | Once per second after a player disconnects | `disconnected_username`, `seconds_remaining` |
| `game_over` | A king is captured or a player forfeits | `winner_color`, `winner_username`, `reason` (`king_captured` \| `disconnect`), `new_ratings` |

---

## Rating System

Ratings use fixed points (not ELO), applied once per finished game:

| Result | Change |
|---|---|
| Win | **+100** |
| Loss | **−30** |
| Each piece you captured | **+2** (for both winner and loser) |

New accounts start at **1200**. An air capture counts for the player whose piece was jumping. Draws are not possible in the current rules.

---

## Configuration

| File | Main settings |
|---|---|
| `shared/realtime/motion.py` | `DEFAULT_SPEED = 1000` ms per square, `JUMP_DURATION_MS = 1000`, `LONG_REST_MS = 4000`, `SHORT_REST_MS = 2000` |
| `shared/config.py` | Piece and color codes, message type names, `MATCH_TIMEOUT_SECONDS = 60`, `MAX_ROOM_PLAYERS = 2` |
| `server/config.py` | `TICK_MS = 100`, `DISCONNECT_RESIGN_SECONDS = 20`, rating values, `RATING_RANGE = 100`, ID format, DB path, `PBKDF2_ITERATIONS` |
| `client/config.py` | `SERVER_URI`, frame delay, colors and layout of the board window |
| `client/ui/game_snapshot/pieces_mine/<piece>/states/<state>/config.json` | Animation frame rate and looping for each sprite state |

Piece tokens are two characters: color (`w`/`b`) + type (`K`, `Q`, `R`, `B`, `N`, `P`). `.` is an empty square. Board positions are always `(row, col)`, with row 0 at the top (Black's back rank).

---

## Testing

The project has about 130 pytest unit tests in `tests/unit/`. They cover:

- **Rules and engine**: piece movement, blocking, pawn rules, promotion, legality results, move timing, real-time interactions, jumps and air captures, game over.
- **Server**: authentication, rating math, WebSocket routing.
- **Client**: board mapping, board parsing and printing, `RemoteGameEngine`, `AppBridge`, widgets, and every menu screen (using a stub bridge).

Run them from `chess-project/`:

```bash
python -m pytest
```

The tests never use real `time.sleep()`. Time moves forward explicitly with `engine.advance_time(ms)`, so they are fast and repeatable. UI tests import OpenCV, so `opencv-python` must be installed.

The board renderer and sprite animations have no automated tests and are checked by hand.

---

## Design Principles

1. **Rules never change the board.** `rule_engine.check_move` only returns a result code.
2. **The board changes only on arrival**, inside `RealTimeArbiter`, never when a move is requested.
3. **`GameEngine` contains no piece-specific rules, drawing, pixel math or networking.**
4. **`Controller` doesn't check legality.** It only tracks the selection and passes requests on.
5. **Only `shared/model/piece.py` reads the token format** (`token_color` / `token_type`).
6. **Movement rules are data-driven.** Piece validators are registered in `shared/config.py::MOVEMENT_VALIDATORS`.
7. **The server is the source of truth.** Clients send requests and apply snapshots; they never guess the board state.
8. **No duplicated legality logic** between client and server.
9. **Board size is not hard-coded.** The rules use `board.height` / `board.width` everywhere.

For the full decision log and implementation notes, see [`chess-project/Handoff.md`](chess-project/Handoff.md).

---

## Known Limitations

- Castling and en passant are not implemented.
- Spectators who join a room stay on the room waiting screen; there is no live spectator board yet.
- There are no draws or stalemates; every game has a winner.
- In local mode, illegal moves are ignored without any on-screen message.
- `opencv-python` and `numpy` are not yet listed in `client/requirements.txt`.
- The server keeps matchmaking queues, rooms and active games in memory, so they are lost on restart. Only accounts and ratings are saved.
