"""Generated from Consumer_Impl.tla. Inductive Inv:
  /\\ received \\in BoundedSeq(1..10, 3)
  /\\ sum \\in 0..30
  /\\ sum = SumSeq(received)
  /\\ pc \\in {"ConsumeLoop", "Finish", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


def _sum_seq(s):
    return sum(s)


@icontract.invariant(
    lambda self: len(self.received) <= 3
    and all(v in range(1, 11) for v in self.received)
)
@icontract.invariant(lambda self: self.sum in range(0, 31))
@icontract.invariant(lambda self: self.sum == _sum_seq(self.received))
@icontract.invariant(lambda self: self.pc in {"ConsumeLoop", "Finish", "Done"})
class Consumer:
    def __init__(self) -> None:
        self.received: list[int] = []
        self.sum: int = 0
        self.pc: str = "ConsumeLoop"

    @icontract.require(
        lambda self, v: v in range(1, 11)
    )
    @icontract.require(lambda self: self.pc in {"ConsumeLoop", "Finish"})
    def consume(self, v: int) -> None:
        if self.pc == "ConsumeLoop":
            if len(self.received) < 3:
                self.received = self.received + [v]
                self.sum = self.sum + v
                log_action(
                    "Consumer.Consume",
                    {
                        "received": list(self.received),
                        "sum": self.sum,
                    },
                )
            else:
                # leave loop, no abs-var change -> stutter
                self.pc = "Finish"
        elif self.pc == "Finish":
            # skip then done -> stutter
            self.pc = "Done"
        # pc == "Done": stutter
