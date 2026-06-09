"""Generated from LogStore_Impl.tla. Inductive Inv: TypeOK."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(
        n in self.log
        and isinstance(self.log[n], list)
        and len(self.log[n]) <= self.max_len
        and all(e in self.entries for e in self.log[n])
        for n in self.nodes
    )
    and set(self.log.keys()) == set(self.nodes)
)
class LogStore:
    def __init__(self, nodes, entries, max_len: int) -> None:
        self.nodes = list(nodes)
        self.entries = list(entries)
        self.max_len = int(max_len)
        self.log = {n: [] for n in self.nodes}

    @icontract.require(lambda self, n, e: n in self.nodes and e in self.entries)
    @icontract.require(lambda self, n, e: len(self.log[n]) < self.max_len)
    @icontract.ensure(lambda self, n, e: self.log[n][-1] == e)
    def append_entry(self, n, e) -> None:
        self.log[n] = self.log[n] + [e]
        log_action(
            "LogStore.AppendEntry",
            {"log": {k: list(v) for k, v in self.log.items()}},
        )

    @icontract.require(lambda self, src, dst: src in self.nodes and dst in self.nodes)
    @icontract.require(lambda self, src, dst: src != dst)
    @icontract.ensure(lambda self, src, dst: self.log[dst] == self.log[src])
    def replicate(self, src, dst) -> None:
        self.log[dst] = list(self.log[src])
        log_action(
            "LogStore.Replicate",
            {"log": {k: list(v) for k, v in self.log.items()}},
        )
