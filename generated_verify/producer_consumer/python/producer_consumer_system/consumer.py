"""Generated from Consumer_Impl.tla. Inductive Inv:
    /\\ received \\in BSeq(1..MaxVal, MaxLen)
    /\\ sum \\in 0..(MaxLen*MaxVal)
    /\\ sum = SumOf(received)
    /\\ pc \\in {"Loop", "Finish", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


def _sum_of(s: list[int]) -> int:
    return sum(s)


@icontract.invariant(
    lambda self: all(v in range(1, self.max_val + 1) for v in self.received)
    and len(self.received) <= self.max_len
)
@icontract.invariant(
    lambda self: self.sum in range(0, self.max_len * self.max_val + 1)
)
@icontract.invariant(lambda self: self.sum == _sum_of(self.received))
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class Consumer:
    def __init__(self, max_len: int, max_val: int) -> None:
        self.max_len = max_len
        self.max_val = max_val
        self.received: list[int] = []
        self.sum: int = 0
        self.pc: str = "Loop"

    @icontract.require(lambda self, v: 1 <= v <= self.max_val)
    def consume(self, v: int) -> None:
        if self.pc == "Loop" and len(self.received) < self.max_len:
            self.received = self.received + [v]
            self.sum = self.sum + v
            log_action(
                "Consumer.Consume",
                {
                    "received": list(self.received),
                    "sum": self.sum,
                },
            )
        elif self.pc == "Loop":
            # Loop -> Finish (stutter w.r.t. abs vars)
            self.pc = "Finish"
        elif self.pc == "Finish":
            # Finish -> Done (stutter w.r.t. abs vars)
            self.pc = "Done"
        # Done: no-op stutter
