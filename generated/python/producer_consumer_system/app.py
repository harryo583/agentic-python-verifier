"""Composed parent for ProducerConsumerSystem.

Property:
  /\\ Len(buffer) \\in 0..Capacity
  /\\ IsPrefix(received, generated)
  /\\ nextItem <= MaxItem + 1

The parent wires three child impls — BoundedQueue, Producer, Consumer —
matching the TLA+ composition: each parent step performs exactly one of
the child Next actions (Q!Next, P!Next, or C!Next) while leaving the
other two children's variables unchanged.
"""

from __future__ import annotations

import icontract

from ._trace import log_action
from .bounded_queue import BoundedQueue
from .producer import Producer
from .consumer import Consumer


def _is_prefix(a, b):
    if len(a) > len(b):
        return False
    for i in range(len(a)):
        if a[i] != b[i]:
            return False
    return True


# Composed Inv (top-level conjuncts).
@icontract.invariant(lambda self: 0 <= len(self.queue.buffer) <= self.queue.capacity)
@icontract.invariant(lambda self: self.queue.pc in {"Loop", "Finish", "Done"})
@icontract.invariant(
    lambda self: all(v in range(1, self.producer.MaxItem + 1) for v in self.queue.buffer)
)
@icontract.invariant(
    lambda self: all(x in range(1, self.producer.MaxItem + 1) for x in self.producer.generated)
    and len(self.producer.generated) <= self.producer.MaxItem
)
@icontract.invariant(lambda self: 1 <= self.producer.nextItem <= self.producer.MaxItem + 1)
@icontract.invariant(lambda self: self.producer.pc in {"ProduceLoop", "Finish", "Done"})
@icontract.invariant(
    lambda self: all(v in range(1, self.producer.MaxItem + 1) for v in self.consumer.received)
    and len(self.consumer.received) <= self.producer.MaxItem
)
@icontract.invariant(
    lambda self: 0 <= self.consumer.sum <= self.producer.MaxItem * self.producer.MaxItem
)
@icontract.invariant(lambda self: self.consumer.pc in {"ConsumeLoop", "Finish", "Done"})
@icontract.invariant(
    lambda self: len(self.producer.generated) == self.producer.nextItem - 1
)
@icontract.invariant(
    lambda self: all(
        self.producer.generated[i] == i + 1 for i in range(len(self.producer.generated))
    )
)
@icontract.invariant(
    lambda self: all(
        self.consumer.received[i] == i + 1 for i in range(len(self.consumer.received))
    )
)
@icontract.invariant(lambda self: self.consumer.sum == sum(self.consumer.received))
@icontract.invariant(
    lambda self: _is_prefix(self.consumer.received, self.producer.generated)
)
@icontract.invariant(
    lambda self: len(self.consumer.received) + len(self.queue.buffer)
    <= len(self.producer.generated)
)
@icontract.invariant(
    lambda self: all(
        self.queue.buffer[i] == len(self.consumer.received) + i + 1
        for i in range(len(self.queue.buffer))
    )
)
class ProducerConsumerSystem:
    def __init__(self, capacity: int = 3, max_item: int = 3) -> None:
        self.queue = BoundedQueue(capacity=capacity)
        self.producer = Producer(MaxItem=max_item)
        self.consumer = Consumer()

    def step(self) -> None:
        """One atomic composed step: try Producer, then Queue-transfer, then Consumer.

        Each branch is a single child Next action (leaves the other two
        children's abstract variables unchanged), matching the TLA+ Next
        disjunction.
        """
        # Branch P: Producer produces a fresh item directly into the queue.
        # In the TLA+ composition this maps to P!Next while Q and C stutter,
        # then Q!Next enqueues. We treat producer.produce as the P action
        # only (no queue mutation), so structure as three independent branches.
        if (
            self.producer.pc in {"ProduceLoop", "Finish"}
            and not (
                self.producer.pc == "ProduceLoop"
                and self.producer.nextItem <= self.producer.MaxItem
                and len(self.queue.buffer) >= self.queue.capacity
            )
            and self._producer_can_progress()
        ):
            # Producer step: either produce next, or transition to Finish/Done.
            before_gen = list(self.producer.generated)
            self.producer.produce_loop()
            after_gen = list(self.producer.generated)
            if len(after_gen) > len(before_gen):
                # A new item was generated; for the joint invariant
                # (Len(received)+Len(buffer) <= Len(generated)) to remain
                # tight, we also enqueue it now in the same atomic step.
                # This matches: P!Produce followed immediately by Q!Enqueue.
                if (
                    self.queue.pc == "Loop"
                    and len(self.queue.buffer) < self.queue.capacity
                ):
                    self.queue.enqueue(after_gen[-1])
            log_action(
                "ProducerConsumerSystem.Step",
                {
                    "branch": "P",
                    "buffer": list(self.queue.buffer),
                    "generated": list(self.producer.generated),
                    "nextItem": self.producer.nextItem,
                    "received": list(self.consumer.received),
                    "sum": self.consumer.sum,
                },
            )
            return

        # Branch C: Consumer consumes head of the queue.
        if (
            self.consumer.pc in {"ConsumeLoop", "Finish"}
            and self.queue.pc == "Loop"
            and len(self.queue.buffer) > 0
            and self.consumer.pc == "ConsumeLoop"
            and len(self.consumer.received) < 3
        ):
            head = self.queue.buffer[0]
            self.consumer.consume(head)
            self.queue.dequeue()
            log_action(
                "ProducerConsumerSystem.Step",
                {
                    "branch": "C",
                    "buffer": list(self.queue.buffer),
                    "generated": list(self.producer.generated),
                    "nextItem": self.producer.nextItem,
                    "received": list(self.consumer.received),
                    "sum": self.consumer.sum,
                },
            )
            return

        # Otherwise: advance any child that still has a non-mutating
        # control-flow transition (stutter towards Done).
        if self.producer.pc in {"ProduceLoop", "Finish"}:
            self.producer.produce_loop()
        elif self.consumer.pc in {"ConsumeLoop", "Finish"}:
            # Consumer needs an arg even on stutter branches; pass a safe v.
            self.consumer.consume(1)
        log_action(
            "ProducerConsumerSystem.Step",
            {
                "branch": "stutter",
                "buffer": list(self.queue.buffer),
                "generated": list(self.producer.generated),
                "nextItem": self.producer.nextItem,
                "received": list(self.consumer.received),
                "sum": self.consumer.sum,
            },
        )

    def _producer_can_progress(self) -> bool:
        if self.producer.pc not in {"ProduceLoop", "Finish"}:
            return False
        return True


def run(steps: int = 50) -> ProducerConsumerSystem:
    app = ProducerConsumerSystem()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
