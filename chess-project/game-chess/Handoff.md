# Kung Fu Chess — Handoff Document

> This document is meant to let a new developer (or a fresh Claude conversation) continue this project **without** access to the previous chat history. It summarizes purpose, architecture, decisions, current status, and constraints.

---

## 1. System Purpose

**Kung Fu Chess** is a **real-time** chess variant, unlike classic turn-based chess:

- **No turns** — both players can move pieces at any moment (subject to a business constraint added later — see section 7).
- Every move has a **duration** computed from distance. During that time the piece is "in motion" and unavailable for further action.
- **Capture** only happens when a move actually arrives (Atomic Update), never while a piece is "in flight."
- There is no theoretical "check"/"checkmate" — the game ends **immediately** when a king is actually captured.
- A **"Jump"** mechanic was also added — a piece can "jump" and stay on its logical cell; if an enemy moving piece arrives at that cell while it's airborne, the jumping piece captures it (Air Capture).

The project was built through ten-plus incremental development iterations (see section 8), starting from a text-only board and ending with movement rules, real-time mechanics, captures, game-over, promotion, and jumps.

---

## 2. Architecture

The project follows strict separation of concerns, inspired by Clean Architecture. **Core principle**: every layer knows only what it must, and nothing more.

| Layer | Responsibility | Must NOT know about |
|---|---|---|
| **Model** | Raw board/piece/position/game-state | Rendering, input, time |
| **Rules** | Move legality (shape, blocking, capture) | How to draw, how to actually move pieces, time |
| **Realtime** | Logical clock, active motions, jumps, Atomic Update | Move legality (that's Rules' job) |
| **Engine** | Orchestrates the overall flow: move request → checks → trigger motion | Specific piece rules, drawing, pixel mapping |
| **Input** | Click → logical position mapping, selection state | Move legality |
| **IO Options** | Textual board read/write | Anything beyond text |
| **Text Test** | Running textual scripts (click/jump/wait/print) | Business logic |

**Key principle:** `Rule Engine` **never** moves pieces or removes enemies — it only returns a result code (`OK`, `BLOCKED`, `ILLEGAL_SHAPE`, etc.). The actual board mutation happens **only** in `RealTimeArbiter`, and only at the moment of arrival (Atomic Update) — not when the move request is sent.

---

## 3. Technologies

- **Python 3.13**
- **pytest** for unit testing (`pytest-9.1.1`)
- No external dependencies beyond stdlib at the current stage (no graphical UI yet — text only)
- I/O is done via `stdin`/`stdout` (Text IO), suited for running as `python app.py < script.kfc`

---

## 4. Project Structure

The repo root contains two sibling folders: `game-chess/` (all the code below) and `graphics/` (sprite/animation assets for the future graphical UI — see section 4a). The root also has a `Handoff · MD.docx` (an exported mirror of this same document — keep this `.md` file as the source of truth and treat the `.docx` as stale) and a leftover `__pycache__/game.cpython-*.pyc` inside `game-chess/` — a compiled trace of a pre-refactor `game.py`/`test_game.py` pair with no source files left; harmless, safe to ignore or delete.

