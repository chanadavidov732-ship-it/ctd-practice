# Kung Fu Chess — Graphical UI Design

> Design for the first graphical UI layer, built on top of the existing engine (`game-chess/engine/`, `realtime/`, `model/`). This document supersedes the initial draft — the four contradictions found in review are resolved inline and marked **[RESOLVED]**.

---

## 1. Goal

Build the first graphical UI layer for the chess game.

- The renderer receives a `GameSnapshot` from the game engine and is responsible **only** for displaying the current game state.
- Game logic stays completely outside the UI — `renderer.py` and `sprite_manager.py` never call into `engine/`, `rules/`, or `realtime/` decision logic; they only read data handed to them and return raw input back up.

`GameSnapshot` here is a **data structure passed at each frame** (whatever the engine exposes at that point — dict, dataclass, or namedtuple), not a formal existing class in the codebase today. **[RESOLVED — naming]** There is no class named `GameSnapshot` in `game-chess/`, so the folder `ui/game_snapshot/` (sprite assets) does not actually collide with any class of the same name. No rename needed.

---

## 2. Folder Structure

Matches what already exists on disk (see `game-chess/ui/`):

```
game-chess/
├── ui/
│   ├── game_snapshot/        # sprite/animation assets (not the GameSnapshot data object — see §1)
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
│   ├── img.py                 # existing OpenCV/numpy helper — do not modify
│   ├── renderer.py            # currently an empty stub — this design fills it in
│   └── sprite_manager.py      # currently an empty stub — this design fills it in
├── engine/                    # GameEngine — untouched by this design
└── app.py                     # composition root / entry point (referred to as "main.py" in the original pseudocode)
```

---

## 3. `renderer.py` — Responsibilities

Draws the entire screen. Never decides animation frames — that's `SpriteManager`'s job.

**Per-frame flow — `render(snapshot)`:**

1. Load the board image, resized to `(board.width * square_size, board.height * square_size)` (`IMG.read`). **[UPDATED — implementation]** re-reading + resizing every frame, instead of caching a fixed-size board once, is what keeps the checkerboard pixels and the piece-position math in section "Centering" below in sync whenever `square_size` changes — see the note there.
2. Loop over every piece in `snapshot["pieces"]`.
3. Convert logical `(col, row)` → the pixel **center** of that cell (`_cell_center`), not its top-left corner — see "Centering pieces in their square" below.
4. Ask `SpriteManager` which sprite to draw for this piece.
5. Draw the sprite on the board, offset from the cell center by the sprite's own rendered half-width/half-height (`IMG.draw_on`).
6. Draw player name.
7. Draw opponent name.
8. Draw the two move-history tables, one on each side of the board.
9. Display the final frame (`IMG.show`).

**Full responsibility list:**
- Draw the chess board.
- Draw every piece, always centered in its square regardless of `square_size` (see below). **[UPDATED — implementation]**
- Draw player name / opponent name.
- Draw both move-history tables.
- Capture mouse clicks (OpenCV `cv2.setMouseCallback`, registered internally by the renderer).
- Convert the raw pixel click into board coordinates via `BoardMapper`.
- Expose the last click to the caller via `get_click()`.

### Centering pieces in their square **[NEW — implementation, resolves the "keeps working if the board shrinks" requirement]**

Two things have to be computed from `square_size` — not hardcoded — for a piece to stay centered in its cell at any board scale:

1. **Cell center, not cell corner.** `Renderer._cell_center((col, row))` returns `(col*square_size + square_size//2, row*square_size + square_size//2)`.
2. **Offset by the sprite's own actual size**, not by an assumed square: `x, y = cx - sprite_w//2, cy - sprite_h//2`, where `sprite_w, sprite_h` come from `sprite.img.shape`, not from `square_size`. `draw_on` draws from the top-left corner, so this offset is what turns a corner-anchored draw into a centered one.

This alone isn't enough — the board *image* also has to be reloaded at `board.width*square_size × board.height*square_size` every frame (step 1 above), otherwise the checkerboard raster (a fixed-size PNG) stops lining up with the `square_size`-based math the moment `square_size` changes. Both the board image and `SpriteManager`'s sprite output (see section 4) scale off the same `square_size` value, which `app.py` sets once and passes to `BoardMapper`, `SpriteManager`, and `Renderer` — see section 6.

