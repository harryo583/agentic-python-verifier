"""Generated from RWLock_Impl.tla.

Inductive Inv:
  /\\ state \\in {"free", "read", "write"}
  /\\ reader_count \\in 0..MaxReaders
  /\\ (state = "write") => (reader_count = 0)
  /\\ (state = "free") => (reader_count = 0)
  /\\ (state = "read") => (reader_count >= 1)
  /\\ pc \\in {"Loop", "Finish", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: self.state in {"free", "read", "write"})
@icontract.invariant(lambda self: 0 <= self.reader_count <= self.MaxReaders)
@icontract.invariant(lambda self: (self.state != "write") or (self.reader_count == 0))
@icontract.invariant(lambda self: (self.state != "free") or (self.reader_count == 0))
@icontract.invariant(lambda self: (self.state != "read") or (self.reader_count >= 1))
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class RWLock:
    def __init__(self, MaxReaders: int = 3) -> None:
        self.MaxReaders = MaxReaders
        self.state = "free"
        self.reader_count = 0
        self.pc = "Loop"

    @icontract.require(
        lambda self: self.pc == "Loop"
        and self.state in {"free", "read"}
        and self.reader_count < self.MaxReaders
    )
    def acquire_read(self) -> None:
        self.state = "read"
        self.reader_count = self.reader_count + 1
        log_action(
            "RWLock.AcquireRead",
            {"state": self.state, "reader_count": self.reader_count},
        )

    @icontract.require(
        lambda self: self.pc == "Loop"
        and self.state == "read"
        and self.reader_count > 0
    )
    def release_read(self) -> None:
        if self.reader_count - 1 == 0:
            self.state = "free"
        self.reader_count = self.reader_count - 1
        log_action(
            "RWLock.ReleaseRead",
            {"state": self.state, "reader_count": self.reader_count},
        )

    @icontract.require(
        lambda self: self.pc == "Loop"
        and self.state == "free"
        and self.reader_count == 0
    )
    def acquire_write(self) -> None:
        self.state = "write"
        log_action(
            "RWLock.AcquireWrite",
            {"state": self.state, "reader_count": self.reader_count},
        )

    @icontract.require(lambda self: self.pc == "Loop" and self.state == "write")
    def release_write(self) -> None:
        self.state = "free"
        log_action(
            "RWLock.ReleaseWrite",
            {"state": self.state, "reader_count": self.reader_count},
        )
