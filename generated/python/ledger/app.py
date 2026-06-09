"""Composed parent for Ledger. Property: Conservation /\\ BoundsOK /\\ AuditIntegrity."""

from __future__ import annotations

import icontract

from ._trace import log_action
from .accounts import Accounts
from .audit_log import AuditLog


def _credited_to(log, x):
    return sum(e[2] for e in log if e[1] == x)


def _debited_from(log, x):
    return sum(e[2] for e in log if e[0] == x)


@icontract.invariant(
    lambda self: all(0 <= self.accounts.balances[a] <= self.accounts.cap for a in self.accounts.accts)
)
@icontract.invariant(
    lambda self: self.accounts.balances["A"] + self.accounts.balances["B"] == 10
)
@icontract.invariant(
    lambda self: all(
        self.accounts.balances[x] - 5
        == _credited_to(self.audit.log, x) - _debited_from(self.audit.log, x)
        for x in self.accounts.accts
    )
)
class Ledger:
    def __init__(self) -> None:
        accts = ["A", "B"]
        amounts = [1, 2, 3]
        self.accounts = Accounts(accts=accts, amounts=amounts, cap=10)
        self.audit = AuditLog(accts=accts, amounts=amounts, max_len=3)
        # Deterministic schedule of (from, to, amount) transfers.
        self._schedule = [
            ("A", "B", 1),
            ("B", "A", 1),
            ("A", "B", 2),
        ]
        self._idx = 0

    def step(self) -> None:
        """One atomic composed transfer: debit `f`, credit `t`, append log entry."""
        # If audit log is full, we cannot perform another logged transfer.
        if len(self.audit.log) >= self.audit.max_len:
            return
        if self._idx >= len(self._schedule):
            return

        f, t, n = self._schedule[self._idx]
        self._idx += 1

        # Guard preconditions; skip if not satisfiable.
        if self.accounts.balances[f] < n:
            return
        if self.accounts.balances[t] + n > self.accounts.cap:
            return

        # Atomic composed action: debit, credit, log.
        self.accounts.debit(f, n)
        self.accounts.credit(t, n)
        self.audit.append1(f, t, n)

        log_action(
            "Ledger.Step",
            {
                "balances": dict(self.accounts.balances),
                "log": list(self.audit.log),
            },
        )


def run(steps: int = 50) -> Ledger:
    app = Ledger()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
