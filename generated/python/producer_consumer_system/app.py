"""Composed parent for ProducerConsumerSystem.

Property: Len(buffer) in 0..3 /\\ IsPrefix(received, generated) /\\ nextItem <= 4.
"""

from __future__ import annotations

import icontract

from ._trace import log_action
from .bounded_queue import BoundedQueue
from .producer import Producer
from .consumer import Consumer


def _is_prefix(s: list[int], t: list[int]) -> bool:
    return len(s) <= len(t) and all(s[i] == t[i] for i in range(len(s)))


@icontract.invariant(lambda self: 0 <= len(self.queue.buffer) <= 3)
@icontract.invariant(lambda self: _is_prefix(self.consumer.received, self.producer.generated))
@icontract.invariant(lambda self: self.producer.nextItem in range(1, 5))
class ProducerConsumerSystem:
    def __init__(self) -> None:
        self.queue = BoundedQueue(capacity=3)
        self.producer = Producer(MaxItem=3)
        self.consumer = Consumer(MaxLen=3)
        # Deterministic scheduler turn: 0 = produce+enqueue, 1 = dequeue+consume.
        self._turn: int = 0

    def step(self) -> None:
        """One atomic step of the composed system.

        We interleave a produce-then-enqueue atomic action with a
        dequeue-then-consume atomic action, so the buffer never reflects an
        intermediate state where generated/received drift apart in a way that
        breaks IsPrefix.
        """
        if self._turn == 0:
            # Produce + enqueue atomically (if both children can advance).
            if (
                self.producer.pc == "Loop"
                and self.producer.nextItem <= self.producer.MaxItem
                and len(self.queue.buffer) < self.queue.capacity
                and self.queue.pc == "Loop"
            ):
                item = self.producer.nextItem
                self.producer.produce()
                self.queue.enqueue(item)
            else:
                # stutter the producer toward Finish/Done if it can't loop
                if self.producer.pc in {"Loop", "Finish"} and (
                    self.producer.nextItem > self.producer.MaxItem
                    or self.producer.pc == "Finish"
                ):
                    self.producer.produce()
            self._turn = 1
        else:
            # Dequeue + consume atomically.
            if (
                len(self.queue.buffer) > 0
                and self.queue.pc == "Loop"
                and self.consumer.pc == "Loop"
                and len(self.consumer.received) < self.consumer.MaxLen
            ):
                v = self.queue.buffer[0]
                self.queue.dequeue()
                self.consumer.consume(v)
            else:
                # stutter the consumer if needed
                if self.consumer.pc in {"Loop", "Finish"}:
                    # advance only if it would not require an enqueued value
                    if self.consumer.pc == "Finish" or len(self.consumer.received) >= self.consumer.MaxLen:
                        # consume(v) with dummy value is unsafe; the consumer's
                        # stutter branches don't require v to be enqueued, but
                        # the method still requires v in 1..10. Pass a benign 1.
                        try:
                            self.consumer.consume(1)
                        except Exception:
                            pass
            self._turn = 0

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
