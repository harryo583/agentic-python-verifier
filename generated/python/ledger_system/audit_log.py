"""Generated from AuditLog_Impl.tla. Inductive Inv: TypeOK /\\ WellFormed /\\ pc \\in {"Loop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: isinstance(self.log, list) and len(self.log) <= self.max_log_len)
@icontract.invariant(
    lambda self: all(
        isinstance(e, dict)
        and set(e.keys()) == {"from", "to", "amount"}
        and e["from"] in self.accts
        and e["to"] in self.accts
        and e["amount"] in self.amounts
        for e in self.log
    )
)
@icontract.invariant(
    lambda self: all(
        e["amount"] in self.amounts and e["from"] != e["to"] for e in self.log
    )
)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class AuditLog:
    def __init__(self, accts, amounts, max_log_len: int) -> None:
        self.accts = set(accts)
        self.amounts = set(amounts)
        self.max_log_len = max_log_len
        self.log: list[dict] = []
        self.pc = "Loop"

    @icontract.require(lambda self, frm, to, amt: frm in self.accts and to in self.accts)
    @icontract.require(lambda self, frm, to, amt: amt in self.amounts)
    @icontract.require(lambda self, frm, to, amt: frm != to)
    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.require(lambda self: len(self.log) < self.max_log_len)
    @icontract.ensure(lambda self: self.pc == "Loop")
    def append_entry(self, frm, to, amt) -> None:
        self.log = self.log + [{"from": frm, "to": to, "amount": amt}]
        log_action(
            "AuditLog.Append1",
            {"log": [dict(e) for e in self.log]},
        )

    def finish(self) -> None:
        if self.pc == "Loop":
            self.pc = "Finish"
        # stutter: do not log; abs var `log` unchanged

    def done(self) -> None:
        if self.pc == "Finish":
            self.pc = "Done"
        # stutter: do not log; abs var `log` unchanged
