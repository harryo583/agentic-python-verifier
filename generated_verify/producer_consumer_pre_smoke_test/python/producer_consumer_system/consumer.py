"""Generated from Consumer_Impl.tla. Inductive Inv: received \\in BSeq(1..10) /\\ sum \\in 0..(10 * MaxLen) /\\ sum = SumSeq(received) /\\ pc \\in {"Loop", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


def _sum_seq(s: list[int]) -> int:
    return sum(s)


@icontract.invariant(lambda self: all(v in range(1, 11) for v in self.received) and len(self.received) <= self.max_len)
@icontract.invariant(lambda self: self.sum in range(0, 10 * self.max_len + 1))
@icontract.invariant(lambda self: self.sum == _sum_seq(self.received))
@icontract.invariant(lambda self: self.pc in {"Loop", "Done"})
class Consumer:
    def __init__(self, max_len: int = 5) -> None:
        self.max_len = max_len
        self.received: list[int] = []
        self.sum: int = 0
        self.pc: str = "Loop"

    @icontract.require(lambda self, v: v in range(1, 11))
    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.require(lambda self: len(self.received) < self.max_len)
    @icontract.ensure(lambda self: self.pc in {"Loop", "Done"})
    def consume(self, v: int) -> None:
        self.received = self.received + [v]
        self.sum = self.sum + v
        if len(self.received) >= self.max_len:
            self.pc = "Done"
        else:
            self.pc = "Loop"
        log_action(
            "Consumer.Consume",
            {"received": list(self.received), "sum": self.sum},
        )