### Mouse click ownership **[RESOLVED — flow]**

The renderer *listens* for clicks (owns the OpenCV callback) and *translates* pixel → board coordinates, but it does **not** call the engine directly:

```
mouse click (OpenCV callback, inside Renderer)
   -> pixel coordinates
   -> BoardMapper.pixel_to_cell()
   -> stored as "last click" inside Renderer
   -> renderer.get_click()          # called from app.py's loop
   -> app.py calls engine.request_move(...) / handle_click(...)
```

`app.py` (the "main.py" of the original pseudocode) remains the sole caller of the engine. This keeps "renderer never manipulates game logic" true even though the renderer is the thing physically listening for OS-level mouse events.

---

## 4. `sprite_manager.py` — Responsibilities

A state machine for piece animation, nothing else:

- Load sprite folders (`ui/game_snapshot/pieces_mine/<color><type>/states/...`).
- Resize every loaded sprite frame to `(sprite_size, sprite_size)` (constructor param, default 100, `keep_aspect=True`). **[NEW — implementation]** the raw source PNGs are 320×320 — far larger than a 100px board square — so without this resize step pieces overflow past their cell (and past the board edge for pieces near row/col 7). `app.py` passes the same `square_size` value used by `BoardMapper`/`Renderer` here, so sprites and board squares always agree on scale (see section 6).
- Cache loaded images, keyed by `(token, state)`; frames are loaded lazily on first use.
- Determine the current animation state for a piece.
- Calculate the current animation frame (using `config.json`'s `frames_per_sec` / `is_loop`).
- Return the correct image for the renderer to draw.

**Flow:**
```
Piece -> current state -> idle? move? jump? long_rest? short_rest?
      -> calculate animation frame -> return image
```

### Long Rest vs. Short Rest **[RESOLVED — determination rule]**

Determined **purely from remaining rest duration**, nothing else. `SpriteManager` does not need to know what action preceded the rest.

This matches the engine constants already defined in `realtime/motion.py`:
- `LONG_REST_MS = 1000` → rest remaining above the mid threshold ⇒ **Long Rest**.
- `SHORT_REST_MS = 500` → rest remaining at/below the mid threshold ⇒ **Short Rest**.

In practice a regular move always sets `LONG_REST_MS` and a landed jump always sets `SHORT_REST_MS` (per `realtime_arbiter.py`), so duration alone is a reliable, sufficient signal — no need to thread "previous action" through the snapshot.

---

## 5. `img.py`

Unchanged. Renderer only calls its existing API:
- `IMG.read(...)`
- `IMG.resize(...)`
- `IMG.drawOn(...)`

---

## 6. `app.py` (entry point)

**Target design** (unchanged) — once the engine loop is wired back in:

```
engine = GameEngine(...)
renderer = Renderer()

while True:
    snapshot = engine.get_snapshot()
    renderer.render(snapshot)

    click = renderer.get_click()
    if click:
        engine.handle_click(click)   # or request_move / request_jump, per existing engine API
```

**Current implementation status [UPDATED — first UI milestone]:** `app.py` does not run the loop above yet. `GameState`/`RealTimeArbiter`/`GameEngine`/`Controller`/`board_parser`/`script_runner` imports and setup are commented out (not deleted — meant to be restored once the renderer is ready to drive real game state). Today `main()`:

1. Builds the standard chess starting grid directly (pawns via `pawn_start_row`, back rank via a local `BACK_RANK_ORDER` list) — not read from `engine`/`io_options`.
2. Defines **one `square_size` value** and passes it to `BoardMapper`, `SpriteManager(sprite_size=square_size)`, and `Renderer(square_size=square_size)`. This is the single place to change to resize the whole board — every pixel computation in `Renderer`/`SpriteManager` derives from it, so nothing else needs to change (see the centering note in section 3).
3. Converts the grid into a flat `pieces` list of `{"token": "wK", "pos": (col, row)}` dicts and calls `renderer.render({"pieces": pieces})` **once** (no loop, no `get_click()` consumption yet).

This `{"pieces": [...]}` shape is the **provisional snapshot contract** `Renderer.render()` currently reads (also expects optional `"player_name"`, `"opponent_name"`, `"player_moves"`, `"opponent_moves"` keys, all read via `.get(...)` with safe defaults). It has not been reconciled against a real `GameEngine.get_snapshot()` — see section 11.

---

## 7. Screen Layout

```
+----------------------------------------------------------+
                         Player Name
+----------------------------------------------------------+
 Move History          Chess Board           Move History
  (Player)             8x8 Board               (Opponent)
                     Animated Pieces
+----------------------------------------------------------+
                       Opponent Name
+----------------------------------------------------------+
```

Two separate move-history tables, one per side of the board — one per player.

---

## 8. Rendering Order (per frame)

1. Draw background.
2. Draw empty chess board.
3. Draw all pieces.
4. Draw overlays (reserved for later — selection highlight, legal-move markers, etc.).
5. Draw player name.
6. Draw opponent name.
7. Draw both move-history tables (left + right).
8. Display frame.

---

## 9. Class Interaction

```
GameEngine -> GameSnapshot -> Renderer -> SpriteManager -> IMG -> Screen

Renderer.get_click() -> app.py -> GameEngine   (input path, separate from the render path above)
```

---

## 10. Design Principles

- `Renderer` is responsible only for drawing (and for owning/relaying raw mouse input — it still never decides game logic).
- `SpriteManager` is responsible only for animation-state selection, using rest **duration** alone to distinguish long vs. short rest.
- `GameEngine` owns all game logic; `app.py` is the only caller of engine mutation methods.
- `GameSnapshot` is a read-only data view for the UI — not a class the UI folder structure needs to avoid colliding with.
- `img.py` is an existing utility library — not modified.
- UI components stay modular so additional animations/overlays can be added later without touching game logic.
- **[NEW]** `square_size` has exactly one source of truth (`app.py`), threaded into `BoardMapper`, `SpriteManager`, and `Renderer` — resizing the board is a one-line change, not a hunt through pixel math.
- **[NEW]** A piece's on-screen position is derived from its cell's center plus the sprite's own rendered dimensions, never from a hardcoded/assumed size — this is what keeps pieces visually centered in their square at any `square_size` (see section 3).

---

## 11. Open Items Carried Over from `Handoff.md` §9/§10

- Reconcile `speed_m_per_sec` (in `config.json` files) against `DEFAULT_SPEED`/Chebyshev distance in `realtime/motion.py`.
- Decide whether `cv2`/`numpy` become declared project dependencies.
- ~~Model per-piece animation state (idle/move/jump/short_rest/long_rest) without making `RealTimeArbiter`/`GameEngine` visual-aware~~ **[DONE]** — `SpriteManager.determine_state(is_airborne, is_moving, rest_remaining_ms)` implements exactly this, as plain parameters rather than a snapshot object with assumed field names (see below).
- ~~Keep pieces visually correct (fit their square, stay centered) regardless of board/sprite size~~ **[DONE]** — see the centering note in section 3 and the resize note in section 4.

**New open items from the first implementation pass:**
- **The real `GameSnapshot`/pieces contract is still provisional.** `Renderer.render()` currently expects `{"pieces": [{"token": "wK", "pos": (col, row), "is_airborne": bool, "is_moving": bool, "rest_remaining_ms": int, "elapsed_ms": int}, ...], "player_name": ..., "opponent_name": ..., "player_moves": [...], "opponent_moves": [...]}`. None of this has been checked against what `GameEngine`/`RealTimeArbiter` can actually expose today (e.g. there is no `elapsed_ms`-since-state-change tracked anywhere in `GameState`/`RealTimeArbiter` yet) — expect this shape to change once section 6's real loop is wired back in.
- **The `app.py` render loop + `get_click()` → `engine.request_move`/`request_jump` wiring from section 6's target design is not implemented.** `main()` currently does a single one-shot `render()` of a hardcoded standard starting position (pawns + back rank), with all `GameEngine`/`Controller`/`RealTimeArbiter`/`io_options` imports commented out rather than deleted.
- `Renderer`'s move-history/name text placement uses fixed pixel offsets (e.g. `x=10`, `y=20`) rather than being derived from `square_size` — unlike piece centering, this has **not** been made scale-independent yet.
