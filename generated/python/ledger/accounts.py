"""Generated from Accounts_Impl.tla. Inductive Inv: balances \\in [Accts -> 0..Cap] /\\ pc \\in {"Loop","Finish","Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: all(0 <= self.balances[a] <= self.cap for a in self.accts))
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class Accounts:
    def __init__(self, accts, amounts, cap) -> None:
        self.accts = set(accts)
        self.amounts = set(amounts)
        self.cap = cap
        self.balances = {a: 5 for a in self.accts}
        self.pc = "Loop"

    @icontract.require(lambda self, x, n: x in self.accts and n in self.amounts)
    @icontract.require(lambda self, x, n: self.balances[x] >= n)
    @icontract.ensure(lambda self: self.pc == "Loop")
    def debit(self, x, n) -> None:
        self.balances[x] = self.balances[x] - n
        self.pc = "Loop"
        log_action(
            "Accounts.Debit",
            {"balances": dict(self.balances)},
        )

    @icontract.require(lambda self, x, n: x in self.accts and n in self.amounts)
    @icontract.require(lambda self, x, n: self.balances[x] + n <= self.cap)
    @icontract.ensure(lambda self: self.pc == "Loop")
    def credit(self, x, n) -> None:
        self.balances[x] = self.balances[x] + n
        self.pc = "Loop"
        log_action(
            "Accounts.Credit",
            {"balances": dict(self.balances)},
        )
