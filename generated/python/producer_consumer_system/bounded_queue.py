"""Generated from BoundedQueue_Impl.tla.

Inductive Inv:
    /\ pc \in {"Loop", "Finish", "Done"}
    /\ buffer \in BoundedSeqs
    /\ Len(buffer) \in 0..Capacity
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
@icontract.invariant(
    lambda self: isinstance(self.buffer, list)
    and all(isinstance(x, int) and 1 <= x <= 10 for x in self.buffer)
)
@icontract.invariant(lambda self: 0 <= len(self.buffer) <= self.capacity)
class BoundedQueue:
    def __init__(self, capacity: int = 3) -> None:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        self.capacity: int = capacity
        self.buffer: list[int] = []
        self.pc: str = "Loop"

    @icontract.require(lambda self, v: isinstance(v, int) and 1 <= v <= 10)
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
    def dequeue(self) -> int:
        head = self.buffer[0]
        self.buffer = self.buffer[1:]
        log_action(
            "BoundedQueue.Dequeue",
            {"queue": list(self.buffer)},
        )
        return head
