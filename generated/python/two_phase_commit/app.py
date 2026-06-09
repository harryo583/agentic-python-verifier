"""Composed parent for TwoPhaseCommit. Property: Agreement /\\ CommitImpliesDecision."""

from __future__ import annotations

import icontract

from ._trace import log_action
from .rm1 import RM1
from .rm2 import RM2
from .coordinator import Coordinator


@icontract.invariant(lambda self: self.rm1.rm1State in {"working", "prepared", "committed", "aborted"})
@icontract.invariant(lambda self: self.rm2.rm2State in {"working", "prepared", "committed", "aborted"})
@icontract.invariant(lambda self: self.co.decision in {"none", "commit", "abort"})
@icontract.invariant(lambda self: set(self.co.votes) <= {"rm1", "rm2"})
@icontract.invariant(lambda self: self.rm1.pc in {"RMLoop", "Finish", "Done"})
@icontract.invariant(lambda self: self.rm2.pc in {"RMLoop", "Finish", "Done"})
@icontract.invariant(lambda self: self.co.pc in {"CoLoop", "Finish", "Done"})
@icontract.invariant(
    lambda self: (self.co.decision != "commit") or (set(self.co.votes) == {"rm1", "rm2"})
)
@icontract.invariant(
    lambda self: (self.rm1.rm1State != "committed") or (self.co.decision == "commit")
)
@icontract.invariant(
    lambda self: (self.rm2.rm2State != "committed") or (self.co.decision == "commit")
)
@icontract.invariant(
    lambda self: not (
        (self.rm1.rm1State == "committed" and self.rm2.rm2State == "aborted")
        or (self.rm1.rm1State == "aborted" and self.rm2.rm2State == "committed")
    )
)
class TwoPhaseCommit:
    def __init__(self) -> None:
        self.rm1 = RM1(States={"working", "prepared", "committed", "aborted"})
        self.rm2 = RM2(states={"working", "prepared", "committed", "aborted"})
        self.co = Coordinator(
            RMIDs={"rm1", "rm2"},
            Decisions={"none", "commit", "abort"},
        )

    def step(self) -> None:
        """One atomic step of the composed 2PC protocol.

        Drives the happy-path: each RM prepares, the coordinator collects votes,
        decides commit, then each RM applies the commit. After completion the
        step is a no-op so further ticks keep all invariants stable.
        """
        # Phase 1: RM1 prepares
        if self.rm1.rm1State == "working" and self.rm1.pc == "RMLoop":
            self.rm1.prepare()
        # Phase 1: RM2 prepares
        elif self.rm2.rm2State == "working":
            self.rm2.prepare()
        # Phase 2: coordinator collects RM1's vote
        elif (
            self.co.pc == "CoLoop"
            and self.co.decision == "none"
            and "rm1" not in self.co.votes
        ):
            self.co.receive_prepared("rm1")
        # Phase 2: coordinator collects RM2's vote
        elif (
            self.co.pc == "CoLoop"
            and self.co.decision == "none"
            and "rm2" not in self.co.votes
        ):
            self.co.receive_prepared("rm2")
        # Phase 3: coordinator decides commit once all votes are in
        elif (
            self.co.pc == "CoLoop"
            and self.co.decision == "none"
            and set(self.co.votes) == {"rm1", "rm2"}
        ):
            self.co.decide_commit()
        # Phase 4: RMs apply the commit (only after decision = commit, preserving Inv)
        elif (
            self.co.decision == "commit"
            and self.rm1.rm1State == "prepared"
            and self.rm1.pc == "RMLoop"
        ):
            self.rm1.apply_commit()
        elif (
            self.co.decision == "commit"
            and self.rm2.rm2State == "prepared"
        ):
            self.rm2.apply_commit()
        # else: protocol complete; idle step

        log_action(
            "TwoPhaseCommit.Step",
            {
                "rm1State": self.rm1.rm1State,
                "rm2State": self.rm2.rm2State,
                "votes": sorted(self.co.votes),
                "decision": self.co.decision,
            },
        )


def run(steps: int = 50) -> TwoPhaseCommit:
    app = TwoPhaseCommit()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
