# Kung Fu Chess — Graphical UI Design

> Design for the graphical UI layer, built on top of the existing engine (`game-chess/engine/`, `realtime/`, `model/`). This document originally described the *planned* design before implementation. **It has now been updated to reflect what was actually built** across iterations 1–12 (plus the rest-bar addition after iteration 12) — sections that changed during implementation are marked **[AS BUILT]**, with the original planned behavior kept alongside for context where it diverged.

---

## 1. Goal

Build the graphical UI layer for the chess game.

- `renderer.py` and `sprite_manager.py` never call into `engine/`, `rules/`, or `realtime/` *decision* logic (legality, motion scheduling, capture) — they only read state and translate it into pixels, and hand raw input back up to `Controller`.
- Game logic (what is legal, when a move settles, when a piece may act again) stays entirely in `model/`, `rules/`, `realtime/`, `engine/` — untouched by rendering concerns.

### [AS BUILT] No `GameSnapshot` object exists

The original draft imagined a `GameSnapshot` data structure (dict/dataclass) handed to the renderer each frame. **This was not built.** Instead, `Renderer` holds direct references to the live `board`, `controller`, `game_engine` (and, through it, `game_engine.game_state`) and `move_history` list, and reads them fresh every frame in `_draw_frame()`. There was never a snapshot/copy step — the renderer always reads current live objects. This is simpler than the original plan and was not revisited, since no bug or need for a decoupled snapshot ever came up.

The folder `ui/game_snapshot/` (sprite assets) still has no naming collision with any class — there is no `GameSnapshot` class at all now, planned or otherwise.

---

## 2. Folder Structure

```
game-chess/
├── ui/
│   ├── game_snapshot/        # sprite/animation assets
│   │   ├── board.png
│   │   └── pieces_mine/
│   │       └── <color><type>/            # e.g. wK, bQ — matches board token order
│   │           └── states/
│   │               ├── idle/
│   │               ├── move/
│   │               ├── jump/
│   │               ├── short_rest/
│   │               └── long_rest/
│   │                   ├── config.json
│   │                   └── sprites/*.png
│   ├── img.py                 # existing OpenCV/numpy helper — never modified
│   ├── renderer.py            # [AS BUILT] fully implemented (was an empty stub)
│   └── sprite_manager.py      # [AS BUILT] fully implemented (was an empty stub)
├── engine/game_engine.py      # [AS BUILT] one additive change — see §11a
├── realtime/realtime_arbiter.py  # [AS BUILT] two additive changes — see §11a
├── model/game_state.py        # [AS BUILT] one additive field — see §11a
└── app.py                     # composition root / entry point + main real-time loop
```

---

## 3. `renderer.py` — Responsibilities (as built)

### Construction

```python
Renderer(board, controller, game_engine, move_history, square_size=100)
```

- `board` — read every frame for piece positions (`board.get_piece`).
- `controller` — read for `controller.selected` (selection highlight) and called into for input (`handle_click`/`handle_jump`).
- `game_engine` — read for `game_engine.game_state` (the single source of truth for `locked`/`airborne`/`resting`/`resting_duration`/`pending_moves`/`clock`) and `game_engine.is_over`.
- `move_history` — a plain `list`, **owned and appended to by `app.py`** (not the renderer); the renderer only reads it to build the two side panels. Passed by reference so `app.py`'s `move_history.extend(settled)` is immediately visible to the renderer without any extra wiring.
- Opens the `cv2` window and registers the mouse callback **once**, in `__init__` (`cv2.namedWindow` + `cv2.setMouseCallback`).

### Canvas layout **[AS BUILT — full layout, §7]**

The canvas is **wider and taller than the board itself**, to fit two side history panels plus a header/footer name bar:

- `PANEL_WIDTH = 220` px on each side (White panel left, Black panel right).
- `HEADER_HEIGHT = FOOTER_HEIGHT = 60` px (player name bars, top and bottom).
- `board_offset_x = PANEL_WIDTH`, `board_offset_y = HEADER_HEIGHT` — every piece/selection/game-over/rest-bar draw call adds these offsets before drawing.
- Canvas size: `(PANEL_WIDTH*2 + board_width, HEADER_HEIGHT + board_height + FOOTER_HEIGHT)`.

