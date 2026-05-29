"""Composed parent for ReplicatedLog. Property: ElectionSafety /\\ LogBounds /\\ TermBounds."""

from __future__ import annotations

import random

import icontract

from ._trace import log_action
from .election import Election
from .log_store import LogStore

random.seed(0)

_NODES = ["n1", "n2", "n3"]
_MAX_TERM = 2
_MAX_LEN = 3
_ENTRIES = frozenset([1, 2, 3])


@icontract.invariant(
    lambda self: sum(1 for n in self.election.nodes if self.election.role[n] == "leader") <= 1
)
@icontract.invariant(
    lambda self: all(
        len(self.log_store.logs[n]) <= self.log_store.max_len for n in self.log_store.nodes
    )
)
@icontract.invariant(
    lambda self: all(
        all(e in self.log_store.entries for e in self.log_store.logs[n])
        for n in self.log_store.nodes
    )
)
@icontract.invariant(
    lambda self: all(
        isinstance(self.election.term[n], int) and 0 <= self.election.term[n] <= self.election.max_term
        for n in self.election.nodes
    )
)
class ReplicatedLog:
    def __init__(self) -> None:
        self.election = Election(nodes=list(_NODES), max_term=_MAX_TERM)
        self.log_store = LogStore(
            nodes=frozenset(_NODES), max_len=_MAX_LEN, entries=_ENTRIES
        )
        self._tick = 0

    def _leaders(self) -> list:
        return [n for n in self.election.nodes if self.election.role[n] == "leader"]

    def step(self) -> None:
        """One atomic composed transition selected deterministically by tick."""
        t = self._tick
        self._tick += 1

        leaders = self._leaders()

        # Cycle through a small deterministic schedule that exercises all actions.
        phase = t % 8

        if phase == 0:
            # Elect a leader if none exists.
            if len(leaders) == 0:
                self.election.elect_leader(_NODES[0])
        elif phase == 1:
            # Leader appends an entry.
            if leaders:
                ldr = leaders[0]
                if len(self.log_store.logs[ldr]) < self.log_store.max_len:
                    entry = ((t // 8) % 3) + 1
                    self.log_store.append_entry(ldr, entry)
        elif phase == 2:
            # Replicate from leader to a follower.
            if leaders:
                ldr = leaders[0]
                followers = [n for n in self.election.nodes if self.election.role[n] == "follower"]
                if followers:
                    self.log_store.replicate(followers[0], ldr)
        elif phase == 3:
            # Leader appends another entry.
            if leaders:
                ldr = leaders[0]
                if len(self.log_store.logs[ldr]) < self.log_store.max_len:
                    entry = ((t // 8) % 3) + 1
                    self.log_store.append_entry(ldr, entry)
        elif phase == 4:
            # Replicate to second follower.
            if leaders:
                ldr = leaders[0]
                followers = [n for n in self.election.nodes if self.election.role[n] == "follower"]
                if len(followers) >= 2:
                    self.log_store.replicate(followers[1], ldr)
        elif phase == 5:
            # Bump term if possible.
            if self.election.term[_NODES[0]] < self.election.max_term:
                self.election.bump_term(_NODES[0])
        elif phase == 6:
            # Step down current leader.
            if leaders:
                self.election.step_down(leaders[0])
        elif phase == 7:
            # Elect a (possibly different) leader if none.
            if len(self._leaders()) == 0:
                idx = (t // 8) % len(_NODES)
                self.election.elect_leader(_NODES[idx])

        log_action(
            "ReplicatedLog.Step",
            {
                "role": dict(self.election.role),
                "term": dict(self.election.term),
                "logs": {k: list(v) for k, v in self.log_store.logs.items()},
            },
        )


def run(steps: int = 50) -> ReplicatedLog:
    app = ReplicatedLog()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
