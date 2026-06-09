"""Generated from Consumer_Impl.tla. Inductive Inv: pc \\in {"Loop","Finish","Done"} /\\ received \\in BoundedSeqs /\\ sum \\in 0..(MaxLen*10) /\\ sum = SumSeq(received)."""

from __future__ import annotations

import icontract

from ._trace import log_action


def _sum_seq(s: list[int]) -> int:
    return sum(s)


@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
@icontract.invariant(
    lambda self: len(self.received) <= self.MaxLen
    and all(v in range(1, 11) for v in self.received)
)
@icontract.invariant(lambda self: 0 <= self.sum <= self.MaxLen * 10)
@icontract.invariant(lambda self: self.sum == _sum_seq(self.received))
class Consumer:
    def __init__(self, MaxLen: int = 3) -> None:
        self.MaxLen = MaxLen
        self.received: list[int] = []
        self.sum: int = 0
        self.pc: str = "Loop"

    @icontract.require(lambda self, v: v in range(1, 11))
    @icontract.require(lambda self: self.pc in {"Loop", "Finish"})
    def consume(self, v: int) -> None:
        if self.pc == "Loop" and len(self.received) < self.MaxLen:
            self.received = self.received + [v]
            self.sum = self.sum + v
            if len(self.received) >= self.MaxLen:
                self.pc = "Finish"
            log_action(
                "Consumer.Consume",
                {
                    "received": list(self.received),
                    "sum": self.sum,
                },
            )
            return
        # stutter: either Loop with full buffer transitioning to Finish,
        # or Finish -> Done. No abs-var mutation, no log_action.
        if self.pc == "Loop":
            self.pc = "Finish"
        elif self.pc == "Finish":
            self.pc = "Done"
