import math

DEFAULT_SPEED = 1000  # ms per square


def calculate_duration(from_pos, to_pos, speed=DEFAULT_SPEED):
    dx = abs(to_pos[0] - from_pos[0])
    dy = abs(to_pos[1] - from_pos[1])
    distance = max(dx, dy)         # CHANGED: was math.sqrt(dx*dx + dy*dy)
    return distance * speed