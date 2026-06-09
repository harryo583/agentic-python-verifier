"""Generated from Election_Impl.tla. Inductive Inv: TypeOK /\\ AtMostOneLeader."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(self.role[n] in ("leader", "follower") for n in self.nodes)
    and all(0 <= self.term[n] <= self.max_term for n in self.nodes)
)
@icontract.invariant(
    lambda self: sum(1 for n in self.nodes if self.role[n] == "leader") <= 1
)
class Election:
    def __init__(self, nodes: list, max_term: int) -> None:
        if not nodes:
            raise ValueError("Nodes must be non-empty")
        self.nodes = list(nodes)
        self.max_term = int(max_term)
        initial_leader = self.nodes[0]
        self.role = {
            n: ("leader" if n == initial_leader else "follower") for n in self.nodes
        }
        self.term = {n: 0 for n in self.nodes}

    def _max_term_value(self) -> int:
        return max(self.term[n] for n in self.nodes)

    @icontract.ensure(
        lambda self: sum(1 for n in self.nodes if self.role[n] == "leader") <= 1
    )
    def elect_leader(self, ldr) -> bool:
        max_t = self._max_term_value()
        if max_t >= self.max_term:
            return False
        if ldr not in self.nodes:
            return False
        self.role = {
            n: ("leader" if n == ldr else "follower") for n in self.nodes
        }
        self.term = {n: max_t + 1 for n in self.nodes}
        log_action(
            "Election.ElectLeader",
            {
                "role": dict(self.role),
                "term": dict(self.term),
            },
        )
        return True

    def step_down(self) -> None:
        # Stutter step: vars unchanged, do not log.
        return None