**Background composition** — `board.png` cannot be used to fill the whole canvas directly: stretching it non-uniformly to the full canvas width/height distorts its baked-in 8×8 grid so it no longer lines up with the 100px piece grid (this was a real bug found and fixed after iteration 8 — see §12). The fix, still using only `Img`'s existing API:
1. Read `board.png` once, resized to the *full canvas size* — used only as filler behind the side panels and header/footer (which then get fully painted over by solid-color rectangles anyway).
2. Read `board.png` a **second time**, resized to the exact `board_width × board_height` (undistorted, square cells), and `draw_on()` it at `(board_offset_x, board_offset_y)` — this is the actual playing surface pieces are drawn onto.

### Per-frame flow — `_draw_frame()`

1. Build the canvas as above.
2. `_draw_pieces` — for each occupied cell: if there's an active `pending_move` whose `from` is this cell, ask `SpriteManager` for the **move** sprite and draw at an **interpolated pixel position** between `from` and `to` (see §4); otherwise ask for the sprite matching the piece's current state (idle/jump/rest) and draw it at its fixed cell position.
3. `_draw_rest_bars` **[NEW — added after iteration 12, see §13]** — for every position in `game_state.resting`, draw a thin countdown bar along the bottom edge of that cell.
4. `_draw_selection` — yellow rectangle (`cv2.rectangle`, 4-tuple BGRA color) around `controller.selected["pos"]`, if any.
5. `_draw_game_over` — if `game_engine.is_over`, overlay `"GAME OVER"` text (via `Img.put_text`) centered on the board.
6. `_draw_history_panels` — two solid side panels (White left, Black right), each listing that color's settled moves (see §6).
7. `_draw_names` — solid header/footer bars with the two player names, centered (see §7).
8. `cv2.imshow` + `cv2.waitKey(FRAME_DELAY_MS=30)` — returns the pressed key (or `-1`).

`render()` wraps this: it returns `True` to keep looping, or `False` (and closes the window) if the key was `ESC`/`q`. **`app.py` owns the `while` loop** and calls `render()` once per iteration — the renderer does not loop internally (see §8, this changed after iteration 4).

### Mouse click ownership **[AS BUILT — deviates from the original planned flow]**

The original draft planned: renderer stores "last click" → `app.py`'s loop polls `renderer.get_click()` → `app.py` calls the engine. **This was not built.** Instead, the `cv2` mouse callback calls straight into `Controller` from inside the renderer:

```
mouse event (OpenCV callback, inside Renderer._on_mouse)
   -> window-pixel coordinates (x, y)
   -> subtract (board_offset_x, board_offset_y)   # window pixel -> board pixel
   -> EVENT_LBUTTONDOWN   -> controller.handle_click(board_x, board_y)
   -> EVENT_LBUTTONDBLCLK -> controller.handle_jump(board_x, board_y)
```

`Controller.handle_click`/`handle_jump` (unchanged) do their own `BoardMapper.pixel_to_cell()` conversion internally — the renderer does not call `BoardMapper` directly, it just makes sure the pixel coordinates it hands over are already board-relative (offset already subtracted). `get_click()` was never implemented; there is no such method. This still keeps "renderer never decides game logic" true, because `Controller` (not `Renderer`) is the layer that decides whether/when to call `GameEngine` — the renderer only forwards raw (offset-corrected) input to it, exactly the same division of labor `Controller` already had in the text-mode UI.

**Known rough edge:** OpenCV fires a `LBUTTONDOWN` (twice) *before* the `LBUTTONDBLCLK` event for any double-click. This means `handle_click` runs twice ahead of `handle_jump` on every double-click. Harmless when double-clicking a piece that was already/becomes selected; if a different piece was selected beforehand, the first of those two clicks can trigger an ordinary `request_move` as a side effect before the jump fires. Not worked around — flagged as a known limitation, not fixed.

---

## 4. `sprite_manager.py` — Responsibilities (as built)

```python
SpriteManager(square_size=100)
```

