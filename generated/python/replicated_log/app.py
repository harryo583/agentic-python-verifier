"""Composed parent for ReplicatedLog. Property: AtMostOneLeader /\\ TypeOK."""

from __future__ import annotations

import icontract

from ._trace import log_action
from .election import Election
from .log_store import LogStore


@icontract.invariant(
    lambda self: all(
        self.election.role[n] in ("leader", "follower") for n in self.election.nodes
    )
    and all(0 <= self.election.term[n] <= self.election.max_term for n in self.election.nodes)
)
@icontract.invariant(
    lambda self: all(
        n in self.log_store.log
        and isinstance(self.log_store.log[n], list)
        and len(self.log_store.log[n]) <= self.log_store.max_len
        and all(e in self.log_store.entries for e in self.log_store.log[n])
        for n in self.log_store.nodes
    )
    and set(self.log_store.log.keys()) == set(self.log_store.nodes)
)
@icontract.invariant(
    lambda self: sum(
        1 for n in self.election.nodes if self.election.role[n] == "leader"
    )
    <= 1
)
class ReplicatedLog:
    def __init__(self) -> None:
        nodes = ["n1", "n2", "n3"]
        entries = [1, 2, 3]
        self.election = Election(nodes=nodes, max_term=2)
        self.log_store = LogStore(nodes=nodes, entries=entries, max_len=3)
        self._turn = 0

    def step(self) -> None:
        """One atomic step: alternate between Election.Next and LogStore.Next.

        Election action keeps log/pcL UNCHANGED; LogStore action keeps
        role/term/pcE UNCHANGED. Each branch performs exactly one composed
        transition.
        """
        nodes = self.election.nodes
        t = self._turn
        self._turn += 1

        if t % 2 == 0:
            # Election action: try to elect the next node as leader.
            max_t = max(self.election.term[n] for n in nodes)
            if max_t < self.election.max_term:
                # Choose deterministic candidate.
                candidate = nodes[(t // 2) % len(nodes)]
                self.election.elect_leader(candidate)
        else:
            # LogStore action: append or replicate.
            # Find a leader (or fall back to n1) and append an entry.
            leader = None
            for n in nodes:
                if self.election.role[n] == "leader":
                    leader = n
                    break
            if leader is None:
                leader = nodes[0]
            if len(self.log_store.log[leader]) < self.log_store.max_len:
                # Deterministic entry choice.
                entry = self.log_store.entries[
                    (t // 2) % len(self.log_store.entries)
                ]
                self.log_store.append_entry(leader, entry)
            else:
                # Replicate leader's log to a follower whose log differs.
                for dst in nodes:
                    if dst != leader and self.log_store.log[dst] != self.log_store.log[leader]:
                        self.log_store.replicate(leader, dst)
                        break

        log_action(
            "ReplicatedLog.Step",
            {
                "role": dict(self.election.role),
                "term": dict(self.election.term),
                "log": {k: list(v) for k, v in self.log_store.log.items()},
            },
        )


def run(steps: int = 50) -> ReplicatedLog:
    app = ReplicatedLog()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
