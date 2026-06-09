"""Composed parent for WriteThroughCache. Property: Coherent /\\ StoreWellFormed /\\ CacheWellFormed."""

from __future__ import annotations

import random

import icontract

from ._trace import log_action
from .store import Store
from .cache import Cache

random.seed(0)


@icontract.invariant(lambda self: set(self.store.store.keys()) <= set(self.store.keys))
@icontract.invariant(lambda self: all(v in self.store.vals for v in self.store.store.values()))
@icontract.invariant(lambda self: set(self.cache.cache.keys()) <= set(self.cache.keys))
@icontract.invariant(lambda self: all(v in self.cache.vals for v in self.cache.cache.values()))
@icontract.invariant(
    lambda self: all(
        k in self.store.store and self.cache.cache[k] == self.store.store[k]
        for k in self.cache.cache
    )
)
class WriteThroughCache:
    def __init__(self) -> None:
        keys = ["a", "b", "c"]
        vals = [0, 1, 2, 3, 4, 5]
        no_val = ["NoVal"]
        self.store = Store(keys=keys, vals=vals, no_val=no_val)
        self.cache = Cache(keys=keys, vals=vals, no_val=no_val)
        self._keys = keys
        self._vals = vals
        self._tick = 0

    def write_through(self, k, v) -> None:
        """Atomic WriteThrough(k, v): update store and cache together."""
        self.store.write_store(k, v)
        self.cache.fill(k, v)
        log_action(
            "WriteThroughCache.WriteThrough",
            {"k": k, "v": v, "store": dict(self.store.store), "cache": dict(self.cache.cache)},
        )

    def read_hit(self, k) -> None:
        # No mutation; stutter on abstract vars.
        log_action(
            "WriteThroughCache.ReadHit",
            {"k": k, "store": dict(self.store.store), "cache": dict(self.cache.cache)},
        )

    def read_miss(self, k) -> None:
        """ReadMiss(k): k in store but not in cache; fill cache from store."""
        self.cache.fill(k, self.store.store[k])
        log_action(
            "WriteThroughCache.ReadMiss",
            {"k": k, "store": dict(self.store.store), "cache": dict(self.cache.cache)},
        )

    def read_absent(self, k) -> None:
        log_action(
            "WriteThroughCache.ReadAbsent",
            {"k": k, "store": dict(self.store.store), "cache": dict(self.cache.cache)},
        )

    def step(self) -> None:
        """One atomic step of the composed system, deterministic given fixed seed."""
        # Deterministic schedule cycling through actions.
        t = self._tick
        self._tick += 1
        k = self._keys[t % len(self._keys)]

        phase = t % 5
        if phase == 0 or phase == 1:
            # Write-through write.
            v = self._vals[t % len(self._vals)]
            self.write_through(k, v)
        elif phase == 2:
            # Read: hit if in cache, miss if in store only, absent otherwise.
            if k in self.cache.cache:
                self.read_hit(k)
            elif k in self.store.store:
                self.read_miss(k)
            else:
                self.read_absent(k)
        elif phase == 3:
            # Try a different key to exercise miss/absent paths.
            k2 = self._keys[(t + 1) % len(self._keys)]
            if k2 in self.cache.cache:
                self.read_hit(k2)
            elif k2 in self.store.store:
                self.read_miss(k2)
            else:
                self.read_absent(k2)
        else:
            # Another write-through to keep things lively.
            v = self._vals[(t * 3) % len(self._vals)]
            self.write_through(k, v)

        log_action(
            "WriteThroughCache.Step",
            {"tick": t, "store": dict(self.store.store), "cache": dict(self.cache.cache)},
        )


def run(steps: int = 50) -> WriteThroughCache:
    app = WriteThroughCache()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
