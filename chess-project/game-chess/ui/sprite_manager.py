import json
import pathlib

from ui.img import Img
from realtime.motion import JUMP_DURATION_MS, LONG_REST_MS, SHORT_REST_MS

SPRITES_ROOT = pathlib.Path(__file__).parent / "game_snapshot" / "pieces_mine"
REST_THRESHOLD_MS = (LONG_REST_MS + SHORT_REST_MS) / 2

STATE_IDLE = "idle"
STATE_MOVE = "move"
STATE_JUMP = "jump"
STATE_LONG_REST = "long_rest"
STATE_SHORT_REST = "short_rest"


class SpriteManager:
    def __init__(self, square_size=100):
        self.square_size = square_size
        self._frames_cache = {}
        self._config_cache = {}

    def determine_state(self, pos, game_state):
        if pos in game_state.airborne:
            return STATE_JUMP
        if pos in game_state.locked:
            return STATE_MOVE
        if pos in game_state.resting:
            remaining = game_state.resting[pos] - game_state.clock
            if remaining > REST_THRESHOLD_MS:
                return STATE_LONG_REST
            return STATE_SHORT_REST
        return STATE_IDLE

    def get_sprite_for_piece(self, token, pos, game_state):
        state = self.determine_state(pos, game_state)
        elapsed_ms = self._elapsed_in_state(pos, state, game_state)
        return self.get_sprite(token, state, elapsed_ms)

    def get_sprite_for_move(self, move, game_state):
        elapsed_ms = move["duration"] - (move["completion_time"] - game_state.clock)
        return self.get_sprite(move["token"], STATE_MOVE, elapsed_ms)

    def jump_progress(self, pos, game_state):
        """0.0 right as a jump starts, 1.0 right as it's about to land. None if not airborne."""
        if pos not in game_state.airborne:
            return None
        remaining = game_state.airborne[pos] - game_state.clock
        elapsed = JUMP_DURATION_MS - remaining
        return max(0.0, min(1.0, elapsed / JUMP_DURATION_MS))

    def rest_fraction_remaining(self, pos, game_state):
        """1.0 right as resting starts, 0.0 right as it's about to clear. None if not resting.

        Uses game_state.resting_duration (the actual original duration for this
        rest) rather than determine_state()'s remaining-time guess, which can't
        tell a long_rest that has decayed below the threshold apart from a
        short_rest that just started.
        """
        if pos not in game_state.resting:
            return None
        total = game_state.resting_duration.get(pos)
        if not total:
            return None
        remaining = game_state.resting[pos] - game_state.clock
        return max(0.0, min(1.0, remaining / total))

    def get_sprite(self, token, state, elapsed_ms):
        frames = self._load_frames(token, state)
        config = self._load_config(token, state)
        fps = config["graphics"]["frames_per_sec"]
        is_loop = config["graphics"]["is_loop"]
        frame_duration = 1000 / fps
        frame_index = int(max(elapsed_ms, 0) // frame_duration)
        if is_loop:
            frame_index %= len(frames)
        else:
            frame_index = min(frame_index, len(frames) - 1)
        return frames[frame_index]

    def _elapsed_in_state(self, pos, state, game_state):
        if state == STATE_JUMP:
            remaining = game_state.airborne[pos] - game_state.clock
            return JUMP_DURATION_MS - remaining
        if state == STATE_LONG_REST:
            remaining = game_state.resting[pos] - game_state.clock
            return LONG_REST_MS - remaining
        if state == STATE_SHORT_REST:
            remaining = game_state.resting[pos] - game_state.clock
            return SHORT_REST_MS - remaining
        return game_state.clock

    def _state_dir(self, token, state):
        return SPRITES_ROOT / token / "states" / state

    def _load_config(self, token, state):
        key = (token, state)
        if key not in self._config_cache:
            path = self._state_dir(token, state) / "config.json"
            with open(path, encoding="utf-8") as f:
                self._config_cache[key] = json.load(f)
        return self._config_cache[key]

    def _load_frames(self, token, state):
        key = (token, state)
        if key not in self._frames_cache:
            sprites_dir = self._state_dir(token, state) / "sprites"
            paths = sorted(sprites_dir.glob("*.png"), key=lambda p: int(p.stem))
            size = (self.square_size, self.square_size)
            self._frames_cache[key] = [Img().read(p, size=size) for p in paths]
        return self._frames_cache[key]
