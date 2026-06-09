"""Generated from BoundedQueue_Impl.tla. Inductive Inv:
    /\\ buffer \\in BSeq(1..10, Capacity)
    /\\ pc \\in {"Loop", "Finish", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: isinstance(self.buffer, list)
    and len(self.buffer) <= self.capacity
    and all(v in range(1, 11) for v in self.buffer)
)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class BoundedQueue:
    def __init__(self, capacity: int = 3) -> None:
        self.capacity = capacity
        self.buffer: list[int] = []
        self.pc = "Loop"

    @icontract.require(lambda self, v: v in range(1, 11))
    @icontract.require(lambda self: len(self.buffer) < self.capacity)
    @icontract.ensure(lambda self: self.pc in {"Loop", "Finish", "Done"})
    def enqueue(self, v: int) -> None:
        self.buffer = self.buffer + [v]
        log_action(
            "BoundedQueue.Enqueue",
            {"buffer": list(self.buffer)},
        )

    @icontract.require(lambda self: len(self.buffer) > 0)
    @icontract.ensure(lambda self: self.pc in {"Loop", "Finish", "Done"})
    def dequeue(self) -> None:
        self.buffer = self.buffer[1:]
        log_action(
            "BoundedQueue.Dequeue",
            {"buffer": list(self.buffer)},
        )
