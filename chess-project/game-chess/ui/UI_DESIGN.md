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

1. Load/draw empty board image (`IMG.read` + `IMG.drawOn`).
2. Loop over every piece in `snapshot`.
3. Convert logical `(row, col)` → pixel coordinates.
4. Ask `SpriteManager` which sprite to draw for this piece.
5. Draw the sprite on the board (`IMG.drawOn`).
6. Draw player name.
7. Draw opponent name.
8. Draw the two move-history tables, one on each side of the board.
9. Display the final frame (`IMG.show`).

**Full responsibility list:**
- Draw the chess board.
- Draw every piece.
- Draw player name / opponent name.
- Draw both move-history tables.
- Capture mouse clicks (OpenCV `cv2.setMouseCallback`, registered internally by the renderer).
- Convert the raw pixel click into board coordinates via `BoardMapper`.
- Expose the last click to the caller via `get_click()`.

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
- Cache loaded images.
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

---

## 11. Open Items Carried Over from `Handoff.md` §9/§10

- Reconcile `speed_m_per_sec` (in `config.json` files) against `DEFAULT_SPEED`/Chebyshev distance in `realtime/motion.py`.
- Decide whether `cv2`/`numpy` become declared project dependencies.
- Model per-piece animation state (idle/move/jump/short_rest/long_rest) without making `RealTimeArbiter`/`GameEngine` visual-aware — this design keeps that mapping entirely inside `SpriteManager`, driven by data already available on the snapshot (position, `locked`/`resting`/`airborne` status, remaining rest ms).
