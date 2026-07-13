import math

DEFAULT_SPEED = 1000  # ms per square

JUMP_DURATION_MS = 1000   # כלל 1 - קפיצה נמשכת 1000ms

def calculate_duration(from_pos, to_pos, speed=DEFAULT_SPEED):
    dx = abs(to_pos[0] - from_pos[0])
    dy = abs(to_pos[1] - from_pos[1])
    distance = max(dx, dy)
    return distance * speed