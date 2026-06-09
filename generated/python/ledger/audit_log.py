"""Generated from AuditLog_Impl.tla. Inductive Inv: log \\in BoundedSeqs /\\ pc \\in {"Loop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: isinstance(self.log, list) and len(self.log) <= self.max_len)
@icontract.invariant(
    lambda self: all(
        isinstance(e, tuple)
        and len(e) == 3
        and e[0] in self.accts
        and e[1] in self.accts
        and e[2] in self.amounts
        for e in self.log
    )
)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class AuditLog:
    def __init__(self, accts, amounts, max_len: int) -> None:
        self.accts = frozenset(accts)
        self.amounts = frozenset(amounts)
        self.max_len = max_len
        self.log: list[tuple] = []
        self.pc = "Loop"

    @icontract.require(lambda self, f, t, n: f in self.accts)
    @icontract.require(lambda self, f, t, n: t in self.accts)
    @icontract.require(lambda self, f, t, n: n in self.amounts)
    @icontract.require(lambda self, f, t, n: len(self.log) < self.max_len)
    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.ensure(lambda self: len(self.log) <= self.max_len)
    def append1(self, f, t, n) -> None:
        self.log = self.log + [(f, t, n)]
        log_action(
            "AuditLog.Append1",
            {"log": list(self.log)},
        )

    def finish(self) -> None:
        # Stutter: pc transition only; no abs-var change, no log_action.
        if self.pc == "Loop":
            self.pc = "Finish"
        elif self.pc == "Finish":
            self.pc = "Done"