- Loads and caches sprite frames per `(token, state)` — `_load_frames`/`_load_config`, keyed off `ui/game_snapshot/pieces_mine/<token>/states/<state>/`.
- `determine_state(pos, game_state)` → one of `idle`/`move`/`jump`/`long_rest`/`short_rest`, purely from `game_state.locked`/`airborne`/`resting` (no new model state added, as required).
- `get_sprite_for_piece(token, pos, game_state)` — full path for a stationary piece: determines state, computes elapsed-in-state, returns the right frame.
- `get_sprite_for_move(move, game_state)` — separate path for a piece with an active `pending_move`; always state `"move"`, elapsed computed from the move's own stored `duration` (see §11a — this is why `duration` was added to `pending_moves`).
- `rest_fraction_remaining(pos, game_state)` **[NEW — added after iteration 12]** — see §13.
- `get_sprite(token, state, elapsed_ms)` — shared frame-selection logic: `frame_index = elapsed_ms // (1000/frames_per_sec)`, wrapped (`% len(frames)`) if `config.json`'s `is_loop` is true, clamped to the last frame otherwise.

### Long Rest vs. Short Rest — determination rule (unchanged from original design, with a known limitation)

`determine_state` still decides `long_rest` vs `short_rest` **purely from remaining time**, exactly as originally designed:
- `remaining = game_state.resting[pos] - game_state.clock`
- `remaining > REST_THRESHOLD_MS` (= `(LONG_REST_MS + SHORT_REST_MS) / 2` = 750ms) ⇒ `long_rest`, else `short_rest`.

**[AS BUILT — known limitation, deliberately not touched]** This heuristic cannot distinguish "a `long_rest` that has decayed below 750ms remaining" from "a `short_rest` that just started" — both look identical from `remaining` alone once it drops under 500ms. This was found while building the rest-countdown-bar feature (§13) and was **deliberately left as-is** in `determine_state` (per explicit instruction: don't change existing logic, only add what's needed) — it only affects sprite-pose selection in that narrow edge window, not the countdown bar, which was given its own accurate data source instead (`resting_duration`, §11a/§13).

### Move duration source **[AS BUILT]**

The original design didn't specify where per-move duration data would come from. In practice, `pending_moves` entries didn't originally carry `duration` (only `completion_time`), which isn't enough to compute a sliding-animation progress fraction (no way to recover *when* the move started). Rather than have the UI recompute it via `realtime.motion.calculate_duration` (which would mean `sprite_manager`/`renderer` reaching into `realtime/` business logic), `duration` was added as a stored field on each `pending_moves` entry at the point `GameEngine.request_move` already computes it — see §11a.

---

## 5. `img.py`

Unchanged, exactly as planned. Renderer/SpriteManager only ever call its existing API: `Img().read(...)`, `.draw_on(...)`, `.put_text(...)`. No new methods were added to it, even when doing so would have been the "purest" fix for the canvas-composition bug (§12) — the workaround (drawing an extra correctly-sized `Img` on top) was chosen specifically to avoid touching this file.

**[AS BUILT]** A few things `img.py` still cannot do, worked around with direct `cv2` calls instead (never inside `img.py`, only in `renderer.py`, and only for primitives `Img` has no equivalent for):
- Creating a blank/solid-color canvas from scratch (`Img.read()` only loads existing files) — worked around by stretching `board.png` as filler (§12) instead of adding `Img.blank()`.
- Drawing rectangles/progress bars (`cv2.rectangle`, used directly for selection highlight, panel/header/footer backgrounds, and rest bars).
- Registering the mouse callback and running the window's event loop (`cv2.namedWindow`, `cv2.setMouseCallback`, `cv2.imshow`, `cv2.waitKey`) — the design already called for this in §3 above.
- Measuring rendered text width for centering (`cv2.getTextSize`, used only in `_draw_centered_text`).

---

## 6. Move History Panels **[AS BUILT — new, was only a layout placeholder in §7 originally]**

- `app.py` owns a plain `move_history = []` list and does `move_history.extend(settled)` every frame, where `settled` is the list `GameEngine.advance_time(ms)` now returns (see §11a).
- `Renderer._draw_history_panels` splits `move_history` by `token_color(move["token"])` into White (left panel) / Black (right panel) — going through `model/piece.py`'s `token_color`, per the project's "no raw token indexing outside `piece.py`" rule.
- Each panel: solid dark background (`PANEL_BG_COLOR`, full panel height), a title, and up to as many of the most recent move lines as fit (`(panel_height - header) // line_height`), oldest of that visible window at top.
- Move line format: `"{token} ({from_col},{from_row})->({to_col},{to_row})"`, with a trailing `" x"` if `captured_token != "."`. No algebraic chess notation — kept to the raw `(col, row)` representation already used everywhere else in the codebase.

---

## 7. Screen Layout **[AS BUILT — implemented to match]**

