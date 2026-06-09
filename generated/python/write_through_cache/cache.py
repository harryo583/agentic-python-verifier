"""Generated from Cache_Impl.tla. Inductive Inv: IsPartialFn(cache, Keys, Vals)."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: set(self.cache.keys()) <= set(self.keys)
    and all(v in self.vals for v in self.cache.values())
)
class Cache:
    def __init__(self, keys, vals, no_val=None) -> None:
        self.keys = set(keys)
        self.vals = set(vals)
        self.no_val = no_val
        self.cache: dict = {}

    @icontract.require(lambda self, k, v: k in self.keys and v in self.vals)
    def fill(self, k, v) -> None:
        new_cache = dict(self.cache)
        new_cache[k] = v
        self.cache = new_cache
        log_action("Cache.Fill", {"cache": dict(self.cache)})

    @icontract.require(lambda self, k, v: k in self.keys and v in self.vals)
    def update(self, k, v) -> None:
        new_cache = dict(self.cache)
        new_cache[k] = v
        self.cache = new_cache
        log_action("Cache.Update", {"cache": dict(self.cache)})

    @icontract.require(lambda self, k: k in self.keys)
    def invalidate(self, k) -> None:
        new_cache = {j: val for j, val in self.cache.items() if j != k}
        self.cache = new_cache
        log_action("Cache.Invalidate", {"cache": dict(self.cache)})

    def lookup(self) -> None:
        # Stutter step on abs vars: UNCHANGED cache. Do not log_action.
        pass
