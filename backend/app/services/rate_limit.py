"""In-memory request limiter."""

from collections import defaultdict, deque
import threading
import time
from collections.abc import Callable


class SlidingWindowLimiter:
    """Thread-safe bounded sliding-window limiter."""

    def __init__(self, limit: int, window_sec: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window_sec = window_sec
        self.clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window_sec:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            if not hits:
                self._hits.pop(key, None)
            return True
