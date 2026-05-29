"""Generated from Election_Impl.tla. Inductive Inv: TypeOK /\\ Cardinality(Leaders) <= 1."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(self.role[n] in {"leader", "follower"} for n in self.nodes)
    and all(isinstance(self.term[n], int) and 0 <= self.term[n] <= self.max_term for n in self.nodes)
)
@icontract.invariant(
    lambda self: sum(1 for n in self.nodes if self.role[n] == "leader") <= 1
)
class Election:
    def __init__(self, nodes, max_term: int) -> None:
        self.nodes = list(nodes)
        self.max_term = max_term
        self.role = {n: "follower" for n in self.nodes}
        self.term = {n: 0 for n in self.nodes}

    def _leaders_count(self) -> int:
        return sum(1 for n in self.nodes if self.role[n] == "leader")

    @icontract.require(lambda self, n: n in self.nodes)
    @icontract.require(lambda self, n: self._leaders_count() == 0)
    def elect_leader(self, n) -> None:
        self.role[n] = "leader"
        log_action(
            "Election.ElectLeader",
            {"role": dict(self.role), "term": dict(self.term)},
        )

    @icontract.require(lambda self, n: n in self.nodes)
    @icontract.require(lambda self, n: self.role[n] == "leader")
    def step_down(self, n) -> None:
        self.role[n] = "follower"
        log_action(
            "Election.StepDown",
            {"role": dict(self.role), "term": dict(self.term)},
        )

    @icontract.require(lambda self, n: n in self.nodes)
    @icontract.require(lambda self, n: self.term[n] < self.max_term)
    def bump_term(self, n) -> None:
        new_val = self.term[n] + 1
        self.term = {m: new_val for m in self.nodes}
        log_action(
            "Election.BumpTerm",
            {"role": dict(self.role), "term": dict(self.term)},
        )
