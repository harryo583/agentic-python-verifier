"""Generated from Coordinator_Impl.tla.

Inductive Inv:
  /\\ pc \\in PCs
  /\\ coordState \\in CoordStates
  /\\ decision \\in Decisions
  /\\ votes \\in [RMs -> VoteVals]
  /\\ (decision = "Commit") => (\\A r \\in RMs : votes[r] = "prepared")
"""

from __future__ import annotations

import icontract

from ._trace import log_action


COORD_STATES = {"init", "preparing", "decided"}
VOTE_VALS = {"none", "prepared", "aborted"}
DECISIONS = {"none", "Commit", "Abort"}
PCS = {"Run", "Finish", "Done"}


@icontract.invariant(lambda self: self.pc in PCS)
@icontract.invariant(lambda self: self.coordState in COORD_STATES)
@icontract.invariant(lambda self: self.decision in DECISIONS)
@icontract.invariant(
    lambda self: all(r in self.votes for r in self.rms)
    and all(self.votes[r] in VOTE_VALS for r in self.rms)
)
@icontract.invariant(
    lambda self: (self.decision != "Commit")
    or all(self.votes[r] == "prepared" for r in self.rms)
)
class Coordinator:
    def __init__(self, rms) -> None:
        self.rms = frozenset(rms)
        self.coordState = "init"
        self.votes = {r: "none" for r in self.rms}
        self.decision = "none"
        self.pc = "Run"

    @icontract.require(lambda self: self.coordState == "init")
    def send_prepare(self) -> None:
        self.coordState = "preparing"
        log_action(
            "Coordinator.SendPrepare",
            {
                "coordState": self.coordState,
                "votes": dict(self.votes),
                "decision": self.decision,
            },
        )

    @icontract.require(
        lambda self, r, v: r in self.rms
        and v in {"prepared", "aborted"}
        and self.coordState == "preparing"
        and self.votes[r] == "none"
    )
    def collect_vote(self, r, v) -> None:
        self.votes[r] = v
        log_action(
            "Coordinator.CollectVote",
            {
                "coordState": self.coordState,
                "votes": dict(self.votes),
                "decision": self.decision,
            },
        )

    @icontract.require(
        lambda self: self.coordState == "preparing"
        and self.decision == "none"
        and all(self.votes[r] == "prepared" for r in self.rms)
    )
    def decide_commit(self) -> None:
        self.decision = "Commit"
        self.coordState = "decided"
        log_action(
            "Coordinator.DecideCommit",
            {
                "coordState": self.coordState,
                "votes": dict(self.votes),
                "decision": self.decision,
            },
        )

    @icontract.require(
        lambda self: self.coordState == "preparing"
        and self.decision == "none"
        and any(self.votes[r] == "aborted" for r in self.rms)
    )
    def decide_abort(self) -> None:
        self.decision = "Abort"
        self.coordState = "decided"
        log_action(
            "Coordinator.DecideAbort",
            {
                "coordState": self.coordState,
                "votes": dict(self.votes),
                "decision": self.decision,
            },
        )
