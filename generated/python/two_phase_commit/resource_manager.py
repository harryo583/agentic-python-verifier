"""Generated from ResourceManager_Impl.tla. Inductive Inv: pc \\in PCs /\\ rmState \\in [RMs -> States]."""

from __future__ import annotations

import icontract

from ._trace import log_action


STATES = {"working", "prepared", "committed", "aborted"}
PCS = {"Loop", "Finish", "Done"}


@icontract.invariant(lambda self: self.pc in PCS)
@icontract.invariant(
    lambda self: isinstance(self.rmState, dict)
    and set(self.rmState.keys()) == set(self.RMs)
    and all(v in STATES for v in self.rmState.values())
)
class ResourceManager:
    def __init__(self, RMs=None) -> None:
        if RMs is None:
            RMs = ("r1", "r2")
        self.RMs = tuple(RMs)
        self.rmState = {r: "working" for r in self.RMs}
        self.pc = "Loop"

    @icontract.require(lambda self, r: r in self.RMs)
    @icontract.require(lambda self, r: self.rmState[r] == "working")
    def prepare(self, r) -> None:
        self.rmState[r] = "prepared"
        log_action(
            "ResourceManager.Prepare",
            {"rmState": dict(self.rmState)},
        )

    @icontract.require(lambda self, r: r in self.RMs)
    @icontract.require(lambda self, r: self.rmState[r] == "working")
    def vote_abort(self, r) -> None:
        self.rmState[r] = "aborted"
        log_action(
            "ResourceManager.VoteAbort",
            {"rmState": dict(self.rmState)},
        )

    @icontract.require(lambda self, r: r in self.RMs)
    @icontract.require(lambda self, r: self.rmState[r] == "prepared")
    def receive_commit(self, r) -> None:
        self.rmState[r] = "committed"
        log_action(
            "ResourceManager.ReceiveCommit",
            {"rmState": dict(self.rmState)},
        )

    @icontract.require(lambda self, r: r in self.RMs)
    @icontract.require(lambda self, r: self.rmState[r] in {"working", "prepared"})
    def receive_abort(self, r) -> None:
        self.rmState[r] = "aborted"
        log_action(
            "ResourceManager.ReceiveAbort",
            {"rmState": dict(self.rmState)},
        )
