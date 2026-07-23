from shared.realtime.motion import calculate_duration

def test_calculate_duration_straight_line():
    duration = calculate_duration((0, 0), (0, 3))
    assert duration == 3000 