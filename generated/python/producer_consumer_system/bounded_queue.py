"""Generated from BoundedQueue_Impl.tla. Inductive Inv: buffer \\in BoundedSeq(1..10, Capacity) /\\ pc \\in {"Loop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(v in range(1, 11) for v in self.buffer)
    and len(self.buffer) <= self.capacity
)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class BoundedQueue:
    def __init__(self, capacity: int = 3) -> None:
        self.capacity = capacity
        self.buffer: list[int] = []
        self.pc = "Loop"

    @icontract.require(lambda self, v: v in range(1, 11))
    @icontract.require(lambda self: len(self.buffer) < self.capacity)
    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.ensure(lambda self: self.pc == "Loop")
    def enqueue(self, v: int) -> None:
        self.buffer = self.buffer + [v]
        log_action(
            "BoundedQueue.Enqueue",
            {"queue": list(self.buffer)},
        )

    @icontract.require(lambda self: len(self.buffer) > 0)
    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.ensure(lambda self: self.pc == "Loop")
    def dequeue(self) -> None:
        self.buffer = self.buffer[1:]
        log_action(
            "BoundedQueue.Dequeue",
            {"queue": list(self.buffer)},
        )
