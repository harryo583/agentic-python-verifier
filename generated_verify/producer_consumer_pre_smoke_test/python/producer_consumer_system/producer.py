"""Generated from Producer_Impl.tla. Inductive Inv:
  /\\ generated \\in BSeq(1..MaxItem)
  /\\ next_item \\in 1..(MaxItem+1)
  /\\ Len(generated) = next_item - 1
  /\\ \\A i \\in 1..Len(generated) : generated[i] = i
  /\\ pc \\in {"Loop", "Done"}
"""

from __future__ import annotations

import icontract

from ._trace import log_action


@icontract.invariant(
    lambda self: all(x in range(1, self.max_item + 1) for x in self.generated)
    and len(self.generated) <= self.max_len
)
@icontract.invariant(lambda self: self.next_item in range(1, self.max_item + 2))
@icontract.invariant(lambda self: len(self.generated) == self.next_item - 1)
@icontract.invariant(
    lambda self: all(
        self.generated[i] == i + 1 for i in range(len(self.generated))
    )
)
@icontract.invariant(lambda self: self.pc in {"Loop", "Done"})
class Producer:
    def __init__(self, max_item: int = 3, max_len: int = 3) -> None:
        assert max_len >= max_item, "MaxLen must be >= MaxItem to bound BSeq"
        self.max_item = max_item
        self.max_len = max_len
        self.generated: list[int] = []
        self.next_item: int = 1
        self.pc: str = "Loop"

    @icontract.require(lambda self: self.pc == "Loop")
    @icontract.ensure(lambda self: self.pc in {"Loop", "Done"})
    def produce(self) -> None:
        if self.next_item <= self.max_item:
            self.generated = self.generated + [self.next_item]
            self.next_item = self.next_item + 1
            # stay in Loop
        else:
            self.pc = "Done"
        log_action(
            "Producer.Produce",
            {
                "generated": list(self.generated),
                "next_item": self.next_item,
            },
        )
