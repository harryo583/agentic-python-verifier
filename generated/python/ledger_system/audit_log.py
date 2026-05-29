"""Generated from AuditLog_Impl.tla. Inductive Inv: TypeOK /\\ WellFormed /\\ pc \\in {"Loop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: len(self.log) <= self.max_log_len)
@icontract.invariant(
    lambda self: all(
        (entry["from"] in self.accts)
        and (entry["to"] in self.accts)
        and (entry["amount"] in self.amounts)
        for entry in self.log
    )
)
@icontract.invariant(
    lambda self: all(
        (entry["from"] != entry["to"]) and (entry["amount"] > 0)
        for entry in self.log
    )
)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class AuditLog:
    def __init__(
        self,
        accts: frozenset[str] = frozenset({"a", "b", "c"}),
        amounts: frozenset[int] = frozenset({1, 2, 3}),
        max_log_len: int = 5,
    ) -> None:
        self.accts = frozenset(accts)
        self.amounts = frozenset(amounts)
        self.max_log_len = max_log_len
        self.log: list[dict] = []
        self.pc = "Loop"

    @icontract.require(lambda self, f, t, amt: f in self.accts)
    @icontract.require(lambda self, f, t, amt: t in self.accts)
    @icontract.require(lambda self, f, t, amt: amt in self.amounts)
    @icontract.require(lambda self, f, t, amt: f != t)
    @icontract.require(lambda self, f, t, amt: amt > 0)
    @icontract.ensure(lambda self: self.pc in {"Loop", "Finish", "Done"})
    def do_append(self, f: str, t: str, amt: int) -> None:
        if self.pc == "Loop" and len(self.log) < self.max_log_len:
            self.log = self.log + [{"from": f, "to": t, "amount": amt}]
            log_action(
                "AuditLog.DoAppend",
                {"log": [dict(e) for e in self.log]},
            )

    @icontract.ensure(lambda self: self.pc in {"Loop", "Finish", "Done"})
    def finish(self) -> None:
        # Stutter: transition Loop -> Finish -> Done does not change abs vars.
        if self.pc == "Loop":
            self.pc = "Finish"
        elif self.pc == "Finish":
            self.pc = "Done"