```
game-chess/                    # note the hyphen — not "game_chess"
├── app.py                      # Main entry point (Composition Root)
├── model/
│   ├── position.py              # namedtuple Position (col, row)
│   ├── piece.py                 # token_color(), token_type() - token parsing
│   ├── board.py                 # Board: grid, get/set_piece, is_inside, height/width
│   └── game_state.py            # GameState: clock, pending_moves, locked, airborne
├── rules/
│   ├── piece_rules.py           # MOVEMENT_VALIDATORS, is_legal_move, is_sliding_piece,
│   │                             # is_legal_pawn_move/capture, pawn_start_row, pawn_promotion_row
│   ├── piece_registry.py        # PIECE_TYPES, COLORS - single source of truth for which pieces exist
│   └── rule_engine.py           # check_move() - the central legality-check function
├── realtime/
│   ├── motion.py                # calculate_duration() - Chebyshev distance, DEFAULT_SPEED, JUMP_DURATION_MS,
│   │                             # LONG_REST_MS, SHORT_REST_MS
│   └── realtime_arbiter.py      # RealTimeArbiter: start_motion, start_jump, advance_time,
│                                 # _settle_due_moves (Atomic Update + air capture), _land_due_jumps,
│                                 # _release_due_rests
├── engine/
│   └── game_engine.py           # GameEngine: request_move, request_jump, advance_time, is_over, is_locked
├── input/
│   ├── board_mapper.py          # BoardMapper: pixel_to_cell()
│   └── controller.py            # Controller: handle_click, handle_jump, selection state management
├── io_options/                  # (renamed from "io" to avoid clashing with the stdlib module)
│   ├── board_parser.py          # read_board, validate_board, VALID_TOKENS
│   └── board_printer.py         # print_board()
├── text_test/
│   ├── script_parser.py         # parse_command() - click/jump/wait/print board
│   └── script_runner.py         # run_commands() - runs a script from stdin
└── test/
    └── unit/
        ├── test_board.py
        ├── test_board_mapper.py
        ├── test_board_parser.py
        ├── test_board_printer.py
        ├── test_game_engine.py
        ├── test_game_over.py
        ├── test_motion.py
        ├── test_movement_over_time.py
        ├── test_realtime_interactions.py
        ├── test_rule_engine.py
        └── test_rules.py
```

**Correction vs. earlier drafts of this document**: `view/`, `integration/`, and `scripts/` do **not exist yet at all** — not even as empty stub folders. Anyone starting the graphical-UI iteration needs to create `game-chess/view/` from scratch.

### 4a. `graphics/` — sprite/animation assets (new, not yet wired to any code)

Added in the most recent commit (`add graphics folder`), sitting as a **sibling** of `game-chess/`, not inside it:

```
graphics/
├── board.png                    # board background image
├── pieces1/                     # first piece-skin set
│   └── <TC>/                    # e.g. QW, KB, PB... (type+color code, opposite order from board tokens)
│       └── states/
│           ├── idle/
│           │   ├── config.json  # {"physics": {...}, "graphics": {"frames_per_sec", "is_loop"}}
│           │   └── sprites/1.png..5.png
│           ├── move/
│           ├── jump/
│           ├── short_rest/
│           └── long_rest/
├── pieces2/                     # second piece-skin set (identical structure)
└── py/
    ├── img.py                   # Img: OpenCV (cv2) helper — read/resize, draw_on (alpha-blend), put_text, show
    ├── example.py                # demo: loads board.png + a piece sprite, draws it, shows the canvas
    └── requirements.txt          # opencv-python
```

Each state's `config.json` looks like:
```json
{
  "physics": {"speed_m_per_sec": 1.5, "next_state_when_finished": "long_rest"},
  "graphics": {"frames_per_sec": 12, "is_loop": true}
}
```

**Why this matters for whoever picks up the graphical-UI work:**
- This introduces a **per-piece animation state machine** (`idle → move/jump → short_rest/long_rest → idle`, chained via `next_state_when_finished`) that **does not exist anywhere in the current code**. `GameState`/`RealTimeArbiter` only track `locked`/`airborne`/`pending_moves` — there is no concept of "which visual state is this piece in" yet. That will need new state in the Model or a new layer, without leaking visuals into `RealTimeArbiter`/`GameEngine` (see section 2/11).
- `speed_m_per_sec` is a **different unit and a different number** than `DEFAULT_SPEED` (ms/square) in `realtime/motion.py` — reconcile deliberately, don't assume they're meant to be the same value.
- The demo code (`graphics/py/example.py`, `img.py`) uses **OpenCV (`cv2`)**, which is a new dependency not yet in the project (currently stdlib-only, see section 3). It is a throwaway example, not integrated — treat it as a spike, not a library to import as-is.
- Nothing in `game-chess/` currently reads from `graphics/` — nothing is wired up. This is asset/spike prep for the still-missing `view/renderer.py` + `view/image_view.py` (section 9), not a completed step.

