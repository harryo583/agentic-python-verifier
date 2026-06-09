"""Generated from Producer_Impl.tla. Inductive Inv:
  /\\ generated \\in BSeq(1..MaxItem, MaxItem)
  /\\ nextItem \\in 1..(MaxItem+1)
  /\\ nextItem = Len(generated) + 1
  /\\ pc \\in {"Loop", "Finish", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(x in range(1, self.MaxItem + 1) for x in self.generated)
    and len(self.generated) <= self.MaxItem
)
@icontract.invariant(lambda self: self.nextItem in range(1, self.MaxItem + 2))
@icontract.invariant(lambda self: self.nextItem == len(self.generated) + 1)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class Producer:
    def __init__(self, MaxItem: int = 3) -> None:
        self.MaxItem = MaxItem
        self.generated: list[int] = []
        self.nextItem: int = 1
        self.pc: str = "Loop"

    @icontract.require(lambda self: self.pc in {"Loop", "Finish", "Done"})
    def produce(self) -> None:
        if self.pc == "Loop":
            if self.nextItem <= self.MaxItem:
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
                # Stutter: transition to Finish without mutating abs vars.
                self.pc = "Finish"
        elif self.pc == "Finish":
            # Stutter: Finish -> Done, no abs change.
            self.pc = "Done"
        # If Done: pure stutter; do nothing.
