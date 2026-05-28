"""Generated from Producer_Impl.tla. Inductive Inv: /\\ nextItem \\in 1..(MaxItem+1) /\\ generated \\in PrefixSeqs /\\ Len(generated) = nextItem - 1 /\\ pc \\in {\"Loop\", \"Finish\", \"Done\"}."""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(lambda self: self.nextItem in range(1, self.MaxItem + 2))
@icontract.invariant(lambda self: self.generated == [i for i in range(1, len(self.generated) + 1)] and len(self.generated) <= self.MaxItem)
@icontract.invariant(lambda self: len(self.generated) == self.nextItem - 1)
@icontract.invariant(lambda self: self.pc in {"Loop", "Finish", "Done"})
class Producer:
    def __init__(self, MaxItem: int) -> None:
        self.MaxItem = MaxItem
        self.generated: list[int] = []
        self.nextItem: int = 1
        self.pc: str = "Loop"

    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.ensure(lambda self: self.pc in {"Loop", "Finish"})
    def step(self) -> None:
        if self.nextItem <= self.MaxItem:
            self.generated = self.generated + [self.nextItem]
            self.nextItem = self.nextItem + 1
            # pc stays "Loop"
        else:
            self.pc = "Finish"
        log_action(
            "Producer.Produce",
            {"generated": list(self.generated), "nextItem": self.nextItem},
        )

    @icontract.require(lambda self: self.pc == "Finish")
    @icontract.ensure(lambda self: self.pc == "Done")
    def finish(self) -> None:
        self.pc = "Done"
        log_action(
            "Producer.Finish",
            {"generated": list(self.generated), "nextItem": self.nextItem},
        )
