"""Composed parent for ProducerConsumerSystem.

Property: Len(buffer) in 0..Capacity /\\ IsPrefix(received, generated) /\\ nextItem <= MaxItem + 1.
"""

from __future__ import annotations

import icontract

from ._trace import log_action
from .bounded_queue import BoundedQueue
from .producer import Producer
from .consumer import Consumer


CAPACITY = 4
MAX_ITEM = 8
MAX_LEN = 4


def _is_prefix(s, t) -> bool:
    if len(s) > len(t):
        return False
    for i, x in enumerate(s):
        if x != t[i]:
            return False
    return True


@icontract.invariant(lambda self: 0 <= len(self.queue.buffer) <= self.capacity)
@icontract.invariant(lambda self: _is_prefix(self.consumer.received, self.producer.generated))
@icontract.invariant(lambda self: 1 <= self.producer.nextItem <= self.max_item + 1)
class ProducerConsumerSystem:
    """Parent composition wiring BoundedQueue, Producer, and Consumer.

    Matches Spec: Init = Q!Init /\\ P!Init /\\ C!Init; Next interleaves
    Q!Next, P!Next, C!Next (each with the others' vars UNCHANGED).
    """

    def __init__(self) -> None:
        self.capacity = CAPACITY
        self.max_item = MAX_ITEM
        self.max_len = MAX_LEN
        self.queue = BoundedQueue(capacity=self.capacity)
        self.producer = Producer(max_item=self.max_item)
        self.consumer = Consumer()
        self._tick = 0

    def _produce_step(self) -> None:
        """P!Next: producer advances; buffer/received/runningSum UNCHANGED."""
        if self.producer.nextItem <= self.max_item:
            self.producer.step()

    def _enqueue_step(self) -> None:
        """Q!Next (enqueue side): move a generated-but-not-buffered item into buffer."""
        # Items already buffered or consumed shouldn't be re-enqueued.
        # The "in-flight" prefix is producer.generated; what's already passed
        # downstream is consumer.received plus what's currently in queue.buffer.
        delivered = len(self.consumer.received) + len(self.queue.buffer)
        if delivered < len(self.producer.generated) and len(self.queue.buffer) < self.capacity:
            item = self.producer.generated[delivered]
            self.queue.enqueue(item)

    def _consume_step(self) -> None:
        """C!Next: consumer dequeues head of buffer; generated/nextItem UNCHANGED."""
        if len(self.queue.buffer) > 0:
            head = self.queue.buffer[0]
            # Dequeue by mutating the buffer in place to keep the BoundedQueue
            # invariant intact.
            self.queue.buffer = self.queue.buffer[1:]
            self.consumer.consume(head)

    def step(self) -> None:
        """One atomic step of the composed system (deterministic round-robin)."""
        phase = self._tick % 3
        if phase == 0:
            self._produce_step()
        elif phase == 1:
            self._enqueue_step()
        else:
            self._consume_step()
        self._tick += 1
        log_action(
            "ProducerConsumerSystem.Step",
            {
                "buffer": list(self.queue.buffer),
                "generated": list(self.producer.generated),
                "nextItem": self.producer.nextItem,
                "received": list(self.consumer.received),
                "runningSum": self.consumer.runningSum,
            },
        )


def run(steps: int = 50) -> ProducerConsumerSystem:
    app = ProducerConsumerSystem()
    for _ in range(steps):
        app.step()
    return app


if __name__ == "__main__":
    run()
