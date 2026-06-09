"""Generated from ResourceManager_Impl.tla.

Inductive Inv:
  /\ rmState \in States
  /\ pc \in {"Loop","Finish","Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


STATES = {"working", "prepared", "committed", "aborted"}
PC_VALUES = {"Loop", "Finish", "Done"}


@icontract.invariant(lambda self: self.rmState in STATES)
@icontract.invariant(lambda self: self.pc in PC_VALUES)
class ResourceManager:
    def __init__(self) -> None:
        self.rmState = "working"
        self.pc = "Loop"

    @icontract.require(lambda self: self.rmState == "working")
    @icontract.ensure(lambda self: self.rmState == "prepared")
    def prepare(self) -> None:
        self.rmState = "prepared"
        log_action(
            "ResourceManager.Prepare",
            {"rm1State": self.rmState},
        )

    @icontract.require(lambda self: self.rmState == "prepared")
    @icontract.ensure(lambda self: self.rmState == "committed")
    def receive_commit(self) -> None:
        self.rmState = "committed"
        log_action(
            "ResourceManager.ReceiveCommit",
            {"rm1State": self.rmState},
        )

    @icontract.require(lambda self: self.rmState in {"working", "prepared"})
    @icontract.ensure(lambda self: self.rmState == "aborted")
    def receive_abort(self) -> None:
        self.rmState = "aborted"
        log_action(
            "ResourceManager.ReceiveAbort",
            {"rm1State": self.rmState},
        )

    def stutter(self) -> None:
        # No state change; do not emit a trace entry.
        pass