### Files critical to understanding the architecture (read these first)
1. **`engine/game_engine.py`** — the operational heart: shows the full decision sequence for every move/jump request.
2. **`realtime/realtime_arbiter.py`** — the only place that actually mutates the board; critical for understanding Atomic Update, capture, promotion, and air-capture.
3. **`rules/rule_engine.py`** — all legality rules (including the more complex pawn logic) are centralized here.
4. **`model/game_state.py`** — all the transient logical state (locked, pending_moves, airborne) — small but central to all timing.

---

## 5. Components and Modules — Brief Description

### Model
- **`Position`**: `namedtuple("Position", ["col","row"])` — in practice most of the code still uses raw `(col, row)` tuples, not always the formal `Position`.
- **`Board`**: wraps `grid` (list of lists of strings), exposes `get_piece`, `set_piece`, `is_inside`, `height`, `width`.
- **`GameState`**: `clock` (int, ms), `pending_moves` (list of dict: from/to/token/completion_time), `locked` (set of positions), `airborne` (dict: pos → completion_time), `resting` (dict: pos → completion_time; new cooldown mechanic — see Realtime section below and section 7).
- **`piece.py`**: `token_color(token)`, `token_type(token)` — parses the `"wR"`/`"bK"`/`"."` format.

### Rules
- **`piece_rules.py`**: pure "movement shape" logic (dx,dy only, no board access). Contains:
  - `MOVEMENT_VALIDATORS` dict for the regular pieces (K/Q/R/B/N).
  - `is_legal_pawn_move(dx,dy,color,from_row,board_height)` and `is_legal_pawn_capture(dx,dy,color)` — pawns are handled separately from the generic path because they have two different patterns (move/capture) and depend on color and position.
  - `pawn_start_row(color, board_height)` = `height-2` for white, `1` for black.
  - `pawn_promotion_row(color, board_height)` = `0` for white, `height-1` for black.
  - `SLIDING_PIECES = {"Q","R","B"}` and `is_sliding_piece()`.
- **`piece_registry.py`**: `PIECE_TYPES`, `COLORS` — created to centralize "which pieces exist" in one place (groundwork for future support of custom pieces, see section 10).
- **`rule_engine.py`**: `check_move(board, piece_type, piece_color, from_pos, to_pos)` returns only a result code — `OK`/`OUT_OF_BOUNDS`/`ILLEGAL_SHAPE`/`BLOCKED`/`FRIENDLY_FIRE`. **Does not** mutate the board. Has a dedicated path for pawns (`_check_pawn_move`) that also checks path-blocking for the double move.

### Realtime
- **`motion.py`**: `calculate_duration(from_pos, to_pos, speed=DEFAULT_SPEED)` — **Chebyshev distance** (`max(|dx|,|dy|)`), **not** Euclidean! `DEFAULT_SPEED = 1000` (ms per square). `JUMP_DURATION_MS = 1000`. **New**: `LONG_REST_MS = 1000` (cooldown after a regular move settles) and `SHORT_REST_MS = 500` (cooldown after a jump lands safely) — see below.
- **`realtime_arbiter.py`**: `RealTimeArbiter` holds references to `board` and `game_state`.
  - `start_motion(from_pos, to_pos, token, completion_time)` — registers a move in `pending_moves`, adds to `locked`.
  - `start_jump(pos)` — registers `airborne[pos] = clock + JUMP_DURATION_MS`.
  - `advance_time(ms)` — advances `clock`, calls `_settle_due_moves()`, then `_land_due_jumps()`, then `_release_due_rests()` (in that order!).
  - `_settle_due_moves()` — **the most important function in the project**. For each move whose time has come: first checks for **air capture** (if the destination is in `airborne`, the arriving enemy is captured and the jumping piece stays put), otherwise performs the regular Atomic Update (including pawn promotion check) **and now also** sets `resting[move["to"]] = clock + LONG_REST_MS` — the landing square enters a cooldown before it can be selected/moved again. Returns the list of settled moves, each including `captured_token`.
  - `_land_due_jumps()` — clears pieces that finished jumping without being captured; **now also** sets `resting[pos] = clock + SHORT_REST_MS` for a piece that lands safely (jump cooldown is shorter than a regular-move cooldown).
  - `_release_due_rests()` — **new**. Clears `resting` entries whose completion time has passed, mirroring `_land_due_jumps`'s pattern for `airborne`.