```
+----------------------------------------------------------+
                    Player (White) Name
+----------------------------------------------------------+
 Move History          Chess Board           Move History
  (White)              8x8 Board                (Black)
                     Animated Pieces
+----------------------------------------------------------+
                    Opponent (Black) Name
+----------------------------------------------------------+
```

Matches the original diagram exactly, with the mapping decided during implementation: **White = top name + left panel, Black = bottom name + right panel** (not specified in the original draft; chosen for consistency between the two features). Player names are typed in by the user at game start (`Renderer.prompt_player_names()`, §9) rather than being a fixed data source — the original draft didn't say where the names would come from at all.

---

## 8. `app.py` (entry point) — as built

The original draft's pseudocode (`while True: render(snapshot); click = get_click(); ...`) was not implemented as written — no snapshot, no `get_click()`. The real loop:

```python
board = Board(grid)
game_state = GameState()
arbiter = RealTimeArbiter(board, game_state)
game_engine = GameEngine(board, game_state, arbiter)
board_mapper = BoardMapper(board)
controller = Controller(board, board_mapper, game_engine)

move_history = []
renderer = Renderer(board, controller, game_engine, move_history)
renderer.prompt_player_names()          # blocks until both names are entered

last_time = time.perf_counter()
running = True
while running:
    now = time.perf_counter()
    elapsed_ms = (now - last_time) * 1000
    last_time = now

    settled = game_engine.advance_time(elapsed_ms)   # real elapsed time, not a fixed tick
    move_history.extend(settled)
    running = renderer.render()                      # draws one frame, returns False to quit
```

Mouse input is **not** polled here — it arrives asynchronously via the `cv2` callback registered inside `Renderer.__init__`, which calls straight into `Controller` (§3). `app.py`'s loop only drives time and drawing.

The pre-existing text-mode path (`text_test/script_runner.run_commands`) still exists and is untested by this change — `app.py` simply no longer calls it (replaced in iteration 1); it remains available for whoever wants to exercise the logic layers via `.kfc`-style scripts directly against `GameEngine`, independent of the GUI.

---

## 9. Player Name Entry **[NEW — not in the original draft at all]**

Before the main loop starts, `Renderer.prompt_player_names()` runs a small blocking sub-loop **on the same `cv2` window**:
- Draws a prompt + the text typed so far (`Img.put_text`, redrawn every ~30ms) on a solid-color full-canvas background.
- Captures keys directly via `cv2.waitKey()`: printable ASCII appends, `Backspace` (8) removes the last character, `Enter` (13/10) confirms.
- Called twice — once for White's name, once for Black's — falling back to `"White"`/`"Black"` if the user just presses Enter with nothing typed.
- No new dependency: everything goes through `Img`/`cv2`, nothing external (no OS text-input widgets).

This was added specifically because there is (and was) no concept of a player name anywhere in `model`/`engine` — it exists purely as `Renderer.player_name_white`/`player_name_black`, decided at UI-startup time, not part of `GameState`.

---

## 10. Class Interaction **[AS BUILT]**

```
app.py:
  GameEngine.advance_time(elapsed_ms) -> settled moves -> move_history.extend(settled)
  Renderer.render() -> reads board / controller / game_engine.game_state / move_history live
                     -> SpriteManager (state + frame selection) -> Img (draw) -> cv2 (window)

Input (separate path, event-driven, not polled by app.py):
  cv2 mouse callback (inside Renderer) -> Controller.handle_click/handle_jump
                                        -> GameEngine.request_move/request_jump
```

No `GameSnapshot` object anywhere in this path — every arrow above reads live, mutable state directly.

---

## 11. Design Principles (updated)

- `Renderer` draws, owns the `cv2` window/callback, and forwards already-offset-corrected raw input to `Controller` — it still never decides legality or timing.
- `SpriteManager` owns *all* state/time arithmetic (which state, which frame, rest-fraction) — `Renderer` never computes elapsed-in-state itself, only pixel positions.
- `GameEngine` owns all game logic; `Controller` (unchanged) is the boundary between raw input and engine mutation; `app.py` is the composition root and owns the frame loop + real-time clock.
- There is no `GameSnapshot` — UI code reads live model/engine objects directly every frame. This is simpler than originally planned and caused no observed problems.
- `img.py` is untouched. Gaps in its API (blank canvas, rectangles, text measurement, window/event/mouse plumbing) are filled with direct, narrow `cv2` calls inside `renderer.py` only — never inside `img.py`, never for anything `Img` already provides.
- UI components stay modular; the rest-bar addition (§13) needed one new `SpriteManager` method and one new `Renderer` method and touched nothing else.

