"""Planner agent that maps natural language to a structured task."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.models.task import TaskSpecification


@dataclass(slots=True)
class PlannerAgent:
    """Rule-based planner for supported educational examples."""

    def plan(self, prompt: str) -> TaskSpecification:
        """Parse a natural language prompt into a structured task specification."""

        text = prompt.strip()
        lowered = text.lower()

        if "counter" in lowered:
            return self._plan_bounded_counter(text)
        if "transfer" in lowered or "account" in lowered or "balance" in lowered:
            return self._plan_bank_transfer(text)
        if "state machine" in lowered or "fsm" in lowered:
            return self._plan_state_machine(text)
        if "mutual exclusion" in lowered or "critical section" in lowered or "mutex" in lowered:
            return self._plan_mutual_exclusion(text)
        if "queue" in lowered:
            return self._plan_queue(text)
        if "stack" in lowered:
            return self._plan_stack(text)
        return self._plan_generic(text)

    def _plan_bounded_counter(self, prompt: str) -> TaskSpecification:
        numbers = [int(match) for match in re.findall(r"-?\d+", prompt)]
        minimum = numbers[0] if len(numbers) >= 2 else 0
        maximum = numbers[1] if len(numbers) >= 2 else (numbers[0] if numbers else 10)
        if len(numbers) == 1:
            minimum = 0
        return TaskSpecification(
            name="BoundedCounter",
            slug="bounded_counter",
            task_type="bounded_counter",
            description=prompt,
            inputs=["counter"],
            outputs=["counter"],
            state_variables={"counter": minimum},
            preconditions=[f"{minimum} <= counter <= {maximum}"],
            postconditions=[f"{minimum} <= result <= {maximum}"],
            invariants=[f"{minimum} <= counter <= {maximum}"],
            operations=["increment"],
            parameters={"min_value": minimum, "max_value": maximum},
            assumptions=["Increment saturates at the upper bound."],
        )

    def _plan_bank_transfer(self, prompt: str) -> TaskSpecification:
        return TaskSpecification(
            name="BankTransfer",
            slug="bank_transfer",
            task_type="bank_transfer",
            description=prompt,
            inputs=["source", "target", "amount"],
            outputs=["source", "target"],
            state_variables={"source": 100, "target": 50, "amount": 10},
            preconditions=["source >= 0", "target >= 0", "amount >= 0", "source >= amount"],
            postconditions=[
                "new_source >= 0",
                "new_target >= 0",
                "new_source + new_target = source + target",
            ],
            invariants=["source >= 0", "target >= 0", "source + target = total_funds"],
            operations=["transfer"],
            parameters={"default_source": 100, "default_target": 50, "default_amount": 10},
            assumptions=["Transfers preserve total funds and reject overdrafts."],
        )

    def _plan_state_machine(self, prompt: str) -> TaskSpecification:
        return TaskSpecification(
            name="StateMachine",
            slug="state_machine",
            task_type="state_machine",
            description=prompt,
            inputs=["state", "event"],
            outputs=["state"],
            state_variables={"state": "IDLE"},
            preconditions=["state is a known state", "event is a known event"],
            postconditions=["result is a known state"],
            invariants=["state in {'IDLE', 'RUNNING', 'STOPPED'}"],
            operations=["transition"],
            parameters={"initial_state": "IDLE"},
            assumptions=["Only legal transitions are allowed."],
        )

    def _plan_mutual_exclusion(self, prompt: str) -> TaskSpecification:
        return TaskSpecification(
            name="MutualExclusion",
            slug="mutual_exclusion",
            task_type="mutual_exclusion",
            description=prompt,
            inputs=["lock_owner", "requester"],
            outputs=["lock_owner"],
            state_variables={"lock_owner": "none"},
            preconditions=["requester is a process identifier"],
            postconditions=["at most one process owns the lock"],
            invariants=["lock_owner is either 'none' or a single process identifier"],
            operations=["acquire", "release"],
            parameters={"unlocked": "none"},
            assumptions=["The lock is exclusive and releases are idempotent."],
        )

    def _plan_queue(self, prompt: str) -> TaskSpecification:
        return TaskSpecification(
            name="QueueOperations",
            slug="queue_operations",
            task_type="queue",
            description=prompt,
            inputs=["items", "value"],
            outputs=["items"],
            state_variables={"items": []},
            preconditions=["items is a list"],
            postconditions=["enqueue appends", "dequeue removes oldest when present"],
            invariants=["queue order is FIFO"],
            operations=["enqueue", "dequeue"],
            parameters={},
            assumptions=["Dequeue from an empty queue returns None."],
        )

    def _plan_stack(self, prompt: str) -> TaskSpecification:
        return TaskSpecification(
            name="StackOperations",
            slug="stack_operations",
            task_type="stack",
            description=prompt,
            inputs=["items", "value"],
            outputs=["items"],
            state_variables={"items": []},
            preconditions=["items is a list"],
            postconditions=["push appends", "pop removes newest when present"],
            invariants=["stack order is LIFO"],
            operations=["push", "pop"],
            parameters={},
            assumptions=["Pop from an empty stack returns None."],
        )

    def _plan_generic(self, prompt: str) -> TaskSpecification:
        return TaskSpecification(
            name="GenericTask",
            slug="generic_task",
            task_type="generic",
            description=prompt,
            inputs=["state"],
            outputs=["state"],
            state_variables={"state": 0},
            preconditions=["state is valid"],
            postconditions=["result satisfies the specification"],
            invariants=["state remains well-formed"],
            operations=["step"],
            parameters={},
            assumptions=["Generic tasks use a conservative mock specification."],
        )
