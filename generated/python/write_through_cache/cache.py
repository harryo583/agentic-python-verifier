"""Generated from Cache_Impl.tla. Inductive Inv:
  /\\ cache \\in [Keys -> Values \\cup {Missing}]
  /\\ pc \\in {"Loop", "Finish", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(
        k in self.cache and (self.cache[k] in self.values or self.cache[k] == self.missing)
        for k in self.keys
    )
    and set(self.cache.keys()) == set(self.keys)
)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class Cache:
    def __init__(self, keys, values, missing="__MISSING__") -> None:
        self.keys = list(keys)
        self.values = list(values)
        self.missing = missing
        self.cache = {k: missing for k in self.keys}
        self.pc = "Loop"

    @icontract.require(lambda self, k, v: k in self.keys and v in self.values)
    @icontract.require(lambda self: self.pc == "Loop")
    def put(self, k, v) -> None:
        self.cache[k] = v
        log_action("Cache.Put", {"cache": dict(self.cache)})

    @icontract.require(lambda self, k: k in self.keys)
    @icontract.require(lambda self: self.pc == "Loop")
    def evict(self, k) -> None:
        self.cache[k] = self.missing
        log_action("Cache.Evict", {"cache": dict(self.cache)})

    @icontract.require(lambda self: self.pc in {"Loop", "Finish"})
    def noop(self) -> None:
        # Stutter step: do not log_action; abs vars unchanged.
        if self.pc == "Loop":
            # allow transitioning to Finish without changing cache
            self.pc = "Finish"
        elif self.pc == "Finish":
            self.pc = "Done"
