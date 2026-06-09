"""Generated from KVStore_Impl.tla. Inductive Inv: StoreBounded /\\ pc \\in {"Loop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: all(k in self.keys for k in self.store))
@icontract.invariant(lambda self: all(v in self.values for v in self.store.values()))
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class KVStore:
    def __init__(self, keys: frozenset, values: frozenset, missing=None) -> None:
        self.keys = frozenset(keys)
        self.values = frozenset(values)
        self.missing = missing
        self.store: dict = {}
        self.pc = "Loop"

    @icontract.require(lambda self, k, v: k in self.keys and v in self.values)
    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.ensure(lambda self, k, v: self.store.get(k) == v)
    def put(self, k, v) -> None:
        new_store = dict(self.store)
        new_store[k] = v
        self.store = new_store
        log_action(
            "KVStore.Put",
            {"store": dict(self.store)},
        )

    def get(self, k):
        if k in self.store:
            return self.store[k]
        return self.missing

    def finish(self) -> None:
        # Stutter transition: pc changes from Loop to Finish but abs vars unchanged.
        if self.pc == "Loop":
            self.pc = "Finish"

    def done(self) -> None:
        # Stutter transition: pc changes from Finish to Done but abs vars unchanged.
        if self.pc == "Finish":
            self.pc = "Done"
