"""Generated from FrontCache_Impl.tla. Inductive Inv: TypeOK."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: isinstance(self.cache, dict)
    and set(self.cache.keys()) <= set(self.Keys)
    and all(v in self.Vals for v in self.cache.values())
)
class FrontCache:
    def __init__(self, Keys, Vals, Missing) -> None:
        self.Keys = set(Keys)
        self.Vals = set(Vals)
        self.Missing = Missing
        self.cache: dict = {}

    @icontract.require(lambda self, k, v: k in self.Keys and v in self.Vals)
    def cache_update(self, k, v) -> None:
        new_cache = {}
        for x in set(self.cache.keys()) | {k}:
            new_cache[x] = v if x == k else self.cache[x]
        self.cache = new_cache
        log_action("FrontCache.CacheUpdate", {"cache": dict(self.cache)})

    @icontract.require(lambda self, k: k in self.Keys)
    def cache_invalidate(self, k) -> None:
        new_cache = {x: self.cache[x] for x in self.cache.keys() if x != k}
        self.cache = new_cache
        log_action("FrontCache.CacheInvalidate", {"cache": dict(self.cache)})

    def cache_lookup_step(self) -> None:
        log_action("FrontCache.CacheLookupStep", {"cache": dict(self.cache)})
