"""Composed parent for TwoPhaseCommit. Property: Agreement /\\ CommittedImpliesDecision."""

from __future__ import annotations

import icontract

from ._trace import log_action
from .resource_manager import ResourceManager
from .coordinator import Coordinator


TERMINAL = {"committed", "aborted"}


@icontract.invariant(
    lambda self: all(
        (self.rm.rmState[r1] == self.rm.rmState[r2])
        for r1 in self.rm.RMs
        for r2 in self.rm.RMs
        if self.rm.rmState[r1] in TERMINAL and self.rm.rmState[r2] in TERMINAL
    )
)
@icontract.invariant(
    lambda self: (not any(self.rm.rmState[r] == "committed" for r in self.rm.RMs))
    or (self.co.decision == "Commit")
)
class TwoPhaseCommit:
    def __init__(self, RMs=("r1", "r2")) -> None:
        self.RMs = tuple(RMs)
        self.rm = ResourceManager(RMs=self.RMs)
        self.co = Coordinator(rms=self.RMs)
        self._phase = 0

    def step(self) -> None:
        """One atomic step of the composed 2PC system.

        Drives a deterministic happy-path commit:
          1. Coordinator sends prepare.
          2. Each RM prepares (atomic with collecting its vote at the coordinator).
          3. Coordinator decides commit once all votes are prepared.
          4. Each RM receives the commit decision.
        """
        # Phase 0: coordinator broadcasts prepare.
        if self.co.coordState == "init":
            self.co.send_prepare()
            log_action(
                "TwoPhaseCommit.Step",
                {
                    "rmState": dict(self.rm.rmState),
                    "coordState": self.co.coordState,
                    "votes": dict(self.co.votes),
                    "decision": self.co.decision,
                },
            )
            return

        # Phase 1: for each working RM, atomically prepare + collect its vote.
        for r in self.RMs:
            if self.rm.rmState[r] == "working" and self.co.votes[r] == "none":
                self.rm.prepare(r)
                self.co.collect_vote(r, "prepared")
                log_action(
                    "TwoPhaseCommit.Step",
                    {
                        "rmState": dict(self.rm.rmState),
                        "coordState": self.co.coordState,
                        "votes": dict(self.co.votes),
                        "decision": self.co.decision,
                    },
                )
                return

        # Phase 2: decide commit once all votes are prepared.
        if (
            self.co.coordState == "preparing"
            and self.co.decision == "none"
            and all(self.co.votes[r] == "prepared" for r in self.RMs)
        ):
            self.co.decide_commit()
            log_action(
                "TwoPhaseCommit.Step",
                {
                    "rmState": dict(self.rm.rmState),
                    "coordState": self.co.coordState,
                    "votes": dict(self.co.votes),
                    "decision": self.co.decision,
                },
            )
            return

        # Phase 3: propagate commit to each RM. Safe because decision == "Commit"
        # already holds before any RM transitions to "committed", preserving
        # CommittedImpliesDecision.
        if self.co.decision == "Commit":
            for r in self.RMs:
                if self.rm.rmState[r] == "prepared":
                    self.rm.receive_commit(r)
                    log_action(
                        "TwoPhaseCommit.Step",
                        {
                            "rmState": dict(self.rm.rmState),
                            "coordState": self.co.coordState,
                            "votes": dict(self.co.votes),
                            "decision": self.co.decision,
                        },
                    )
                    return

        # Stuttering: system has reached a terminal committed state.
        log_action(
            "TwoPhaseCommit.Step",
            {
                "rmState": dict(self.rm.rmState),
                "coordState": self.co.coordState,
                "votes": dict(self.co.votes),
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
