"""Generated from Consumer_Impl.tla. Inductive Inv: /\\ received \\in BoundedReceived /\\ runningSum \\in 0..(MaxLen*10) /\\ runningSum = SumSeq(received) /\\ pc \\in {"Loop", "Finish", "Done"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


def _sum_seq(s: list[int]) -> int:
    return sum(s)


def _in_bounded_received(s: list[int], max_len: int) -> bool:
    return len(s) <= max_len and all(v in range(1, 11) for v in s)


@icontract.invariant(lambda self: _in_bounded_received(self.received, self.MaxLen))
@icontract.invariant(lambda self: self.runningSum in range(0, self.MaxLen * 10 + 1))
@icontract.invariant(lambda self: self.runningSum == _sum_seq(self.received))
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class Consumer:
    def __init__(self, MaxLen: int) -> None:
        self.MaxLen = MaxLen
        self.received: list[int] = []
        self.runningSum: int = 0
        self.pc: str = "Loop"

    @icontract.require(lambda self, v: v in range(1, 11))
    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.require(lambda self: len(self.received) < self.MaxLen)
    @icontract.ensure(lambda self: self.pc in {"Loop", "Finish"})
    def consume(self, v: int) -> None:
        self.received = self.received + [v]
        self.runningSum = self.runningSum + v
        if len(self.received) >= self.MaxLen:
            self.pc = "Finish"
        else:
            self.pc = "Loop"
        log_action(
            "Consumer.Consume",
            {"received": list(self.received), "runningSum": self.runningSum},
        )

    @icontract.require(lambda self: self.pc == "Finish")
    @icontract.ensure(lambda self: self.pc == "Done")
    def finish(self) -> None:
        self.pc = "Done"
        log_action(
            "Consumer.Finish",
            {"received": list(self.received), "runningSum": self.runningSum},
        )
