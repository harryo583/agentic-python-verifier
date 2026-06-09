"""Composed parent for RWLockSystem.

Property:
  /\\ MutualExclusion: (state = "write") => (reader_count = 0 /\\ Cardinality(WritingClients) <= 1)
  /\\ NoTornState: reading clients imply state=read & reader_count>=1; state=free implies empty.
  /\\ CountAgrees: reader_count = Cardinality(ReadingClients)

Composition: Each step performs one atomic composed transition that pairs a
RWLock action with the matching Clients action (e.g. AcquireRead+StartRead) so
that the joint invariant holds at method boundaries.
"""

from __future__ import annotations

import icontract

from ._trace import log_action
from .rwlock import RWLock
from .clients import Clients


def _reading_clients(cs):
    return {c for c, s in cs.items() if s == "reading"}


def _writing_clients(cs):
    return {c for c, s in cs.items() if s == "writing"}


@icontract.invariant(
    lambda self: self.lock.state in {"free", "read", "write"}
)
@icontract.invariant(
    lambda self: 0 <= self.lock.reader_count <= self.lock.MaxReaders
)
@icontract.invariant(
    lambda self: all(
        self.clients.client_state[c] in {"idle", "reading", "writing"}
        for c in self.clients.clients
    )
)
# MutualExclusion
@icontract.invariant(
    lambda self: (self.lock.state != "write")
    or (
        self.lock.reader_count == 0
        and len(_writing_clients(self.clients.client_state)) <= 1
    )
)
# NoTornState: any reading client => state=read & reader_count>=1
@icontract.invariant(
    lambda self: (not any(
        self.clients.client_state[c] == "reading"
        for c in self.clients.clients
    ))
    or (self.lock.state == "read" and self.lock.reader_count >= 1)
)
# NoTornState: state=free => no readers, no writers
@icontract.invariant(
    lambda self: (self.lock.state != "free")
    or (
        self.lock.reader_count == 0
        and len(_reading_clients(self.clients.client_state)) == 0
        and len(_writing_clients(self.clients.client_state)) == 0
    )
)
# CountAgrees
@icontract.invariant(
    lambda self: self.lock.reader_count
    == len(_reading_clients(self.clients.client_state))
)
class RWLockSystem:
    def __init__(self, max_readers: int = 3, client_ids=None) -> None:
        if client_ids is None:
            client_ids = ["c1", "c2", "c3"]
        self.lock = RWLock(MaxReaders=max_readers)
        self.clients = Clients(client_ids)
        self._turn = 0

    # --- composed atomic transitions ---

    def acquire_read(self, c) -> None:
        """Atomically: lock.acquire_read() + clients.start_read(c)."""
        self.lock.acquire_read()
        self.clients.start_read(c)
        log_action(
            "RWLockSystem.AcquireRead",
            {
                "state": self.lock.state,
                "reader_count": self.lock.reader_count,
                "client": c,
                "client_state": dict(self.clients.client_state),
            },
        )

    def release_read(self, c) -> None:
        """Atomically: clients.finish_read(c) + lock.release_read()."""
        self.clients.finish_read(c)
        self.lock.release_read()
        log_action(
            "RWLockSystem.ReleaseRead",
            {
                "state": self.lock.state,
                "reader_count": self.lock.reader_count,
                "client": c,
                "client_state": dict(self.clients.client_state),
            },
        )

    def acquire_write(self, c) -> None:
        """Atomically: lock.acquire_write() + clients.start_write(c)."""
        self.lock.acquire_write()
        self.clients.start_write(c)
        log_action(
            "RWLockSystem.AcquireWrite",
            {
                "state": self.lock.state,
                "reader_count": self.lock.reader_count,
                "client": c,
                "client_state": dict(self.clients.client_state),
            },
        )

    def release_write(self, c) -> None:
        """Atomically: clients.finish_write(c) + lock.release_write()."""
        self.clients.finish_write(c)
        self.lock.release_write()
        log_action(
            "RWLockSystem.ReleaseWrite",
            {
                "state": self.lock.state,
                "reader_count": self.lock.reader_count,
                "client": c,
                "client_state": dict(self.clients.client_state),
            },
        )

    def step(self) -> None:
        """One deterministic atomic composed step."""
        cs = self.clients.client_state
        lock = self.lock

        # Find an idle / reading / writing client deterministically.
        idle = [c for c in self.clients.clients if cs[c] == "idle"]
        reading = [c for c in self.clients.clients if cs[c] == "reading"]
        writing = [c for c in self.clients.clients if cs[c] == "writing"]

        phase = self._turn % 6
        self._turn += 1

        # Try a sequence of preferred transitions; fall through to anything legal.
        # 0,1: acquire reads if possible
        if phase in (0, 1) and idle and lock.state in {"free", "read"} \
                and lock.reader_count < lock.MaxReaders and not writing:
            self.acquire_read(idle[0])
            return
        # 2: release one read
        if phase == 2 and reading and lock.state == "read" and lock.reader_count > 0:
            self.release_read(reading[0])
            return
        # 3: release all reads then acquire write
        if phase == 3:
            if reading and lock.state == "read":
                self.release_read(reading[0])
                return
            if not reading and not writing and idle and lock.state == "free":
                self.acquire_write(idle[0])
                return
        # 4: release write
        if phase == 4 and writing and lock.state == "write":
            self.release_write(writing[0])
            return
        # 5: fallback - try any legal action
        # priority: release write, release read, acquire read, acquire write
        if writing and lock.state == "write":
            self.release_write(writing[0])
            return
        if reading and lock.state == "read" and lock.reader_count > 0:
            self.release_read(reading[0])
            return
        if idle and lock.state in {"free", "read"} \
                and lock.reader_count < lock.MaxReaders and not writing:
            self.acquire_read(idle[0])
            return
        if idle and lock.state == "free" and lock.reader_count == 0 and not writing:
            self.acquire_write(idle[0])
            return
        # Nothing to do — stutter (no log_action since no state change).

        log_action(
            "RWLockSystem.Stutter",
            {
                "state": lock.state,
                "reader_count": lock.reader_count,
                "client_state": dict(cs),
            },
        )


def run(steps: int = 50) -> RWLockSystem:
    app = RWLockSystem()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
