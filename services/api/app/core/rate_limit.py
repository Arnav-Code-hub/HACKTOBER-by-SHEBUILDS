"""Small process-local sliding window, not a distributed quota."""

from collections import OrderedDict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic
from uuid import UUID

from app.core.errors import RateLimitError


class SuggestionRateLimiter:
    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self.clock = clock
        self._requests: OrderedDict[UUID, deque[float]] = OrderedDict()
        self._lock = Lock()

    def check(self, user_id: UUID) -> None:
        with self._lock:
            now = self.clock()
            cutoff = now - 60
            # Ordered by each user's latest admitted request; expired identities
            # are removed too, so this does not retain every historical user.
            while self._requests and next(iter(self._requests.values()))[-1] <= cutoff:
                self._requests.popitem(last=False)
            requests = self._requests.get(user_id, deque())
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= 10:
                raise RateLimitError("Too many suggestion requests; wait a minute.")
            requests.append(now)
            self._requests[user_id] = requests
            self._requests.move_to_end(user_id)
