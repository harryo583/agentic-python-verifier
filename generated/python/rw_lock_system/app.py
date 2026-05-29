"""Composed parent for RWLockSystem.

Property:
  /\\ (state = "write") => (reader_count = 0 /\\ Cardinality(WritersSet) <= 1)
  /\\ (\\E c \\in Clients : client_state[c] = "reading") => (state = "read" /\\ reader_count >= 1)
  /\\ (state = "free") => (reader_count = 0 /\\ ReadersSet = {} /\\ WritersSet = {})

The parent composes RWLock (the lock state machine) and Clients (the per-client
state machine) into a single system that performs atomic composed transitions:
each `step()` advances both children together so that the joint invariants
relating `state`/`reader_count` to `ReadersSet`/`WritersSet` always hold at
quiescent boundaries.
"""

from __future__ import annotations

import random

import icontract

from ._trace import log_action
from .rwlock import RWLock
from .clients import Clients

random.seed(0)


def _readers_set(clients: Clients) -> set[str]:
    return {c for c in clients.clients if clients.client_state[c] == "reading"}


def _writers_set(clients: Clients) -> set[str]:
    return {c for c in clients.clients if clients.client_state[c] == "writing"}


# TypeOK + Inv conjuncts -----------------------------------------------------
@icontract.invariant(
    lambda self: self.lock.state in {"free", "read", "write"}
)
@icontract.invariant(
    lambda self: 0 <= self.lock.reader_count <= self.lock.max_readers
)
# (state = "write") => reader_count = 0 /\ |WritersSet| <= 1
@icontract.invariant(
    lambda self: (self.lock.state != "write")
    or (
        self.lock.reader_count == 0
        and sum(1 for c in self.clients.clients if self.clients.client_state[c] == "writing") <= 1
    )
)
# (state = "free") => reader_count = 0 /\ ReadersSet = {} /\ WritersSet = {}
@icontract.invariant(
    lambda self: (self.lock.state != "free")
    or (
        self.lock.reader_count == 0
        and all(self.clients.client_state[c] == "idle" for c in self.clients.clients)
    )
)
# (\E reader) => state = "read" /\ reader_count >= 1
@icontract.invariant(
    lambda self: (
        not any(self.clients.client_state[c] == "reading" for c in self.clients.clients)
    )
    or (self.lock.state == "read" and self.lock.reader_count >= 1)
)
# (\E writer) => state = "write"
@icontract.invariant(
    lambda self: (
        not any(self.clients.client_state[c] == "writing" for c in self.clients.clients)
    )
    or (self.lock.state == "write")
)
# |WritersSet| <= 1
@icontract.invariant(
    lambda self: sum(
        1 for c in self.clients.clients if self.clients.client_state[c] == "writing"
    )
    <= 1
)
# ~(ReadersSet # {} /\ WritersSet # {})
@icontract.invariant(
    lambda self: not (
        any(self.clients.client_state[c] == "reading" for c in self.clients.clients)
        and any(self.clients.client_state[c] == "writing" for c in self.clients.clients)
    )
)
class RWLockSystem:
    def __init__(
        self,
        clients: list[str] | None = None,
        max_readers: int = 3,
    ) -> None:
        if clients is None:
            clients = ["c1", "c2", "c3"]
        self.lock = RWLock(max_readers=max_readers)
        self.clients = Clients(clients=clients)
        # Deterministic per-step scheduling.
        self._rng = random.Random(0)
        # Ordered client list for deterministic iteration.
        self._client_order = sorted(self.clients.clients)

    # --- Composed atomic actions -------------------------------------------
    def _try_start_read(self, c: str) -> bool:
        """Atomically: acquire_read on the lock AND mark client as reading."""
        if self.clients.client_state[c] != "idle":
            return False
        # No writer allowed (client-level guard).
        if any(self.clients.client_state[o] == "writing" for o in self.clients.clients):
            return False
        # Lock-level guard: must be free or read, and capacity not exceeded.
        if self.lock.state not in {"free", "read"}:
            return False
        if self.lock.reader_count >= self.lock.max_readers:
            return False
        self.lock.acquire_read()
        self.clients.start_read(c)
        return True

    def _try_finish_read(self, c: str) -> bool:
        if self.clients.client_state[c] != "reading":
            return False
        if self.lock.state != "read" or self.lock.reader_count <= 0:
            return False
        # Release lock first, then client transitions to idle. Both happen
        # atomically inside this method (invariants checked only on return).
        self.lock.release_read()
        self.clients.finish_read(c)
        return True

    def _try_start_write(self, c: str) -> bool:
        if self.clients.client_state[c] != "idle":
            return False
        if not all(self.clients.client_state[o] == "idle" for o in self.clients.clients):
            return False
        if self.lock.state != "free" or self.lock.reader_count != 0:
            return False
        self.lock.acquire_write()
        self.clients.start_write(c)
        return True

    def _try_finish_write(self, c: str) -> bool:
        if self.clients.client_state[c] != "writing":
            return False
        if self.lock.state != "write":
            return False
        self.lock.release_write()
        self.clients.finish_write(c)
        return True

    def step(self) -> None:
        """One atomic step of the composed RWLockSystem."""
        # Enumerate all enabled composed actions deterministically, then pick
        # one via the seeded RNG. This corresponds to a single Next-step of
        # the parent TLA spec (LockStep \/ ClientsStep) restricted to the
        # subset that keeps the joint invariants intact.
        actions: list[tuple[str, str]] = []
        for c in self._client_order:
            cs = self.clients.client_state[c]
            if cs == "idle":
                # Try start_read
                if (
                    self.lock.state in {"free", "read"}
                    and self.lock.reader_count < self.lock.max_readers
                    and all(self.clients.client_state[o] != "writing" for o in self.clients.clients)
                ):
                    actions.append(("start_read", c))
                # Try start_write
                if (
                    self.lock.state == "free"
                    and self.lock.reader_count == 0
                    and all(self.clients.client_state[o] == "idle" for o in self.clients.clients)
                ):
                    actions.append(("start_write", c))
            elif cs == "reading":
                actions.append(("finish_read", c))
            elif cs == "writing":
                actions.append(("finish_write", c))

        if not actions:
            # No enabled composed action; stutter step.
            log_action(
                "RWLockSystem.Step",
                {
                    "kind": "stutter",
                    "state": self.lock.state,
                    "reader_count": self.lock.reader_count,
                    "client_state": dict(self.clients.client_state),
                },
            )
            return

        kind, c = actions[self._rng.randrange(len(actions))]
        if kind == "start_read":
            self._try_start_read(c)
        elif kind == "finish_read":
            self._try_finish_read(c)
        elif kind == "start_write":
            self._try_start_write(c)
        elif kind == "finish_write":
            self._try_finish_write(c)

        log_action(
            "RWLockSystem.Step",
            {
                "kind": kind,
                "client": c,
                "state": self.lock.state,
                "reader_count": self.lock.reader_count,
                "client_state": dict(self.clients.client_state),
            },
        )


def run(steps: int = 50) -> RWLockSystem:
    app = RWLockSystem()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
