import math

DEFAULT_SPEED = 200  # ms per square (euclidean distance)


def calculate_duration(from_pos, to_pos, speed=DEFAULT_SPEED):
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    distance = math.sqrt(dx * dx + dy * dy)
    return distance * speed