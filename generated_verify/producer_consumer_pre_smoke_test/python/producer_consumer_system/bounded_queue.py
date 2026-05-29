"""Generated from BoundedQueue_Impl.tla. Inductive Inv:
  /\\ buffer \\in BSeq(1..10)
  /\\ Len(buffer) \\in 0..Capacity
  /\\ pc \\in {"Loop", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: all(isinstance(x, int) and 1 <= x <= 10 for x in self.buffer) and len(self.buffer) <= self.max_len)
@icontract.invariant(lambda self: 0 <= len(self.buffer) <= self.capacity)
@icontract.invariant(lambda self: self.pc in {"Loop", "Done"})
class BoundedQueue:
    def __init__(self, capacity: int = 3, max_len: int = 5) -> None:
        assert capacity >= 0
        assert max_len >= capacity
        self.capacity = capacity
        self.max_len = max_len
        self.buffer: list[int] = []
        self.pc = "Loop"

    @icontract.require(lambda self, v: self.pc == "Loop")
    @icontract.require(lambda self, v: len(self.buffer) < self.max_len)
    @icontract.require(lambda self, v: len(self.buffer) < self.capacity)
    @icontract.require(lambda self, v: v in range(1, 11))
    @icontract.ensure(lambda self: self.pc in {"Loop", "Done"})
    def enqueue(self, v: int) -> None:
        self.buffer = self.buffer + [v]
        if len(self.buffer) >= self.max_len:
            self.pc = "Done"
        log_action(
            "BoundedQueue.Enqueue",
            {"queue": list(self.buffer)},
        )

    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.require(lambda self: len(self.buffer) < self.max_len)
    @icontract.require(lambda self: len(self.buffer) > 0)
    @icontract.ensure(lambda self: self.pc in {"Loop", "Done"})
    def dequeue(self) -> None:
        self.buffer = self.buffer[1:]
        if len(self.buffer) >= self.max_len:
            self.pc = "Done"
        log_action(
            "BoundedQueue.Dequeue",
            {"queue": list(self.buffer)},
        )