### Engine
- **`GameEngine`**: `request_move(from_pos, to_pos)` checks in order: `is_over?` → `game_state.locked` **not empty** (a **global** lock! see section 7) → `rule_engine.check_move()` → if `OK`, triggers `arbiter.start_motion`. `request_jump(pos)` checks: `is_over?` → piece not `locked` → piece not already `airborne` → a piece exists on the cell → triggers `arbiter.start_jump`. `advance_time(ms)` calls `arbiter.advance_time`, and for each settled move checks if `captured_token` is a king (`token_type == "K"`) → if so, `is_over = True`. `is_locked(pos)` — a query used by the Controller; **now returns `True` if `pos` is in `locked` OR in `resting`**, so a piece that just arrived (or just landed a jump) reads as unavailable during its cooldown even though it's not in `game_state.locked`.

### Input
- **`BoardMapper`**: `pixel_to_cell(x,y)` based on `square_size=100`, returns `None` if outside the board.
- **`Controller`**: `handle_click(x,y)` — manages the `selected` state. Checks `is_locked` **at the start** of the function (before selection logic) to ignore clicks on occupied cells. `handle_jump(x,y)` — calls `game_engine.request_jump` directly.

### IO Options
- **`board_parser.py`**: `read_board()` reads lines from stdin until `"Commands:"`. `validate_board()` checks squareness and valid tokens (`VALID_TOKENS`, currently built from `piece_registry`).
- **`board_printer.py`**: `print_board(board)` — simple printing, `" ".join(row)` per row.

### Text Test
- **`script_parser.py`**: `parse_command(line)` recognizes `click x y` / `jump x y` / `wait ms` / `print board`.
- **`script_runner.py`**: `run_commands(controller, game_engine, board)` — a loop that reads lines from stdin and triggers the matching action. **`wait` only advances the logical clock — never a real `time.sleep()`.**

---

## 6. Data Flow (End-to-End)

**Regular move (click → click):**
1. User/script sends `click x1 y1` → `Controller.handle_click` → `BoardMapper.pixel_to_cell` → if there's a piece on the cell and it's not locked → `selected = {pos, color}`.
2. Second `click x2 y2` → if same color as the selected piece, replace the selection. Otherwise → `GameEngine.request_move(from_pos, to_pos)`.
3. `GameEngine` checks `is_over`, checks `game_state.locked` (**global**, not just for this piece), calls `rule_engine.check_move`.
4. If `OK` → `arbiter.start_motion` → registered in `pending_moves`, `locked.add(from_pos)`.
5. **The logical board has NOT changed yet!** — only when a sufficient `wait ms` arrives, `advance_time` advances `clock`, and `_settle_due_moves` performs the actual Atomic Update (including checking promotion / air capture / king capture).
6. **New**: the moment a regular move settles, the destination cell also enters a **rest/cooldown** (`resting[to] = clock + LONG_REST_MS`) — during this window `GameEngine.is_locked(to)` returns `True`, so the piece cannot be selected or moved again even though `game_state.locked` no longer contains it. The cooldown clears itself the next time `advance_time` runs past its completion time (`_release_due_rests`).
7. `print board` at any point prints the current actual state of `board.grid` (not including "in-flight" moves).

**Jump:**
1. `jump x y` → `Controller.handle_jump` → `GameEngine.request_jump(pos)` → if valid → `arbiter.start_jump(pos)` → `airborne[pos] = clock + 1000`.
2. If, while the piece is "airborne," an enemy move arrives whose destination is that cell — in `_settle_due_moves`, `move["to"] in airborne` is checked **before** the regular Atomic Update → if true, the arriving enemy is removed from its origin, the jumping piece stays put.
3. If no enemy arrived by the end of the jump — `_land_due_jumps` simply removes the entry from `airborne`; the board doesn't change (the piece was logically there the whole time). **New**: landing safely also starts a (shorter) rest — `resting[pos] = clock + SHORT_REST_MS`.

