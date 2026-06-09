"""Composed parent for LedgerSystem. Property: SumBalances = 10 /\\ \\A a \\in Accts: balances[a] >= 0 /\\ balances[a] <= Cap /\\ AuditIntegrity."""

from __future__ import annotations

import icontract

from ._trace import log_action
from .accounts import Accounts
from .audit_log import AuditLog


def _credits_to(log, a):
    return sum(e["amount"] for e in log if e["to"] == a)


def _debits_from(log, a):
    return sum(e["amount"] for e in log if e["from"] == a)


@icontract.invariant(lambda self: self.accounts.balances["A"] + self.accounts.balances["B"] == 10)
@icontract.invariant(
    lambda self: all(
        0 <= self.accounts.balances[a] <= self.accounts.cap for a in self.accounts.accts
    )
)
@icontract.invariant(lambda self: len(self.audit.log) <= self.audit.max_log_len)
@icontract.invariant(
    lambda self: all(
        5 + _credits_to(self.audit.log, a) - _debits_from(self.audit.log, a)
        == self.accounts.balances[a]
        for a in self.accounts.accts
    )
)
class LedgerSystem:
    def __init__(
        self,
        accts: tuple[str, ...] = ("A", "B"),
        cap: int = 10,
        amounts: tuple[int, ...] = (1, 2, 3),
        max_log_len: int = 4,
    ) -> None:
        self.accounts = Accounts(accts=accts, cap=cap, amounts=amounts)
        self.audit = AuditLog(accts=accts, amounts=amounts, max_log_len=max_log_len)
        self._tick = 0

    def step(self) -> None:
        """One atomic composed Transfer: update balances AND append audit entry."""
        if self.accounts.pc != "Loop" or self.audit.pc != "Loop":
            return
        if len(self.audit.log) >= self.audit.max_log_len:
            return

        # Deterministic transfer selection: alternate direction, amount=1.
        accts = self.accounts.accts
        if self._tick % 2 == 0:
            frm, to = accts[0], accts[1]
        else:
            frm, to = accts[1], accts[0]
        amt = 1

        # Guard against child preconditions.
        if self.accounts.balances[frm] < amt:
            frm, to = to, frm
        if self.accounts.balances[to] + amt > self.accounts.cap:
            return

        self.accounts.transfer(frm, to, amt)
        self.audit.append_entry(frm, to, amt)
        self._tick += 1
        log_action(
            "LedgerSystem.Step",
            {
                "balances": dict(self.accounts.balances),
                "log": [dict(e) for e in self.audit.log],
            },
        )


def run(steps: int = 50) -> LedgerSystem:
    app = LedgerSystem()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
