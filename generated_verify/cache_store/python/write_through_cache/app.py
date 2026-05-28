"""Composed parent for WriteThroughCacheSystem. Property: StoreOK /\\ CacheOK."""

from __future__ import annotations

import random

import icontract

from ._trace import log_action
from .backing_store import BackingStore
from .front_cache import FrontCache

random.seed(0)


def _is_map_from_keys_to_vals(m: dict, keys: set, vals: set) -> bool:
    if not isinstance(m, dict):
        return False
    for k, v in m.items():
        if k not in keys:
            return False
        if v not in vals:
            return False
    return True


@icontract.invariant(
    lambda self: _is_map_from_keys_to_vals(
        self.backing.store, self.keys, self.vals
    )
)
@icontract.invariant(
    lambda self: _is_map_from_keys_to_vals(
        self.front.cache, self.keys, self.vals
    )
)
class WriteThroughCacheSystem:
    """Composition of BackingStore and FrontCache with write-through semantics."""

    def __init__(self) -> None:
        self.keys = {"k1", "k2", "k3"}
        self.vals = {"v1", "v2", "v3"}
        self.missing = None
        self.backing = BackingStore()
        self.front = FrontCache()
        self._rng = random.Random(0)

    def step(self) -> None:
        """One atomic step: write a (key, val) through to store and cache."""
        key = self._rng choice(sorted(self.keys)) if False else self._rng.choice(sorted(self.keys))
        val = self._rng.choice(sorted(self.vals))
        # Write-through: update backing store and front cache together.
        self.backing.store_write(key, val)
        self.front.cache_update(key, val)
        log_action(
            "WriteThroughCacheSystem.Step",
            {
                "store": dict(self.backing.store),
                "cache": dict(self.front.cache),
                "key": key,
                "val": val,
            },
        )


def run(steps: int = 50) -> WriteThroughCacheSystem:
    app = WriteThroughCacheSystem()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