---

## 7. Important Architectural/Business Decisions Made

1. **`io` → `io_options`**: the folder was renamed because `io` clashes with a Python stdlib module.
2. **`app.py` sits at the project root**, not inside `text_test/` — it's the general entry point, not a test-only tool.
3. **`is_locked` as a query in Controller**: moved from a check that originally lived in the monolithic legacy code, into `GameEngine.is_locked(pos)`, queried by `Controller` at the start of `handle_click` — so clicks on "busy" cells are fully ignored without disrupting selection.
4. **Global Lock — a significant decision that deviates from the original spec!** Based on test cases provided (input/expected output), it turned out the system does **not** support simultaneous motion of more than one piece on the whole board — `GameEngine.request_move` checks `if self.game_state.locked:` (non-empty at all, not just whether the specific `from_pos` is locked). In other words: **only one active move on the entire board at any given moment**, regardless of piece/color. This deviates from the original description of "both players move simultaneously," and should be confirmed against the spec/grader as to whether this is final or an interim stage.
5. **Move duration = Chebyshev, not Euclidean**: fixed after a failing test (a queen moving diagonally) revealed that `calculate_duration` needed `max(|dx|,|dy|)` instead of `sqrt(dx²+dy²)` — matching real chess rules (diagonal movement costs the same as straight movement).
6. **`DEFAULT_SPEED = 1000`** (ms per square) — changed from the original `200`, after external tests (input/expected output) revealed this was the expected value.
7. **Pawn start row is board-height-dependent, not fixed**: `pawn_start_row(color, height) = height-2` for white, `1` for black. **Fixed twice** — it was originally `height-1`/`0` (wrong — that's the back-rank row, not the pawn row), then corrected to `height-2`/`1`.
8. **Promotion** (`pawn_promotion_row`): `0` for white, `height-1` for black — correct from the start, this is the actual edge row.
9. **Air capture takes priority over regular settlement**: in `_settle_due_moves`, if `move["to"]` is in `airborne`, a special capture occurs (the attacking piece is removed, the jumping piece stays) **before** the regular Atomic Update check. This ordering is **critical** and was deliberate — see the design note below.
10. **Jumping is NOT checked against the global lock (`locked`)** — a piece can jump even while another piece is moving elsewhere, because `request_jump` only checks whether *that specific piece* is locked/already-airborne, not the global state. **This decision was not finally confirmed** — it needs to be verified whether jumping should also be blocked by the global lock.
11. **Pawns are always handled via a separate path** in `rule_engine.check_move` (`if piece_type=="P": return _check_pawn_move(...)`) rather than through the generic `MOVEMENT_VALIDATORS` — because they have asymmetric rules (color-dependence, move≠capture) that don't fit the simple dx/dy model used by the other pieces.
12. **New — Rest/cooldown after arrival, replacing the earlier "no cooldown" rule**: a previous iteration explicitly established (and tested, via a now-deleted test named `test_piece_can_move_again_immediately_after_arrival_no_cooldown`) that a piece could be redirected the instant it arrived. That has been **reversed**: `GameState.resting` (dict: pos → completion_time) now tracks a post-arrival cooldown, checked by `GameEngine.is_locked`. Two different durations apply: `LONG_REST_MS = 1000` after a regular move settles (`_settle_due_moves`), and the shorter `SHORT_REST_MS = 500` after a jump lands safely (`_land_due_jumps`). Resting is per-position, not global — it does not block other pieces elsewhere on the board (unlike the global `locked` set, decision #4).

---

## 8. What Has Already Been Completed

Based on the 11 iterations done so far:

1. ✅ Text-only board, read/print, basic validation.
2. ✅ Clean Model (`Board`, `GameState`, `piece.py`).
3. ✅ Clicks (`BoardMapper`, `Controller`) with Selection/Deselection management.
4. ✅ First movement rule (Rook), then all the other regular pieces (K/Q/B/N).
5. ✅ Full command pipeline: `Controller → GameEngine → RuleEngine`.
6. ✅ Real-time: `RealTimeArbiter`, Atomic Update, logical `wait` (never real `sleep`).
7. ✅ Captures (including `FRIENDLY_FIRE`/`BLOCKED`) and game-over on king capture (`is_over`, further moves afterward are ignored).
8. ✅ Full pawn rules: single/double move, diagonal capture, path-blocking check, promotion to queen on reaching the last row.
9. ✅ Global lock — only one move active on the whole board at a time (section 7.4).
10. ✅ Advanced integration tests: enemy collision, invalid premoves, landing on a friendly piece, conflicts.
11. ✅ Jump mechanic and air capture — including full wiring in `Controller`, `script_parser`, `script_runner`.
12. ✅ Rest/cooldown after arrival (`GameState.resting`, section 7 #12) — a regular move's destination and a safely-landed jump's cell are now unavailable for a further beat (`LONG_REST_MS`/`SHORT_REST_MS`) via `GameEngine.is_locked`.

Current test coverage: 64 unit tests passing (`pytest`), spread across all layers (except `view/`).

---

## 9. What Is Still Missing

- **Actual graphical UI** (`view/renderer.py`, `view/image_view.py`) — this is step 10 of the original 10 steps, and neither the `view/` folder nor any code for it exists yet. What **does** exist is a fresh, unwired asset library at `graphics/` (sprites, board image, an OpenCV spike) — see section 4a. Building `view/` means designing how those animation states (idle/move/jump/short_rest/long_rest) map onto the existing real-time model (`pending_moves`/`locked`/`airborne`), not starting from nothing.
- **`.kfc` script files** under `scripts/` — not actually written during the conversation (mentioned in the structure but not created); the folder itself doesn't exist either.
- **`integration/`** — no folder, no comprehensive end-to-end integration tests exist (only unit tests exist, even if some are "lightly integration-style").
- **En Passant** — not implemented (not required by any iteration so far).
- **Castling** — not implemented.
- **Support for non-textual/binary board representation** — discussed as a future option (see section 10) but not implemented.
- **Support for user-defined custom games (custom piece rules)** — discussed but not implemented (see section 10).
- **More detailed error reporting in text mode** — currently `Controller`/`GameEngine` simply "stay silent" (`return`) when a move is illegal, with no error message to the user. A feedback channel may be needed in the future.

---

## 10. TODO List (explicit and implied from the conversation)

- [ ] Implement `view/renderer.py` + `view/image_view.py` with a graphical UI (step 10 of the spec), building on the sprite/animation assets already staged in `graphics/` (section 4a).
- [ ] Decide how per-piece animation state (idle/move/jump/short_rest/long_rest, driven by `graphics/**/config.json`) is modeled — new Model state vs. a new layer — without letting `RealTimeArbiter`/`GameEngine` become visual-aware.
- [ ] Reconcile `speed_m_per_sec` (in the `graphics/` configs) against `DEFAULT_SPEED`/`calculate_duration` (ms/square, Chebyshev) in `realtime/motion.py` — decide whether/how they map to each other.
- [ ] Decide whether OpenCV (`cv2`, used by the `graphics/py/` spike) becomes an actual project dependency, or gets replaced.
- [ ] Actually write `.kfc` files under `scripts/` (board_parsing, click_to_move, invalid_moves, capture, game_over).
- [ ] Decide and document: should jumping (`request_jump`) also be checked against the global lock (`game_state.locked`)?
- [ ] Finally confirm against the grader/spec: is the "global lock — only one move on the board" rule permanent, or an interim stage that will later be replaced with full concurrency (per-piece lock only)?
- [ ] When adding custom piece types (future) — avoid adding more hardcoded `if piece_type == "X"` branches; instead build a Data-Driven Registry (see section 11).
- [ ] When moving to a binary representation (future) — make sure `token_color`/`token_type` remain the sole transition point between the raw format and the rest of the system (see section 11).
- [ ] Consider adding a feedback/error channel to `Controller`/`GameEngine` instead of full silence on illegal moves.
- [ ] Check test coverage for `view/`, `integration/`, En Passant, Castling — currently none exists at all.

---

## 11. Constraints and Principles That Must Not Be Violated

1. **`Rule Engine` never moves pieces or removes enemies** — it only returns a result code (a string constant).
2. **The logical board only changes inside `RealTimeArbiter._settle_due_moves`** (Atomic Update), never at the moment a request is sent (`request_move`/`request_jump`).
3. **`GameEngine` contains no piece-specific rules, no drawing, no pixel mapping.**
4. **`Controller` does not check move legality** — it only manages selection/deselection state and forwards requests to `GameEngine`.
5. **Tests never use real `time.sleep()` / `sleep()`** — always `engine.advance_time(ms)`, which advances the logical clock immediately.
6. **No direct coupling to the token format (`"wR"`) outside `model/piece.py`** — the rest of the system must go through `token_color`/`token_type`, never access `token[0]`/`token[1]` directly. This is critical groundwork for a future move to a binary representation.
7. **Piece-type definitions (`PIECE_TYPES`) and movement rules (`MOVEMENT_VALIDATORS`) should not be "burned in" to `rule_engine`/`game_engine` logic** — centralizing them in `piece_registry.py`/`piece_rules.py` is meant to prepare the ground for future support of custom pieces ("Kung Fu Chess, Shlomi's Edition"). When that requirement arrives, the needed change is from a hardcoded Strategy in code to a Data-Driven Registry loaded at runtime — without changing the `rule_engine`/`game_engine` interfaces themselves.
8. **Move speed = Chebyshev distance** (`max(|dx|,|dy|)`), **not** Euclidean — this mistake was already fixed once; it must not be repeated.

---

## 12. Working Assumptions

- The board can be of any size (not just 8×8) — code must reference `board.height`/`board.width` dynamically, never hardcode row numbers (this was a mistake fixed twice with `pawn_start_row`).
- `square_size = 100` pixels is fixed (in `BoardMapper`) — independent of board size.
- A piece token is always a string in the format `"{color}{type}"` (e.g. `"wR"`), or `"."` for an empty cell — currently hardcoded, but care should be taken not to "lock in" this assumption beyond `model/piece.py`.
- `DEFAULT_SPEED=1000`, `JUMP_DURATION_MS=1000` — currently global constants, overridable via a parameter but sharing the same default.
- Input always arrives via `stdin` in the format: `Board:` → board rows → `Commands:` → command lines (`click x y` / `jump x y` / `wait ms` / `print board`).

---

## 13. Additional Important Information for Continuing the Work

- **Project workflow**: every new iteration comes with a short textual requirement (e.g. "This iteration adds pawn movement rules..."), followed by a focused change in only the relevant files + new tests. It's important to **explicitly mark which files/lines changed** (`ADDED`/`CHANGED`/`REMOVED` in comments) to preserve transparency.
- **The bug-discovery process** in this project relied mainly on **external tests** (Input/Expected Output supplied as a "grader") rather than only on internal unit tests — when there's a conflict between the internal assumption (a unit test) and the expected external result, the external spec should be prioritized and the unit tests updated accordingly (this already happened 2-3 times with `pawn_start_row` and `DEFAULT_SPEED`).
- When a test failure report comes in, it's always worth first asking: **is this a bug in production code, or is the test itself already outdated** relative to a recent change? (e.g., changing `pawn_start_row` caused old tests to "correctly fail" because they checked against the old definition).
- Keep two future extensions in mind: binary board representation, and custom user-defined pieces — every new change in `piece.py`/`piece_rules.py`/`rule_engine.py` should be evaluated against the question "does this make either of these extensions harder?".
- **No formal, consolidated commit messages exist yet** — only a few individual examples were given along the way (e.g. `feat(engine): enforce single active motion across the board`, `test(rule_engine): fix pawn double-move start row after height-2 fix`). It's recommended to continue with the Conventional Commits convention.