import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backtest"))
import structure_backtest as s


def zigzag(points, step=6):
    """Bars that walk linearly between turning points."""
    b, k = [], 0
    for a, z in zip(points, points[1:]):
        for j in range(step):
            p = a + (z - a) * j / step
            b.append({"d": f"d{k:04d}", "o": p, "h": p + 0.2, "l": p - 0.2, "c": p, "v": 1e6}); k += 1
    return b


def test_stage2_detected_on_rising_zigzag():
    b = zigzag([20, 12, 15, 13, 16, 14, 17, 16.5])  # lows 12<13<14, highs 15<16<17
    hs, ls = s.pivots(b)
    st, last_low = s.stage_at(hs, ls, len(b) - 1)
    assert st == 2 and abs(last_low - 13.8) < 0.01


def test_falling_zigzag_is_stage0():
    b = zigzag([20, 17, 19, 15, 17, 13, 15, 12])
    hs, ls = s.pivots(b)
    assert s.stage_at(hs, ls, len(b) - 1)[0] == 0
