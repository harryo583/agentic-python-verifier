"""Generated from Store_Impl.tla. Inductive Inv:
  /\\ store \\in [Keys -> Values \\cup {Missing}]
  /\\ pc \\in {"Loop", "Finish", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(
        k in self.store and (self.store[k] in self.values or self.store[k] == self.missing)
        for k in self.keys
    )
    and set(self.store.keys()) == set(self.keys)
)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class Store:
    def __init__(self, keys, values, missing) -> None:
        self.keys = list(keys)
        self.values = list(values)
        self.missing = missing
        self.store = {k: missing for k in self.keys}
        self.pc = "Loop"

    @icontract.require(lambda self, k, v: k in self.keys and v in self.values)
    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.ensure(lambda self, k, v: self.store[k] == v)
    def write(self, k, v) -> None:
        self.store[k] = v
        log_action(
            "Store.Write",
            {"store": dict(self.store)},
        )

    @icontract.require(lambda self: self.pc == "Loop")
    def read_noop(self) -> None:
        # Stutter: no mutation to abs vars, do not log.
        pass

    @icontract.require(lambda self: self.pc in {"Loop", "Finish"})
    def finish(self) -> None:
        # Internal pc progression; no abs-var change, no log_action.
        if self.pc == "Loop":
            self.pc = "Finish"
        else:
            self.pc = "Done"
