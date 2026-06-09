"""Generated from Accounts_Impl.tla. Inductive Inv: TypeOK /\\ SumBal = 10 /\\ pc \\in {"Loop","Finish","Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(
        a in self.balances and 0 <= self.balances[a] <= self.cap for a in self.accts
    )
    and set(self.balances.keys()) == set(self.accts)
)
@icontract.invariant(lambda self: self.balances["A"] + self.balances["B"] == 10)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class Accounts:
    def __init__(
        self,
        accts: tuple[str, ...] = ("A", "B"),
        cap: int = 10,
        amounts: tuple[int, ...] = (1, 2, 3),
    ) -> None:
        self.accts = tuple(accts)
        self.cap = cap
        self.amounts = tuple(amounts)
        self.balances = {a: 5 for a in self.accts}
        self.pc = "Loop"

    @icontract.require(lambda self, frm, to, amt: frm in self.accts and to in self.accts)
    @icontract.require(lambda self, frm, to, amt: amt in self.amounts)
    @icontract.require(lambda self, frm, to, amt: frm != to)
    @icontract.require(lambda self, frm, to, amt: self.balances[frm] >= amt)
    @icontract.require(lambda self, frm, to, amt: self.balances[to] + amt <= self.cap)
    @icontract.require(lambda self: self.pc == "Loop")
    def transfer(self, frm: str, to: str, amt: int) -> None:
        self.balances[frm] -= amt
        self.balances[to] += amt
        log_action(
            "Accounts.TransferStep",
            {"balances": dict(self.balances)},
        )

    def finish(self) -> None:
        # Stutter: move from Loop to Finish without changing abs vars.
        if self.pc == "Loop":
            self.pc = "Finish"

    def done(self) -> None:
        # Stutter: move from Finish to Done without changing abs vars.
        if self.pc == "Finish":
            self.pc = "Done"
