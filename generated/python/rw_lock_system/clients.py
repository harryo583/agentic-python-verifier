"""Generated from Clients_Impl.tla.

Inductive Inv:
  /\\ client_state \\in [Clients -> {"idle","reading","writing"}]
  /\\ Cardinality(WritersSet) <= 1
  /\\ ~(ReadersSet # {} /\\ WritersSet # {})
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(
        self.client_state[c] in {"idle", "reading", "writing"}
        for c in self.clients
    )
)
@icontract.invariant(
    lambda self: sum(
        1 for c in self.clients if self.client_state[c] == "writing"
    )
    <= 1
)
@icontract.invariant(
    lambda self: not (
        any(self.client_state[c] == "reading" for c in self.clients)
        and any(self.client_state[c] == "writing" for c in self.clients)
    )
)
class Clients:
    def __init__(self, clients: frozenset[str] | set[str] | list[str]) -> None:
        self.clients = frozenset(clients)
        self.client_state: dict[str, str] = {c: "idle" for c in self.clients}

    @icontract.require(lambda self, c: c in self.clients)
    @icontract.require(lambda self, c: self.client_state[c] == "idle")
    @icontract.require(
        lambda self: all(
            self.client_state[o] != "writing" for o in self.clients
        )
    )
    @icontract.ensure(lambda self, c: self.client_state[c] == "reading")
    def start_read(self, c: str) -> None:
        self.client_state[c] = "reading"
        log_action(
            "Clients.StartRead",
            {"client_state": dict(self.client_state)},
        )

    @icontract.require(lambda self, c: c in self.clients)
    @icontract.require(lambda self, c: self.client_state[c] == "reading")
    @icontract.ensure(lambda self, c: self.client_state[c] == "idle")
    def finish_read(self, c: str) -> None:
        self.client_state[c] = "idle"
        log_action(
            "Clients.FinishRead",
            {"client_state": dict(self.client_state)},
        )

    @icontract.require(lambda self, c: c in self.clients)
    @icontract.require(lambda self, c: self.client_state[c] == "idle")
    @icontract.require(
        lambda self: all(
            self.client_state[o] == "idle" for o in self.clients
        )
    )
    @icontract.ensure(lambda self, c: self.client_state[c] == "writing")
    def start_write(self, c: str) -> None:
        self.client_state[c] = "writing"
        log_action(
            "Clients.StartWrite",
            {"client_state": dict(self.client_state)},
        )

    @icontract.require(lambda self, c: c in self.clients)
    @icontract.require(lambda self, c: self.client_state[c] == "writing")
    @icontract.ensure(lambda self, c: self.client_state[c] == "idle")
    def finish_write(self, c: str) -> None:
        self.client_state[c] = "idle"
        log_action(
            "Clients.FinishWrite",
            {"client_state": dict(self.client_state)},
        )
