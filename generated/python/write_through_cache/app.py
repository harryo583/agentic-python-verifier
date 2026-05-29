"""Composed parent for WriteThroughCache. Property:
  /\\ \\A k \\in Keys : Read(k) \\in Values \\cup {Missing}
  /\\ \\A k \\in Keys : (cache[k] # Missing) => (Read(k) = store[k])
"""

from __future__ import annotations

import random

import icontract

from ._trace import log_action
from .store import Store
from .cache import Cache

random.seed(0)

_KEYS = ["a", "b", "c"]
_VALUES = [0, 1, 2, 3, 4, 5]
_MISSING = 999


@icontract.invariant(
    lambda self: all(
        k in self.store.store
        and (self.store.store[k] in self.store.values or self.store.store[k] == self.store.missing)
        for k in self.store.keys
    )
)
@icontract.invariant(
    lambda self: all(
        k in self.cache.cache
        and (self.cache.cache[k] in self.cache.values or self.cache.cache[k] == self.cache.missing)
        for k in self.cache.keys
    )
)
@icontract.invariant(
    lambda self: all(
        self.cache.cache[k] == self.cache.missing
        or self.cache.cache[k] == self.store.store[k]
        for k in self.cache.keys
    )
)
@icontract.invariant(lambda self: self.store.pc in {"Loop", "Finish", "Done"})
@icontract.invariant(lambda self: self.cache.pc in {"Loop", "Finish", "Done"})
class WriteThroughCache:
    def __init__(self) -> None:
        self.store = Store(keys=_KEYS, values=_VALUES, missing=_MISSING)
        self.cache = Cache(keys=_KEYS, values=_VALUES, missing=_MISSING)
        self._tick = 0

    def read(self, k):
        if self.cache.cache[k] != self.cache.missing:
            return self.cache.cache[k]
        return self.store.store[k]

    def step(self) -> None:
        """One atomic step of the composed system.

        Picks either a Store action (S!Next with cache unchanged) or a
        Cache action (C!Next with store unchanged). To preserve the joint
        invariant CacheAgreesWithStore, cache puts only mirror the
        store's current value at that key (or evict).
        """
        self._tick += 1
        keys = list(self.store.keys)

        # Alternate between store-side and cache-side transitions so that
        # both children make progress while keeping each step atomic and
        # joint-invariant-preserving.
        if self._tick % 2 == 1:
            # Store-side transition (UNCHANGED cache, pcC).
            if self.store.pc == "Loop":
                # Write a value into the store. We must keep
                # CacheAgreesWithStore: if cache[k] is not missing then it
                # must equal store[k] after the write. Safest choice: evict
                # the cache entry first would be a cache-side action, so
                # instead pick a key whose cache slot is already missing,
                # or write a value matching the current cache slot.
                k_idx = (self._tick // 2) % len(keys)
                k = keys[k_idx]
                if self.cache.cache[k] != self.cache.missing:
                    # Write the same value the cache already holds to
                    # preserve agreement.
                    v = self.cache.cache[k]
                else:
                    v = self._tick % len(self.store.values)
                self.store.write(k, v)
            else:
                self.store.finish()
        else:
            # Cache-side transition (UNCHANGED store, pcS).
            if self.cache.pc == "Loop":
                # Put the store's current value into the cache for some
                # key (write-through fill), which trivially satisfies
                # CacheAgreesWithStore.
                k_idx = (self._tick // 2) % len(keys)
                k = keys[k_idx]
                v = self.store.store[k]
                if v in self.cache.values:
                    self.cache.put(k, v)
                else:
                    # store[k] is Missing; evict cache[k] to keep agreement.
                    self.cache.evict(k)
            else:
                self.cache.noop()

        log_action(
            "WriteThroughCache.Step",
            {
                "store": dict(self.store.store),
                "cache": dict(self.cache.cache),
                "pcS": self.store.pc,
                "pcC": self.cache.pc,
            },
        )


def run(steps: int = 50) -> WriteThroughCache:
    app = WriteThroughCache()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
