"""Sliding-window limiter tests."""

from app.services.rate_limit import SlidingWindowLimiter


def test_limiter_window_and_keys():
    now = [0.0]
    limiter = SlidingWindowLimiter(2, 60, clock=lambda: now[0])
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
    now[0] = 61
    assert limiter.allow("a")
