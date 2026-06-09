"""Generated from RM2_Impl.tla. Inductive Inv: rm2State \\in States /\\ pc \\in {"RMLoop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: self.rm2State in self.States)
@icontract.invariant(lambda self: self.pc in {"RMLoop", "Finish", "Done"})
class RM2:
    def __init__(self, states: frozenset[str] | set[str] | None = None) -> None:
        self.States = frozenset(states) if states is not None else frozenset(
            {"working", "prepared", "committed", "aborted"}
        )
        self.rm2State = "working"
        self.pc = "RMLoop"

    @icontract.require(lambda self: self.rm2State == "working")
    @icontract.ensure(lambda self: self.rm2State == "prepared")
    def prepare(self) -> None:
        self.rm2State = "prepared"
        log_action("RM2.Prepare", {"rm2State": self.rm2State})

    @icontract.require(lambda self: self.rm2State == "prepared")
    @icontract.ensure(lambda self: self.rm2State == "committed")
    def apply_commit(self) -> None:
        self.rm2State = "committed"
        log_action("RM2.ApplyCommit", {"rm2State": self.rm2State})

    @icontract.require(lambda self: self.rm2State in {"working", "prepared"})
    @icontract.ensure(lambda self: self.rm2State == "aborted")
    def apply_abort(self) -> None:
        self.rm2State = "aborted"
        log_action("RM2.ApplyAbort", {"rm2State": self.rm2State})
