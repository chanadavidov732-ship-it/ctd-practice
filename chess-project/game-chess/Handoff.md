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
- No external dependencies declared in any manifest — but as of the graphical UI work (see below), `opencv-python` (`cv2`) and `numpy` are actually imported and required to run `ui/app-ui.py`. Still not formalized in a `requirements.txt`/`pyproject.toml` — open item, see section 10.
- I/O is done via `stdin`/`stdout` (Text IO), suited for running as `python app.py < script.kfc`
- **A graphical UI now exists** (`ui/renderer.py`, `ui/sprite_manager.py`, `ui/app-ui.py`) — OpenCV/`Img`-based, built on top of everything in this document without changing move legality, capture, or timing rules. This document (`Handoff.md`) still covers only the logic layers (`model`/`rules`/`realtime`/`engine`/`input`/`io_options`/`text_test`); the graphical layer is documented separately and in full in **`ui/UI_DESIGN.md`** — read that file for anything UI-related. A few small, purely additive changes the UI work made to the logic layers are called out inline below (search this document for "UI work").

---

## 4. Project Structure

The repo root previously also had a sibling `graphics/` folder (sprite/animation assets for the future graphical UI); it has since been **removed** — its contents now live inside `game-chess/ui/` (see section 4a). The root also has a `Handoff · MD.docx` (an exported mirror of this same document — keep this `.md` file as the source of truth and treat the `.docx` as stale) and a leftover `__pycache__/game.cpython-*.pyc` inside `game-chess/` — a compiled trace of a pre-refactor `game.py`/`test_game.py` pair with no source files left; harmless, safe to ignore or delete.

```
game-chess/                    # note the hyphen — not "game_chess"
├── app.py                      # [UI work] TEXT-MODE entry point only — reads board, calls game_setup.build_game, runs run_commands. No import of ui/ at all.
├── game_setup.py                # [UI work] shared composition-root factory: build_game(grid) -> (board, game_state, arbiter, game_engine, board_mapper, controller). Used by both app.py and ui/app-ui.py so neither duplicates the wiring.
├── model/
│   ├── position.py              # namedtuple Position (col, row)
│   ├── piece.py                 # token_color(), token_type() - token parsing
│   ├── board.py                 # Board: grid, get/set_piece, is_inside, height/width
│   └── game_state.py            # GameState: clock, pending_moves, locked, airborne, resting, [UI work] resting_duration
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
├── ui/                          # moved/renamed from the old root-level graphics/ folder - see section 4a
│   ├── img.py                    # Img: OpenCV (cv2) + numpy helper - read/resize, draw_on (alpha-blend), put_text, show - never modified by the UI work
│   ├── renderer.py               # [UI work] fully implemented - see ui/UI_DESIGN.md (was an empty stub)
│   ├── sprite_manager.py         # [UI work] fully implemented - see ui/UI_DESIGN.md (was an empty stub)
│   ├── app-ui.py                 # [UI work] the graphical entry point - `python ui/app-ui.py`, see ui/UI_DESIGN.md §8
│   └── game_snapshot/            # sprite/animation assets (moved from graphics/, see section 4a for what changed)
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

### 4a. `game-chess/ui/` — sprite/animation assets + graphical UI (moved in from the old root-level `graphics/`)

**[UI work — supersedes most of this section]** Everything below describing `renderer.py`/`sprite_manager.py` as empty and "nothing wired up" is now **stale** — the graphical UI was fully built afterward. It is documented in full, including every deviation from the original plan, in **`ui/UI_DESIGN.md`** — read that file, not the paragraphs below, for how the renderer/sprite manager actually work today. The asset-migration history below (what changed vs. the old `graphics/` folder) is still accurate and kept for context.

The root-level `graphics/` sibling folder described in earlier drafts of this document is **gone** — it was moved inside `game-chess/` and renamed to `ui/`. Along with the move, the asset set was trimmed and code stubs were added:

```
game-chess/ui/
├── img.py                       # Img: OpenCV (cv2) + numpy helper — read/resize, draw_on (alpha-blend), put_text, show
│                                 # (evolved from the old graphics/py/img.py demo; now also imports numpy)
├── renderer.py                  # currently an EMPTY file — not yet implemented
├── sprite_manager.py            # currently an EMPTY file — not yet implemented
└── game_snapshot/                # sprite/animation assets (moved from graphics/)
    ├── board.png                 # board background image
    └── pieces_mine/               # the only piece-skin set kept — the old graphics/pieces2/ set was dropped
        └── <color><type>/         # e.g. wK, bQ... now color+type order, matching board tokens ("wR"),
            │                      # unlike the old graphics/pieces1/<type><color>/ (e.g. QW, KB) — order was flipped
            └── states/
                ├── idle/
                │   ├── config.json   # {"physics": {...}, "graphics": {"frames_per_sec", "is_loop"}}
                │   └── sprites/1.png..5.png
                ├── move/
                ├── jump/
                ├── short_rest/
                └── long_rest/
