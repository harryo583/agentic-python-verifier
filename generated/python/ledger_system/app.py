"""Composed parent for LedgerSystem. Property: SumBal = InitTotal /\\ \\A a \\in Accts : balances[a] >= 0 /\\ balances[a] <= Cap."""

from __future__ import annotations

import icontract

from ._trace import log_action
from .accounts import Accounts
from .audit_log import AuditLog


def _net_for(log: list[dict], a: str) -> int:
    total = 0
    for e in log:
        if e["to"] == a:
            total += e["amount"]
        if e["from"] == a:
            total -= e["amount"]
    return total


@icontract.invariant(
    lambda self: all(0 <= self.accounts.balances[a] <= self.accounts.cap for a in self.accounts.accts)
)
@icontract.invariant(
    lambda self: self.accounts.balances["A"] + self.accounts.balances["B"] == 2 * self.accounts.init0
)
@icontract.invariant(
    lambda self: len(self.audit.log) <= self.audit.max_log_len
)
@icontract.invariant(
    lambda self: all(
        self.accounts.balances[a] == self.accounts.init0 + _net_for(self.audit.log, a)
        for a in self.accounts.accts
    )
)
class LedgerSystem:
    def __init__(
        self,
        accts=("A", "B"),
        cap: int = 10,
        init0: int = 5,
        amounts=(1, 2, 3),
        max_log_len: int = 3,
    ) -> None:
        self.accounts = Accounts(accts=accts, cap=cap, init0=init0, amounts=amounts)
        self.audit = AuditLog(
            accts=frozenset(accts),
            amounts=frozenset(amounts),
            max_log_len=max_log_len,
        )
        # Deterministic schedule of (from, to, amount) transfers.
        self._schedule = [
            ("A", "B", 1),
            ("B", "A", 2),
            ("A", "B", 3),
            ("B", "A", 1),
            ("A", "B", 2),
            ("B", "A", 3),
        ]
        self._idx = 0

    def _can_transfer(self, f: str, t: str, amt: int) -> bool:
        if f == t:
            return False
        if f not in self.accounts.accts or t not in self.accounts.accts:
            return False
        if amt not in self.accounts.amounts:
            return False
        if self.accounts.balances[f] < amt:
            return False
        if self.accounts.balances[t] + amt > self.accounts.cap:
            return False
        if len(self.audit.log) >= self.audit.max_log_len:
            return False
        if self.accounts.pc != "Loop":
            return False
        if self.audit.pc != "Loop":
            return False
        return True

    def step(self) -> None:
        """One atomic composed transition: transfer + audit append, or stutter."""
        # Pick the next schedule entry that satisfies DoTransfer's guards.
        chosen = None
        for _ in range(len(self._schedule)):
            f, t, amt = self._schedule[self._idx % len(self._schedule)]
            self._idx += 1
            if self._can_transfer(f, t, amt):
                chosen = (f, t, amt)
                break

        if chosen is None:
            # Stutter step: UNCHANGED vars.
            log_action("LedgerSystem.Stutter", {
                "balances": dict(self.accounts.balances),
                "log": [dict(e) for e in self.audit.log],
            })
            return

        f, t, amt = chosen
        # Atomic composed action: mutate both children before returning.
        self.accounts.do_xfer(f, t, amt)
        self.audit.do_append(f, t, amt)
        log_action("LedgerSystem.Step", {
            "balances": dict(self.accounts.balances),
            "log": [dict(e) for e in self.audit.log],
        })


def run(steps: int = 50) -> LedgerSystem:
    app = LedgerSystem()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
