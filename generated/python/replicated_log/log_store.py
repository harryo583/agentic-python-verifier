"""Generated from LogStore_Impl.tla. Inductive Inv: TypeOK /\\ \\A n \\in Nodes : Len(logs[n]) <= MaxLen."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: all(n in self.logs for n in self.nodes))
@icontract.invariant(
    lambda self: all(
        all(e in self.entries for e in self.logs[n]) for n in self.nodes
    )
)
@icontract.invariant(
    lambda self: all(len(self.logs[n]) <= self.max_len for n in self.nodes)
)
class LogStore:
    def __init__(
        self,
        nodes: frozenset[str] | set[str],
        max_len: int,
        entries: frozenset[str] | set[str],
    ) -> None:
        self.nodes = frozenset(nodes)
        self.max_len = int(max_len)
        self.entries = frozenset(entries)
        self.logs: dict[str, list] = {n: [] for n in self.nodes}

    @icontract.require(lambda self, n: n in self.nodes)
    @icontract.require(lambda self, n, e: e in self.entries)
    @icontract.require(lambda self, n: len(self.logs[n]) < self.max_len)
    @icontract.ensure(lambda self, n: len(self.logs[n]) <= self.max_len)
    def append_entry(self, n: str, e: str) -> None:
        self.logs[n] = self.logs[n] + [e]
        log_action(
            "LogStore.AppendEntry",
            {"logs": {k: list(v) for k, v in self.logs.items()}},
        )

    @icontract.require(lambda self, f: f in self.nodes)
    @icontract.require(lambda self, f, src: src in self.nodes)
    def replicate(self, f: str, src: str) -> None:
        self.logs[f] = list(self.logs[src])
        log_action(
            "LogStore.Replicate",
            {"logs": {k: list(v) for k, v in self.logs.items()}},
        )
