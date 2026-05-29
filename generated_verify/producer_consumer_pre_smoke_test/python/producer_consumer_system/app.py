"""Composed parent for ProducerConsumerSystem.

Property:
  /\\ Len(buffer) \\in 0..Capacity
  /\\ IsPrefix(received, generated)
  /\\ next_item <= MaxItem + 1
"""

from __future__ import annotations

import icontract

from ._trace import log_action
from .bounded_queue import BoundedQueue
from .producer import Producer
from .consumer import Consumer


def _is_prefix(a, b) -> bool:
    if len(a) > len(b):
        return False
    for i in range(len(a)):
        if a[i] != b[i]:
            return False
    return True


@icontract.invariant(lambda self: 0 <= len(self.queue.buffer) <= self.queue.Capacity)
@icontract.invariant(lambda self: _is_prefix(self.consumer.received, self.producer.generated))
@icontract.invariant(lambda self: self.producer.next_item <= self.producer.MaxItem + 1)
@icontract.invariant(lambda self: all(1 <= x <= 10 for x in self.queue.buffer))
@icontract.invariant(lambda self: all(1 <= x <= self.producer.MaxItem for x in self.producer.generated))
@icontract.invariant(lambda self: all(1 <= x <= self.producer.MaxItem for x in self.consumer.received))
@icontract.invariant(lambda self: self.producer.next_item >= 1)
class ProducerConsumerSystem:
    """Composed system: Producer -> BoundedQueue -> Consumer."""

    def __init__(self, capacity: int = 5, max_item: int = 10, max_len: int = 20) -> None:
        self.queue = BoundedQueue(capacity=capacity, max_len=max_len)
        self.producer = Producer(max_item=max_item, max_len=max_len)
        self.consumer = Consumer(max_len=max_len)
        self._tick = 0

    def step_produce(self) -> None:
        """Producer produces an item and enqueues it if possible."""
        if self.producer.next_item > self.producer.MaxItem:
            return
        if len(self.queue.buffer) >= self.queue.Capacity:
            return
        item = self.producer.produce()
        if item is None:
            return
        self.queue.enqueue(item)
        log_action(
            "ProducerConsumerSystem.Produce",
            {
                "buffer": list(self.queue.buffer),
                "generated": list(self.producer.generated),
                "next_item": self.producer.next_item,
                "received": list(self.consumer.received),
                "sum": self.consumer.sum,
            },
        )

    def step_consume(self) -> None:
        """Consumer dequeues an item from the queue and consumes it."""
        if len(self.queue.buffer) == 0:
            return
        item = self.queue.dequeue()
        if item is None:
            return
        self.consumer.consume(item)
        log_action(
            "ProducerConsumerSystem.Consume",
            {
                "buffer": list(self.queue.buffer),
                "generated": list(self.producer.generated),
                "next_item": self.producer.next_item,
                "received": list(self.consumer.received),
                "sum": self.consumer.sum,
            },
        )

    def step(self) -> None:
        """One atomic step of the composed system; alternates producer/consumer."""
        if self._tick % 2 == 0:
            self.step_produce()
        else:
            self.step_consume()
        self._tick += 1
        log_action(
            "ProducerConsumerSystem.Step",
            {
                "tick": self._tick,
                "buffer": list(self.queue.buffer),
                "generated": list(self.producer.generated),
                "next_item": self.producer.next_item,
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