```

Each state's `config.json` still looks like:
```json
{
  "physics": {"speed_m_per_sec": 1.5, "next_state_when_finished": "long_rest"},
  "graphics": {"frames_per_sec": 12, "is_loop": true}
}
```

**What's changed vs. the old `graphics/` folder** (still accurate, historical):
- The assets now live **inside** `game-chess/` (under `ui/game_snapshot/`) instead of as a root sibling — no more crossing the package boundary to reach them.
- Only one piece-skin set remains (`pieces_mine/`, the old `pieces1/`); the old `pieces2/` set was removed. The per-piece folder naming was also flipped from `<type><color>` (e.g. `QW`) to `<color><type>` (e.g. `wQ`), now matching the board token format used everywhere else (section 12) — don't assume the old naming from earlier drafts of this doc.
- `speed_m_per_sec` (in the `config.json` files) is still a **different unit and a different number** than `DEFAULT_SPEED` (ms/square) in `realtime/motion.py`, and **still unreconciled** — `ui/renderer.py` never ended up needing it (animation frame timing uses `frames_per_sec` instead), so this was never revisited. Still an open item, see section 10.

**[UI work — no longer true, see `ui/UI_DESIGN.md` for the current reality]** The following were true when this section was first written and are **not true anymore**: `renderer.py`/`sprite_manager.py` being empty placeholders; OpenCV/`numpy` not being required to run anything; nothing in `game-chess/` reading from `ui/`; there being no concept of "which visual state a piece is in." All of that now exists — `SpriteManager.determine_state(pos, game_state)` maps `game_state.locked`/`airborne`/`resting` (no new `GameState` field was needed for this) to one of `idle`/`move`/`jump`/`long_rest`/`short_rest`, entirely inside the UI layer.

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
- **`GameState`**: `clock` (int, ms), `pending_moves` (list of dict: from/to/token/completion_time/**duration** — see below), `locked` (set of positions), `airborne` (dict: pos → completion_time), `resting` (dict: pos → completion_time; cooldown mechanic — see Realtime section below and section 7), **`resting_duration`** (dict: pos → original total ms, i.e. `LONG_REST_MS` or `SHORT_REST_MS` — **[UI work]** added so the UI can compute an exact remaining-time fraction without guessing; see section 7 decision #13).
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
  - `start_motion(from_pos, to_pos, token, completion_time, duration)` — registers a move in `pending_moves` (**[UI work]** `duration` is a new parameter, stored on the entry alongside `completion_time`; the caller, `GameEngine.request_move`, already computed it — this just exposes it instead of only implicitly encoding it in `completion_time`, so the UI can derive an animation progress fraction without recomputing `calculate_duration` itself), adds to `locked`.
  - `start_jump(pos)` — registers `airborne[pos] = clock + JUMP_DURATION_MS`.
  - `advance_time(ms)` — advances `clock`, calls `_settle_due_moves()`, then `_land_due_jumps()`, then `_release_due_rests()` (in that order!).
  - `_settle_due_moves()` — **the most important function in the project**. For each move whose time has come: first checks for **air capture** (if the destination is in `airborne`, the arriving enemy is captured and the jumping piece stays put), otherwise performs the regular Atomic Update (including pawn promotion check) and sets `resting[move["to"]] = clock + LONG_REST_MS` (plus, **[UI work]**, `resting_duration[move["to"]] = LONG_REST_MS`) — the landing square enters a cooldown before it can be selected/moved again. Returns the list of settled moves, each including `captured_token`.
  - `_land_due_jumps()` — clears pieces that finished jumping without being captured; sets `resting[pos] = clock + SHORT_REST_MS` for a piece that lands safely (plus, **[UI work]**, `resting_duration[pos] = SHORT_REST_MS`) — jump cooldown is shorter than a regular-move cooldown.
  - `_release_due_rests()` — clears `resting` entries whose completion time has passed, mirroring `_land_due_jumps`'s pattern for `airborne` (plus, **[UI work]**, clears the matching `resting_duration` entry).

### Engine
- **`GameEngine`**: `request_move(from_pos, to_pos)` checks in order: `is_over?` → `is_locked(from_pos)` (**per-piece only — the global lock was removed, see section 7, decision #4; note this checks only the *mover*, `from_pos` — the target `to_pos` is never checked here, which is exactly why capturing a locked/resting piece has always been legal, see decision #13**) → `rule_engine.check_move()` → if `OK`, triggers `arbiter.start_motion`. `request_jump(pos)` checks: `is_over?` → piece not `locked` → piece not already `airborne` → a piece exists on the cell → triggers `arbiter.start_jump`. `advance_time(ms)` calls `arbiter.advance_time`, and for each settled move checks if `captured_token` is a king (`token_type == "K"`) → if so, `is_over = True`; **[UI work]** now ends with `return settled` (previously computed but discarded — the UI's move-history feature reads this).  `is_locked(pos)` — a query used by the Controller **and now also by `request_move` itself**; returns `True` if `pos` is in `locked` OR in `resting`, so a piece that just arrived (or just landed a jump) reads as unavailable during its cooldown even though it's not in `game_state.locked`.

### Input
- **`BoardMapper`**: `pixel_to_cell(x,y)` based on `square_size=100`, returns `None` if outside the board.
- **`Controller`**: `handle_click(x,y)` — manages the `selected` state. `handle_jump(x,y)` — calls `game_engine.request_jump` directly. **[UI work — fixed, see section 7 decision #13]** `is_locked` is checked only where selection actually happens — picking a piece up (`self.selected is None`) or switching selection to another friendly piece — **not** on the move/capture-destination branch. Previously `is_locked(pos)` was checked unconditionally at the top of `handle_click`, which incorrectly also blocked clicking a locked/resting *enemy* piece as a capture target (even though `GameEngine.request_move` was always willing to allow it, since it only ever checks the mover's lock state).

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
2. Second `click x2 y2` → if same color as the selected piece (and not locked/resting), replace the selection. Otherwise → `GameEngine.request_move(from_pos, to_pos)` — **note**: this branch does *not* check whether the *destination* cell is locked/resting (see section 7 decision #13) — a locked/resting enemy piece is a perfectly legal capture target; only the *mover*'s own lock state (step 3) matters.
3. `GameEngine` checks `is_over`, checks `is_locked(from_pos)` (**per-piece only** — the earlier global lock was removed, see section 7, decision #4), calls `rule_engine.check_move`.
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
2. **`app.py` sits at the project root**, not inside `text_test/` — it's the general (text-mode) entry point, not a test-only tool. **[UI work]** Once the graphical UI existed, `app.py` briefly *was* the GUI entry point (iterations 1–12); it was then split back out — `app.py` returned to being the text-mode entry point exactly as described here, and the GUI moved to its own `ui/app-ui.py`, with the shared composition wiring factored into `game_setup.py::build_game(grid)` so neither entry point duplicates it. See `ui/UI_DESIGN.md` §8.
3. **`is_locked` as a query in Controller**: moved from a check that originally lived in the monolithic legacy code, into `GameEngine.is_locked(pos)`, queried by `Controller`. **[UI work — refined, see decision #13]** Originally checked unconditionally at the very start of `handle_click`, before selection vs. move/capture was even distinguished; now checked only where it actually applies — picking up a piece, or switching to another friendly one — never on the move/capture-destination branch.
4. **Global Lock — REMOVED.** A previous iteration had `GameEngine.request_move` checking `if self.game_state.locked:` (non-empty at all, not just whether the specific `from_pos` is locked), meaning only one active move could be in flight on the entire board at any given moment, regardless of piece/color. This deviated from the original description of "both players move simultaneously" and was left as an open question (see the former TODO in section 10). **It has now been reversed**: `request_move` checks only `self.is_locked(from_pos)` — i.e. whether *this specific square* is `locked` (mid-motion) or `resting` (post-arrival cooldown). Any number of pieces, on either side, can now be in motion at the same time; the only thing that blocks a piece is its own lock/rest state. `GameState.locked`/`GameState.resting` and `RealTimeArbiter` were not changed — they were already per-position; only the gate in `GameEngine.request_move` was removed. Covered by `test_second_piece_can_move_while_another_is_in_motion` in `test/unit/test_game_engine.py` (renamed and inverted from the old `test_second_piece_cannot_move_while_another_is_in_motion`, which asserted the opposite behavior).
5. **Move duration = Chebyshev, not Euclidean**: fixed after a failing test (a queen moving diagonally) revealed that `calculate_duration` needed `max(|dx|,|dy|)` instead of `sqrt(dx²+dy²)` — matching real chess rules (diagonal movement costs the same as straight movement).
6. **`DEFAULT_SPEED = 1000`** (ms per square) — changed from the original `200`, after external tests (input/expected output) revealed this was the expected value.
7. **Pawn start row is board-height-dependent, not fixed**: `pawn_start_row(color, height) = height-2` for white, `1` for black. **Fixed twice** — it was originally `height-1`/`0` (wrong — that's the back-rank row, not the pawn row), then corrected to `height-2`/`1`.
8. **Promotion** (`pawn_promotion_row`): `0` for white, `height-1` for black — correct from the start, this is the actual edge row.
9. **Air capture takes priority over regular settlement**: in `_settle_due_moves`, if `move["to"]` is in `airborne`, a special capture occurs (the attacking piece is removed, the jumping piece stays) **before** the regular Atomic Update check. This ordering is **critical** and was deliberate — see the design note below.
10. **Jumping was never checked against the (now-removed) global lock** — `request_jump` only checks whether *that specific piece* is locked/rested/already-airborne, not the global state, so this was already per-piece before decision #4 was reversed. **Resolved**: `request_jump` now calls `self.is_locked(pos)` (the same helper `request_move` uses) instead of checking `pos in self.game_state.locked` directly, so a `resting` piece can no longer jump either. Covered by `test_resting_piece_cannot_jump` in `test/unit/test_game_engine.py`.
11. **Pawns are always handled via a separate path** in `rule_engine.check_move` (`if piece_type=="P": return _check_pawn_move(...)`) rather than through the generic `MOVEMENT_VALIDATORS` — because they have asymmetric rules (color-dependence, move≠capture) that don't fit the simple dx/dy model used by the other pieces.
12. **New — Rest/cooldown after arrival, replacing the earlier "no cooldown" rule**: a previous iteration explicitly established (and tested, via a now-deleted test named `test_piece_can_move_again_immediately_after_arrival_no_cooldown`) that a piece could be redirected the instant it arrived. That has been **reversed**: `GameState.resting` (dict: pos → completion_time) now tracks a post-arrival cooldown, checked by `GameEngine.is_locked`. Two different durations apply: `LONG_REST_MS = 1000` after a regular move settles (`_settle_due_moves`), and the shorter `SHORT_REST_MS = 500` after a jump lands safely (`_land_due_jumps`). Resting is per-position, not global — it does not block other pieces elsewhere on the board (matching `locked`, which itself became purely per-position once the global lock was removed — decision #4).
13. **[UI work] A locked/resting piece can always be captured — only picking one up was ever meant to be blocked.** Confirmed directly against `GameEngine`/`RealTimeArbiter` (bypassing `Controller` entirely): `request_move` only ever checks `is_locked(from_pos)` — the *mover* — never `to_pos`; `rule_engine.check_move` doesn't look at lock/rest state at all; `_settle_due_moves` just captures whatever `board.get_piece(to)` currently holds. This was true from the very first iteration that introduced `resting`/`locked`. What was actually broken was reachability through the UI: `Controller.handle_click` (see decision #3) blocked *any* click on a locked/resting cell, including a capture click aimed at the enemy's locked/resting piece, before `request_move` was ever called. Fixed by scoping the `is_locked` check to the two selection branches only (see decision #3) — no change to `rule_engine.py`, `game_engine.py`, or `realtime_arbiter.py` was needed or made.
14. **[UI work] Small additive exposures added to logic-layer code to support the UI, none changing existing behavior**: `start_motion(..., duration)` — the already-computed `duration` is now passed through and stored on the `pending_moves` entry instead of only being implicitly encoded in `completion_time`; `GameState.resting_duration` — a new dict recording which of `LONG_REST_MS`/`SHORT_REST_MS` a given `resting` entry actually used, populated/cleared in lockstep with `resting` itself; `GameEngine.advance_time` now `return settled` instead of discarding it. All three exist purely so the UI (`ui/UI_DESIGN.md` §11a) can read data the engine already computes, without recomputing any of it or duplicating business logic in the UI layer. Confirmed via the full existing test suite passing unchanged after each.

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
9. ~~Global lock — only one move active on the whole board at a time (section 7.4).~~ **Removed** — see item 13 below and section 7 #4.
10. ✅ Advanced integration tests: enemy collision, invalid premoves, landing on a friendly piece, conflicts.
11. ✅ Jump mechanic and air capture — including full wiring in `Controller`, `script_parser`, `script_runner`.
12. ✅ Rest/cooldown after arrival (`GameState.resting`, section 7 #12) — a regular move's destination and a safely-landed jump's cell are now unavailable for a further beat (`LONG_REST_MS`/`SHORT_REST_MS`) via `GameEngine.is_locked`.
13. ✅ **Global lock removed** — `GameEngine.request_move` now gates only on `self.is_locked(from_pos)` (per-piece: `locked` or `resting`) instead of on `game_state.locked` being non-empty. Any number of pieces can be mid-motion across the board simultaneously; only a piece that is itself mid-motion or resting is blocked. See section 7 #4 (updated) for the full rationale and the test that locks in the new behavior.
14. ✅ **[UI work] Full graphical UI** — `ui/renderer.py` + `ui/sprite_manager.py` (previously empty stubs, section 4a) are now fully implemented and wired to a dedicated entry point (`ui/app-ui.py`), on top of the logic layers described in this document without changing any of them beyond the small additive exposures in section 7 #14. Covers: board+piece rendering with full idle/move/jump/long_rest/short_rest animation, click/double-click input, move-sliding and jump-lift animation, a rest countdown bar, move history panels, player-name entry, and game-over display. Fully described, including every deviation from the original plan and every bug found along the way, in **`ui/UI_DESIGN.md`** — not duplicated here.

Current test coverage: 65 unit tests passing (`pytest`), spread across all logic layers (the UI layer has no automated tests — verified manually/headlessly per iteration, see `ui/UI_DESIGN.md`).

---

## 9. What Is Still Missing

- ~~Actual graphical UI~~ **[UI work] Done** — see section 8 item 14 and `ui/UI_DESIGN.md`. That document's own §14 lists what's still open *within* the UI specifically (mainly: `speed_m_per_sec` reconciliation, no formal `cv2`/`numpy` dependency declaration, no legal-move highlighting/illegal-move feedback in the graphical UI).
- **`.kfc` script files** under `scripts/` — not actually written during the conversation (mentioned in the structure but not created); the folder itself doesn't exist either.
- **`integration/`** — no folder, no comprehensive end-to-end integration tests exist (only unit tests exist, even if some are "lightly integration-style").
- **En Passant** — not implemented (not required by any iteration so far).
- **Castling** — not implemented.
- **Support for non-textual/binary board representation** — discussed as a future option (see section 10) but not implemented.
- **Support for user-defined custom games (custom piece rules)** — discussed but not implemented (see section 10).
- **More detailed error reporting in text mode** — currently `Controller`/`GameEngine` simply "stay silent" (`return`) when a move is illegal, with no error message to the user. A feedback channel may be needed in the future.

---

## 10. TODO List (explicit and implied from the conversation)

- [x] ~~Implement `renderer.py` + `sprite_manager.py` under `game-chess/ui/` (currently empty stubs) with a graphical UI (step 10 of the spec), building on the sprite/animation assets already staged in `ui/game_snapshot/` (section 4a).~~ **Resolved** — see section 8 item 14 / `ui/UI_DESIGN.md`.
- [x] ~~Decide how per-piece animation state (idle/move/jump/short_rest/long_rest, driven by `ui/game_snapshot/**/config.json`) is modeled — new Model state vs. a new layer — without letting `RealTimeArbiter`/`GameEngine` become visual-aware.~~ **Resolved**: entirely inside `SpriteManager.determine_state`, reading existing `GameState` fields — no new model state was needed. See `ui/UI_DESIGN.md` §4.
- [ ] Reconcile `speed_m_per_sec` (in the `ui/game_snapshot/` configs) against `DEFAULT_SPEED`/`calculate_duration` (ms/square, Chebyshev) in `realtime/motion.py` — decide whether/how they map to each other. **Still open** — the built renderer ended up not needing `speed_m_per_sec` at all (uses `frames_per_sec` for animation timing instead), so this was never actually resolved, just avoided.
- [ ] Decide whether OpenCV (`cv2`, used by `ui/img.py`, and now required to run `ui/app-ui.py`) becomes an actual declared project dependency (e.g. `requirements.txt`), or gets replaced. **Still open** — `cv2`/`numpy` are used directly in `renderer.py` too now (not just `img.py`), making this more pressing than before.
- [ ] Actually write `.kfc` files under `scripts/` (board_parsing, click_to_move, invalid_moves, capture, game_over).
- [x] ~~Finally confirm against the grader/spec: is the "global lock — only one move on the board" rule permanent, or an interim stage that will later be replaced with full concurrency (per-piece lock only)?~~ **Resolved**: the global lock was removed (section 7 #4) — `request_move` now uses per-piece `is_locked` only, so any number of pieces can move concurrently; only lock/rest state on that specific square blocks a move.
- [x] ~~Decide and document: should jumping (`request_jump`) also use `is_locked(pos)` (i.e. also respect `resting`, not just `locked`)?~~ **Resolved**: `request_jump` now uses `self.is_locked(pos)`, so a resting piece can no longer jump — see section 7 #10.
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