"""Generated from Accounts_Impl.tla. Inductive Inv: TypeOK /\\ SumBal = 2 * Init0 /\\ pc \\in {"Loop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: all(a in self.balances for a in self.accts) and all(0 <= self.balances[a] <= self.cap for a in self.accts))
@icontract.invariant(lambda self: self.balances["A"] + self.balances["B"] == 2 * self.init0)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class Accounts:
    def __init__(self, accts=("A", "B"), cap: int = 10, init0: int = 5, amounts=(1, 2, 3)) -> None:
        self.accts = tuple(accts)
        self.cap = cap
        self.init0 = init0
        self.amounts = tuple(amounts)
        self.balances = {a: init0 for a in self.accts}
        self.pc = "Loop"

    @icontract.require(lambda self, f, t, amt: f in self.accts and t in self.accts and f != t)
    @icontract.require(lambda self, f, t, amt: amt in self.amounts)
    @icontract.require(lambda self, f, t, amt: self.balances[f] >= amt)
    @icontract.require(lambda self, f, t, amt: self.balances[t] + amt <= self.cap)
    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.ensure(lambda self: self.pc == "Loop")
    def do_xfer(self, f: str, t: str, amt: int) -> None:
        new_balances = dict(self.balances)
        new_balances[f] = new_balances[f] - amt
        new_balances[t] = new_balances[t] + amt
        self.balances = new_balances
        log_action(
            "Accounts.DoXfer",
            {"balances": dict(self.balances)},
        )

    def finish(self) -> None:
        if self.pc == "Loop":
            self.pc = "Finish"
        # stutter: no abs-var change, no log_action

    def done(self) -> None:
        if self.pc == "Finish":
            self.pc = "Done"
        # stutter: no abs-var change, no log_action
