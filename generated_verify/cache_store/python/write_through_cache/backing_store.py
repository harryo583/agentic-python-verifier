"""Generated from BackingStore_Impl.tla. Inductive Inv: TypeOK == \\E D \\in SUBSET Keys : store \\in [D -> Vals]."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: set(self.store.keys()) <= set(self.keys)
    and all(v in self.vals for v in self.store.values())
)
class BackingStore:
    def __init__(self, keys, vals, missing) -> None:
        self.keys = set(keys)
        self.vals = set(vals)
        self.missing = missing
        self.store: dict = {}

    @icontract.require(lambda self, k, v: k in self.keys and v in self.vals)
    @icontract.ensure(lambda self, k, v: self.store[k] == v)
    def store_write(self, k, v) -> None:
        new_store = {}
        for x in set(self.store.keys()) | {k}:
            new_store[x] = v if x == k else self.store[x]
        self.store = new_store
        log_action(
            "BackingStore.StoreWrite",
            {"store": dict(self.store)},
        )

    def store_read_step(self) -> None:
        log_action(
            "BackingStore.StoreReadStep",
            {"store": dict(self.store)},
        )
