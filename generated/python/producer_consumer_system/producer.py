"""Generated from Producer_Impl.tla.

Inductive Inv:
  /\\ nextItem \\in 1..(MaxItem+1)
  /\\ generated \\in BoundedSeq(1..MaxItem, MaxItem)
  /\\ Len(generated) = nextItem - 1
  /\\ \\A i \\in 1..Len(generated) : generated[i] = i
  /\\ pc \\in {"ProduceLoop", "Finish", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: 1 <= self.nextItem <= self.MaxItem + 1)
@icontract.invariant(
    lambda self: all(x in range(1, self.MaxItem + 1) for x in self.generated)
    and len(self.generated) <= self.MaxItem
)
@icontract.invariant(lambda self: len(self.generated) == self.nextItem - 1)
@icontract.invariant(
    lambda self: all(self.generated[i] == i + 1 for i in range(len(self.generated)))
)
@icontract.invariant(lambda self: self.pc in {"ProduceLoop", "Finish", "Done"})
class Producer:
    def __init__(self, MaxItem: int) -> None:
        self.MaxItem = MaxItem
        self.generated: list[int] = []
        self.nextItem: int = 1
        self.pc: str = "ProduceLoop"

    @icontract.require(lambda self: self.pc in {"ProduceLoop", "Finish"})
    def produce_loop(self) -> None:
        if self.pc == "ProduceLoop":
            if self.nextItem <= self.MaxItem:
                # Mutating branch: emit Produce.
                self.generated = self.generated + [self.nextItem]
                self.nextItem = self.nextItem + 1
                log_action(
                    "Producer.Produce",
                    {
                        "generated": list(self.generated),
                        "nextItem": self.nextItem,
                    },
                )
            else:
                # Loop exit: stutter (no abs-var change).
                self.pc = "Finish"
        elif self.pc == "Finish":
            # skip; stutter to Done.
            self.pc = "Done"
