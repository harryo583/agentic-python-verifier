"""Generated from RM1_Impl.tla. Inductive Inv: rm1State \\in States /\\ pc \\in {"RMLoop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: self.rm1State in self.States)
@icontract.invariant(lambda self: self.pc in {"RMLoop", "Finish", "Done"})
class RM1:
    def __init__(self, States: frozenset[str] | set[str] | None = None) -> None:
        self.States = set(States) if States is not None else {
            "working",
            "prepared",
            "committed",
            "aborted",
        }
        self.rm1State = "working"
        self.pc = "RMLoop"

    @icontract.require(lambda self: self.pc == "RMLoop" and self.rm1State == "working")
    @icontract.ensure(lambda self: self.rm1State == "prepared")
    def prepare(self) -> None:
        self.rm1State = "prepared"
        log_action("RM1.Prepare", {"rm1State": self.rm1State})

    @icontract.require(lambda self: self.pc == "RMLoop" and self.rm1State == "prepared")
    @icontract.ensure(lambda self: self.rm1State == "committed")
    def apply_commit(self) -> None:
        self.rm1State = "committed"
        log_action("RM1.ApplyCommit", {"rm1State": self.rm1State})

    @icontract.require(lambda self: self.pc == "RMLoop" and self.rm1State in {"working", "prepared"})
    @icontract.ensure(lambda self: self.rm1State == "aborted")
    def apply_abort(self) -> None:
        self.rm1State = "aborted"
        log_action("RM1.ApplyAbort", {"rm1State": self.rm1State})
