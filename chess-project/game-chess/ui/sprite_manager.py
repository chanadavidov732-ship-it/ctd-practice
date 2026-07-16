import json
import pathlib

from ui.img import Img

ASSETS_ROOT = pathlib.Path(__file__).parent / "game_snapshot" / "pieces_mine"

# Long vs. short rest is decided purely by remaining rest duration (UI_DESIGN.md section 4):
# above this threshold -> long_rest, at/below it -> short_rest. Matches SHORT_REST_MS in realtime/motion.py.
REST_THRESHOLD_MS = 500


class SpriteManager:
    """State machine for piece animation: loads/caches sprites, picks state + frame."""

    def __init__(self, assets_root=ASSETS_ROOT, sprite_size=100):
        self.assets_root = pathlib.Path(assets_root)
        self.sprite_size = sprite_size
        self._cache = {}  # (token, state) -> {"frames": [Img, ...], "frames_per_sec": int, "is_loop": bool}

    def determine_state(self, is_airborne, is_moving, rest_remaining_ms):
        if is_airborne:
            return "jump"
        if rest_remaining_ms and rest_remaining_ms > 0:
            return "long_rest" if rest_remaining_ms > REST_THRESHOLD_MS else "short_rest"
        if is_moving:
            return "move"
        return "idle"

    def _load_state(self, token, state):
        key = (token, state)
        if key in self._cache:
            return self._cache[key]

        state_dir = self.assets_root / token / "states" / state
        with open(state_dir / "config.json", encoding="utf-8") as f:
            config = json.load(f)

        sprite_paths = sorted((state_dir / "sprites").glob("*.png"), key=lambda p: int(p.stem))
        size = (self.sprite_size, self.sprite_size)
        frames = [Img().read(path, size=size, keep_aspect=True) for path in sprite_paths]

        entry = {
            "frames": frames,
            "frames_per_sec": config["graphics"]["frames_per_sec"],
            "is_loop": config["graphics"]["is_loop"],
        }
        self._cache[key] = entry
        return entry

    def get_frame_image(self, token, state, elapsed_ms):
        entry = self._load_state(token, state)
        frames = entry["frames"]
        frame_index = int(elapsed_ms / 1000 * entry["frames_per_sec"])

        if entry["is_loop"]:
            frame_index %= len(frames)
        else:
            frame_index = min(frame_index, len(frames) - 1)

        return frames[frame_index]

    def get_sprite(self, token, is_airborne, is_moving, rest_remaining_ms, elapsed_ms):
        state = self.determine_state(is_airborne, is_moving, rest_remaining_ms)
        return self.get_frame_image(token, state, elapsed_ms)
