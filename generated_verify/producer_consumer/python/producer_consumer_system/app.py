"""Composed parent for ProducerConsumerSystem. Property:
  /\\ Len(buffer) \\in 0..Capacity
  /\\ IsPrefix(received, generated)
  /\\ nextItem <= MaxItem + 1
"""

from __future__ import annotations

import icontract

from ._trace import log_action
from .bounded_queue import BoundedQueue
from .producer import Producer
from .consumer import Consumer


def _is_prefix(s: list[int], t: list[int]) -> bool:
    return len(s) <= len(t) and all(s[i] == t[i] for i in range(len(s)))


def _sum_of(s: list[int]) -> int:
    return sum(s)


@icontract.invariant(
    lambda self: all(v in range(1, self.max_item + 1) for v in self.queue.buffer)
    and len(self.queue.buffer) <= self.capacity
)
@icontract.invariant(
    lambda self: all(v in range(1, self.max_item + 1) for v in self.producer.generated)
    and len(self.producer.generated) <= self.max_item
)
@icontract.invariant(
    lambda self: all(v in range(1, self.max_item + 1) for v in self.consumer.received)
    and len(self.consumer.received) <= self.max_item
)
@icontract.invariant(
    lambda self: self.producer.nextItem in range(1, self.max_item + 2)
)
@icontract.invariant(
    lambda self: self.consumer.sum in range(0, self.max_item * self.max_item + 1)
)
@icontract.invariant(lambda self: self.queue.pc in {"Loop", "Finish", "Done"})
@icontract.invariant(lambda self: self.producer.pc in {"Loop", "Finish", "Done"})
@icontract.invariant(lambda self: self.consumer.pc in {"Loop", "Finish", "Done"})
@icontract.invariant(
    lambda self: self.producer.nextItem == len(self.producer.generated) + 1
)
@icontract.invariant(lambda self: self.consumer.sum == _sum_of(self.consumer.received))
@icontract.invariant(
    lambda self: _is_prefix(self.consumer.received, self.producer.generated)
)
@icontract.invariant(
    lambda self: self.producer.generated
    == self.consumer.received + self.queue.buffer
)
class ProducerConsumerSystem:
    def __init__(self, capacity: int = 3, max_item: int = 3) -> None:
        self.capacity = capacity
        self.max_item = max_item
        self.queue = BoundedQueue(capacity=capacity)
        self.producer = Producer(MaxItem=max_item)
        self.consumer = Consumer(max_len=max_item, max_val=max_item)

    def step(self) -> None:
        """One atomic step of the composed system.

        Alternates between ProduceStep and ConsumeStep when each is enabled,
        preferring Produce when both are possible so the consumer always has
        something to chew on.
        """
        produce_enabled = (
            self.producer.nextItem <= self.producer.MaxItem
            and len(self.queue.buffer) < self.queue.capacity
            and self.producer.pc == "Loop"
        )
        consume_enabled = len(self.queue.buffer) > 0 and self.consumer.pc == "Loop"

        if produce_enabled and (not consume_enabled or len(self.queue.buffer) == 0):
            # ProduceStep: producer generates next item AND it is enqueued atomically.
            v = self.producer.nextItem
            self.producer.produce()
            self.queue.enqueue(v)
        elif consume_enabled:
            # ConsumeStep: dequeue head atomically and feed to consumer.
            head = self.queue.buffer[0]
            self.consumer.consume(head)
            self.queue.dequeue()
        elif produce_enabled:
            v = self.producer.nextItem
            self.producer.produce()
            self.queue.enqueue(v)
        # else: nothing enabled; stutter.

        log_action(
            "ProducerConsumerSystem.Step",
            {
                "buffer": list(self.queue.buffer),
                "generated": list(self.producer.generated),
                "nextItem": self.producer.nextItem,
                "received": list(self.consumer.received),
                "sum": self.consumer.sum,
            },
        )


def run(steps: int = 50) -> ProducerConsumerSystem:
    app = ProducerConsumerSystem()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
