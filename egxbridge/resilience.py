from __future__ import annotations

import random
import time
import logging
from typing import Callable, TypeVar

T = TypeVar("T")
log = logging.getLogger("egxbridge")


class CircuitBreaker:
    """CLOSED → OPEN → HALF-OPEN → CLOSED.

    Defaults: fail_threshold=3, cooldown=60s, one HALF-OPEN probe.
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, fail_threshold: int = 3, cool_down_seconds: float = 60):
        self.fail_threshold = int(fail_threshold)
        self.cool_down_seconds = float(cool_down_seconds)
        self.failures = 0
        self.state = self.CLOSED
        self.open_until = 0.0
        self._half_open_probe_used = False

    def allow(self) -> bool:
        now = time.time()
        if self.state == self.CLOSED:
            return True
        if self.state == self.OPEN:
            if now < self.open_until:
                return False
            # Cooldown elapsed → enter HALF-OPEN for a single probe.
            self.state = self.HALF_OPEN
            self._half_open_probe_used = False
        if self.state == self.HALF_OPEN:
            if self._half_open_probe_used:
                return False
            self._half_open_probe_used = True
            return True
        return False

    def record_success(self):
        self.failures = 0
        self.state = self.CLOSED
        self.open_until = 0.0
        self._half_open_probe_used = False

    def record_failure(self):
        self.failures += 1
        # HALF-OPEN probe failed → reopen. CLOSED failures → open at threshold.
        if self.state == self.HALF_OPEN or self.failures >= self.fail_threshold:
            self.state = self.OPEN
            self.open_until = time.time() + self.cool_down_seconds
            self._half_open_probe_used = False

    @property
    def is_open(self) -> bool:
        self.allow()  # transition OPEN→HALF_OPEN when due
        return self.state == self.OPEN


def retry_call(
    fn: Callable[[], T],
    *,
    retries: int = 2,
    base_delay: float = 0.5,
    jitter: float = 0.2,
    retry_on: tuple = (Exception,),
) -> T:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except retry_on as e:
            last_exc = e
            if attempt >= retries:
                break
            delay = base_delay * (2 ** attempt) + random.uniform(0, jitter)
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


class RateLimiter:
    def __init__(self, min_interval_seconds: float = 0.5):
        self.min_interval = min_interval_seconds
        self._last = 0.0

    def wait(self):
        now = time.time()
        delta = now - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.time()
