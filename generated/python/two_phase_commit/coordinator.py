"""Generated from Coordinator_Impl.tla.

Inductive Inv:
  /\\ votes \\in SUBSET RMIDs
  /\\ decision \\in Decisions
  /\\ (decision = "commit") => (votes = RMIDs)
  /\\ pc \\in {"CoLoop", "Finish", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: set(self.votes) <= set(self.RMIDs))
@icontract.invariant(lambda self: self.decision in self.Decisions)
@icontract.invariant(
    lambda self: (self.decision != "commit") or (set(self.votes) == set(self.RMIDs))
)
@icontract.invariant(lambda self: self.pc in {"CoLoop", "Finish", "Done"})
class Coordinator:
    def __init__(self, RMIDs, Decisions) -> None:
        self.RMIDs = frozenset(RMIDs)
        self.Decisions = frozenset(Decisions)
        self.votes: set = set()
        self.decision: str = "none"
        self.pc: str = "CoLoop"

    @icontract.require(lambda self, r: r in self.RMIDs)
    @icontract.require(lambda self: self.decision == "none")
    @icontract.require(lambda self: self.pc == "CoLoop")
    @icontract.ensure(lambda self, r: r in self.votes)
    @icontract.ensure(lambda self: self.decision == "none")
    def receive_prepared(self, r) -> None:
        self.votes = self.votes | {r}
        log_action(
            "Coordinator.ReceivePrepared",
            {"votes": set(self.votes), "decision": self.decision},
        )

    @icontract.require(lambda self: self.decision == "none")
    @icontract.require(lambda self: set(self.votes) == set(self.RMIDs))
    @icontract.require(lambda self: self.pc == "CoLoop")
    @icontract.ensure(lambda self: self.decision == "commit")
    def decide_commit(self) -> None:
        self.decision = "commit"
        log_action(
            "Coordinator.DecideCommit",
            {"votes": set(self.votes), "decision": self.decision},
        )

    @icontract.require(lambda self: self.decision == "none")
    @icontract.require(lambda self: self.pc == "CoLoop")
    @icontract.ensure(lambda self: self.decision == "abort")
    def decide_abort(self) -> None:
        self.decision = "abort"
        log_action(
            "Coordinator.DecideAbort",
            {"votes": set(self.votes), "decision": self.decision},
        )
