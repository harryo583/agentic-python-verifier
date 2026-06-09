"""Generated from BackingStore_Impl.tla. Inductive Inv: TypeOK /\\ pc \\in {"Loop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: isinstance(self.store, dict) and set(self.store.keys()) == set(self.keys) and all(isinstance(self.store[k], set) and self.store[k] <= set(self.values) for k in self.keys))
@icontract.invariant(lambda self: all(len(self.store[k]) <= 1 for k in self.keys))
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class BackingStore:
    def __init__(self, keys, values) -> None:
        self.keys = list(keys)
        self.values = list(values)
        self.store = {k: set() for k in self.keys}
        self.pc = "Loop"

    @icontract.require(lambda self, k, v: k in self.keys and v in self.values)
    @icontract.ensure(lambda self, k, v: self.store[k] == {v})
    def store_put(self, k, v) -> None:
        if self.pc == "Loop":
            self.store[k] = {v}
            log_action(
                "BackingStore.StorePut",
                {"store": {kk: set(vv) for kk, vv in self.store.items()}},
            )

    def store_noop(self) -> None:
        # Stutter step - no log_action emitted.
        return None

    def finish(self) -> None:
        # Internal transition Loop -> Finish -> Done; abs vars unchanged, so no log_action.
        if self.pc == "Loop":
            self.pc = "Finish"
        elif self.pc == "Finish":
            self.pc = "Done"
