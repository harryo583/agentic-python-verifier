"""Generated from Store_Impl.tla. Inductive Inv: IsPartialFn(store, Keys, Vals)."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: set(self.store.keys()) <= set(self.keys))
@icontract.invariant(lambda self: all(v in self.vals for v in self.store.values()))
class Store:
    def __init__(self, keys=None, vals=None, no_val=None) -> None:
        self.keys = list(keys) if keys is not None else [1, 2, 3]
        self.vals = list(vals) if vals is not None else [10, 20, 30]
        self.no_val = no_val if no_val is not None else 0
        self.store: dict = {}

    @icontract.require(lambda self, k, v: k in self.keys and v in self.vals)
    @icontract.ensure(lambda self, k, v: self.store[k] == v)
    def write_store(self, k, v) -> None:
        self.store[k] = v
        log_action(
            "Store.WriteStore",
            {"store": dict(self.store)},
        )

    def read_store(self) -> None:
        # Stutter w.r.t. abs vars (UNCHANGED store): do not log.
        pass