---

## 11a. Additive changes to `model`/`realtime`/`engine` **[AS BUILT — corrects "engine/ untouched by this design" from the original draft]**

The original draft assumed the UI layer could be built without touching `engine/`/`realtime/`/`model/` at all. In practice, **three small, purely additive changes** were needed — never changing existing behavior, only exposing data the UI needed:

1. **`engine/game_engine.py`** — `advance_time(ms)` now ends with `return settled` (previously computed `settled` internally for the king-capture check and discarded it). One line. Powers the move-history feature (§6).
2. **`realtime/realtime_arbiter.py`** — `start_motion(...)` gained a `duration` parameter (the caller, `GameEngine.request_move`, already computed this value — it's now passed through instead of only implicitly encoded in `completion_time`), stored on the `pending_moves` entry. Powers the move-sliding animation (§4) without the UI re-deriving duration itself.
3. **`realtime/realtime_arbiter.py` + `model/game_state.py`** — a new `GameState.resting_duration` dict (`pos -> original total ms`), populated alongside `resting[pos]` at the same two call sites (`_settle_due_moves`, `_land_due_jumps`) and cleared alongside it in `_release_due_rests`. Powers the rest-countdown bar (§13) with an unambiguous total duration, sidestepping the threshold-guessing limitation described in §4.

None of these changed `rule_engine.py`, `piece_rules.py`, move legality, capture, or timing behavior — confirmed by the full existing unit test suite passing unchanged after each.

---

## 12. Bugs found and fixed during implementation

Two real rendering bugs were found (via direct pixel inspection of saved frames, not just eyeballing the live window) and fixed, both isolated to `renderer.py`:

1. **Checkerboard misalignment.** Stretching `board.png` non-uniformly to the full multi-panel canvas width distorted its baked-in 8×8 grid so it no longer matched the 100px piece grid. Fixed by drawing a second, correctly-square copy of `board.png` on top, positioned exactly at the board's real offset (§3).
2. **Invisible panel/selection backgrounds.** `cv2.rectangle` calls used 3-tuple BGR colors on a 4-channel (BGRA) canvas; OpenCV silently zero-pads the missing alpha channel, making the "filled" rectangle fully transparent. Fixed by using explicit 4-tuple `(B, G, R, 255)` colors everywhere a color is passed to `cv2.rectangle`.

---

## 13. Rest Countdown Bar **[NEW — added after iteration 12, not in the original draft]**

A small thin progress bar drawn along the bottom edge of any cell in `game_state.resting`, visually expressing how much lock time remains before the piece can act again:

- `SpriteManager.rest_fraction_remaining(pos, game_state)` → `1.0` right as resting starts, decaying to `0.0` right before it clears, using `game_state.resting_duration[pos]` as the authoritative total (see §11a) — **not** `determine_state()`'s remaining-time guess, which is ambiguous in exactly this use case (§4).
- `Renderer._draw_rest_bars`: for each resting position, draws a full-width dark track, then a fill rectangle `square_size * fraction` wide, colored by linear interpolation from red (`fraction=1.0`, just locked) to green (`fraction=0.0`, about to unlock).
- Drawn after pieces, before the selection highlight, so it sits at the bottom of the cell without covering the piece sprite.

---

## 14. Open Items Carried Over from `Handoff.md` §9/§10

- Reconcile `speed_m_per_sec` (in `config.json` files) against `DEFAULT_SPEED`/Chebyshev distance in `realtime/motion.py` — **still open**, never addressed; the two units coexist unreconciled (animation `frames_per_sec` is used for frame cycling, `DEFAULT_SPEED`/`calculate_duration` for actual motion timing — they were never made to agree on real-world scale).
- Whether `cv2`/`numpy` become declared project dependencies (e.g. in a `requirements.txt`) — **still open**, no dependency file was added during any UI iteration.
- Legal-move highlighting, illegal-move feedback — still explicitly deferred ("reserved for later" / optional polish), not implemented.
- En Passant, Castling, `integration/` tests — unrelated to the UI work, still open per `Handoff.md`.
