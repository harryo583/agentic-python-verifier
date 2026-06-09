"""Generated from Producer_Impl.tla. Inductive Inv:
/\\ pc \\in {"Loop", "Finish", "Done"}
/\\ nextItem \\in 1..(MaxItem+1)
/\\ generated \\in ExpectedSeqs
/\\ Len(generated) = nextItem - 1
"""

from __future__ import annotations

import icontract

from ._trace import log_action


def _expected_seqs(max_item: int) -> list[list[int]]:
    return [list(range(1, n + 1)) for n in range(0, max_item + 1)]


@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
@icontract.invariant(lambda self: self.nextItem in range(1, self.MaxItem + 2))
@icontract.invariant(lambda self: self.generated in _expected_seqs(self.MaxItem))
@icontract.invariant(lambda self: len(self.generated) == self.nextItem - 1)
class Producer:
    def __init__(self, MaxItem: int = 3) -> None:
        self.MaxItem = MaxItem
        self.generated: list[int] = []
        self.nextItem: int = 1
        self.pc: str = "Loop"

    @icontract.require(lambda self: self.pc in {"Loop", "Finish"})
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
                # Loop exit: while-condition false, advance to Finish (stutter).
                self.pc = "Finish"
        elif self.pc == "Finish":
            # skip; advance to Done (stutter).
            self.pc = "Done"
