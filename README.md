# Kung Fu Chess

A **real-time, multiplayer chess variant** written in Python. There are no turns: both players move their pieces whenever they want. Each move takes time to complete, and a piece that has just moved must rest before it can act again. The game ends the moment a king is captured.

The project has three parts:

- **Shared game engine**: the chess rules plus the real-time logic for movement and captures. Used by both the client and the server.
- **Game server**: built with FastAPI and WebSockets. Handles accounts, ratings, matchmaking, private rooms and live games.
- **Graphical client**: built with OpenCV. Includes login, the main menu, matchmaking and rooms, and an animated game board.

---

## Table of Contents

1. [Game Rules](#game-rules)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Project Structure](#project-structure)
5. [Getting Started](#getting-started)
6. [How to Play](#how-to-play)
7. [Communication Between Client and Server](#communication-between-client-and-server)
8. [Rating System](#rating-system)
9. [Testing](#testing)

---

## Game Rules

Kung Fu Chess uses the standard chess pieces and starting position, but plays in real time.

| Concept | Behavior |
|---|---|
| **No turns** | Either player can move any of their available pieces at any moment. Many pieces can be moving at once. |
| **Move duration** | A move takes 1 second per square of distance. A diagonal step counts the same as a straight one. |
| **Moving pieces** | A piece that is on its way can't be given another order. The board changes only when it arrives. |
| **Capture on arrival** | A capture happens only when the moving piece reaches its destination. |
| **Rest** | After a move, the piece rests for 4 seconds before it can act again. A resting piece can still be captured. |
| **Jump** | A piece can jump in place for 1 second. If an enemy piece lands on that square during the jump, the jumping piece captures it. After a jump, the piece rests for 2 seconds. |
| **Promotion** | A pawn that reaches the last rank becomes a queen automatically. |
| **Game end** | There is no check or checkmate. The game ends as soon as a king is captured. A player who disconnects and doesn't return within 20 seconds loses. |

All pieces move as in regular chess. Queens, rooks and bishops can't pass through other pieces.

---

## Features

- **User accounts**: register and log in. Passwords are stored securely (hashed), and account data is kept in a SQLite database.
- **Rating**: every player starts at 1200, and the rating changes after each game.
- **Matchmaking**: automatically pairs players with similar ratings.
- **Private rooms**: create a room and share its code with a friend. Anyone who joins after the first two players can watch the game.
- **Server-run games**: the server checks every move and keeps all players' boards in sync.
- **Disconnect handling**: if a player disconnects, a countdown appears; if they don't return in time, they lose.
- **Animated board**: piece animations, smooth movement between squares, rest timers, a move history for each player, and a game-over screen.
- **Local mode**: two players on the same computer, without a server.

---

## Architecture

```
┌──────────────────────── Client (each player) ────────────────────────┐
│                                                                       │
│   Window and screens                    Network connection            │
│   ┌──────────────────────────┐          ┌──────────────────────────┐  │
│   │ Login → Home →           │◄─────────│ Receives server messages │  │
│   │ Room / Matchmaking →     │─────────►│ Sends player actions     │  │
│   │ Game board               │          └────────────┬─────────────┘  │
│   └──────────────────────────┘                       │                │
└──────────────────────────────────────────────────────┼────────────────┘
                                                       │  WebSocket (JSON)
┌───────────────────────────── Server ─────────────────┼────────────────┐
│                                                      ▼                │
│   Message routing ──► Login / Matchmaking / Rooms                     │
│                              │                                        │
│                              ▼                                        │
│                         Event bus ──► Game sessions                   │
│                                          (shared game engine)         │
│                                                                       │
│   SQLite database (users and ratings)                                 │
└───────────────────────────────────────────────────────────────────────┘
```

| Part | Folder | What it does |
|---|---|---|
| **Game engine** | `shared/` | Board, pieces, move rules, real-time movement, captures and game end. |
| **Server** | `server/` | Accounts, ratings, matchmaking, rooms, running live games. |
| **Event bus** | `bus/` | Passes events between parts of the server, such as starting a game when a room fills up. |
| **Client** | `client/` | Connects to the server, shows the screens and the board, and handles mouse and keyboard input. |

The client runs the window and the network connection on separate threads, so the screen stays smooth while it waits for messages.

---

## Project Structure

```
chess-project/
├── shared/            # Game engine used by client and server
│   ├── model/         # Board, pieces, game state, starting position
│   ├── rules/         # Legal moves for each piece
│   ├── realtime/      # Move timing, arrivals, jumps, rests
│   ├── engine/        # Handles move and jump requests
│   └── protocol.py    # Message format
│
├── server/
│   ├── main.py        # Server entry point
│   ├── auth/          # Login and registration
│   ├── db/            # SQLite database
│   ├── logic/         # Game sessions, matchmaking, rooms, rating
│   └── network/       # WebSocket connection and message handling
│
├── bus/               # Event bus, events and their handlers
│
├── client/
│   ├── main.py        # Client entry point
│   ├── network/       # Server connection
│   ├── input/         # Mouse clicks and piece selection
│   └── ui/            # Screens, buttons, board drawing, animations, images
│
└── tests/unit/        # Unit tests
```

---

## Getting Started

### Requirements

- Python 3.12 or later
- Server: `fastapi`, `uvicorn[standard]`
- Client: `websockets`, `opencv-python`, `numpy`

### Installation

```bash
cd chess-project
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -r server/requirements.txt
pip install -r client/requirements.txt
pip install opencv-python numpy pytest
```

### Running

Run all commands from the `chess-project/` folder.

**Server:**

```bash
python -m server.main
```

The server listens on `ws://127.0.0.1:8000/ws` and creates the database on its first run.

**Client** (open two to play against each other):

```bash
python -m client.main
```

**Local mode**, two players on one computer (no server needed):

```bash
python -m client.ui.app_ui
```

---

## How to Play

### Screens

```
Login / Register ──► Home ──► Play ──► Matchmaking ──► Game ──► Back to Menu ──► Home
                          └─► Room ──► Create / Join ──► Wait for opponent ──► Game
```

1. **Login**: log in, or create a new account.
2. **Home**: shows your name and rating. Choose **Play** to find an opponent automatically, or **Room** to play with a friend.
3. **Matchmaking**: searches for an opponent with a similar rating. You can cancel at any time. If nobody is found within 60 seconds, you return to the menu.
4. **Room**: **Create** a room and share its code, or **Join** with a code. The game starts when the second player joins.
5. **End of game**: click **Back to Menu** to return home and see your new rating.

### Board controls

| Action | How |
|---|---|
| Select a piece | Click one of your pieces |
| Move | Click the destination square |
| Jump | Double-click a piece |
| Quit | `Esc` or `q`, or close the window |

The side panels list each player's moves. A bar under a resting piece shows how long until it can move again.

---

## Communication Between Client and Server

The client and the server talk over a WebSocket. Every message is a JSON object with a message type and its data:

```json
{ "type": "move", "payload": { "from": [6, 4], "to": [4, 4] } }
```

**The client sends:** login and registration, a menu choice, join or leave the matchmaking queue, create, join or leave a room, and the moves and jumps of the game.

**The server sends:** login results, room updates, match found or search timed out, game start, game updates, rejected moves, a disconnect countdown, and the final result with the new ratings.

---

## Rating System

| Result | Change |
|---|---|
| Win | **+100** |
| Loss | **−30** |
| Each piece you captured | **+2** (for both players) |

New players start with a rating of **1200**.

---

## Testing

The project has about 130 unit tests. They cover the game rules, real-time movement, captures and jumps, login, rating, server message handling, and the client screens.

Run the tests from the `chess-project/` folder:

```bash
python -m pytest
```
