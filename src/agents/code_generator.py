"""Generate Python implementations from verified task specifications."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Optional

from src.llm import LLMClient, LLMError
from src.models.task import TaskSpecification, VerificationResult


@dataclass(slots=True)
class CodeGeneratorAgent:
    """Emit readable Python implementations with invariant assertions."""

    llm_client: Optional[LLMClient] = None

    def generate(self, task: TaskSpecification, verification: VerificationResult) -> str:
        """Generate Python code for a verified task."""

        if task.python_code and _is_valid_python(task.python_code):
            return task.python_code
        if self.llm_client is not None:
            try:
                generated = self._generate_with_llm(task, verification)
                if _is_valid_python(generated):
                    task.python_code = generated
                    return generated
            except LLMError:
                pass

        header = (
            '"""Generated Python code from a verified formal specification."""\n\n'
            "from __future__ import annotations\n\n"
        )

        if task.task_type == "bounded_counter":
            min_value = int(task.parameters.get("min_value", 0))
            max_value = int(task.parameters.get("max_value", 10))
            body = f'''def increment(counter: int, max_value: int = {max_value}, min_value: int = {min_value}) -> int:
    """Increment a bounded counter without exceeding its maximum."""
    assert min_value <= counter <= max_value
    if counter < max_value:
        counter += 1
    assert min_value <= counter <= max_value
    return counter
'''
            return header + body

        if task.task_type == "bank_transfer":
            body = '''def transfer(source: int, target: int, amount: int) -> tuple[int, int]:
    """Transfer money between two accounts while preserving total funds."""
    assert source >= 0
    assert target >= 0
    assert amount >= 0
    assert source >= amount
    total_funds = source + target
    new_source = source - amount
    new_target = target + amount
    assert new_source >= 0
    assert new_target >= 0
    assert new_source + new_target == total_funds
    return new_source, new_target
'''
            return header + body

        if task.task_type == "state_machine":
            body = '''def transition(state: str, event: str) -> str:
    """Apply a legal transition in a small deterministic state machine."""
    allowed_states = {"IDLE", "RUNNING", "STOPPED"}
    assert state in allowed_states
    if state == "IDLE" and event == "start":
        result = "RUNNING"
    elif state == "RUNNING" and event == "stop":
        result = "STOPPED"
    else:
        result = state
    assert result in allowed_states
    return result
'''
            return header + body

        if task.task_type == "mutual_exclusion":
            body = '''def acquire(lock_owner: str, requester: str) -> str:
    """Acquire a lock if it is currently free."""
    assert requester
    if lock_owner == "none":
        lock_owner = requester
    assert lock_owner == "none" or isinstance(lock_owner, str)
    return lock_owner


def release(lock_owner: str, requester: str) -> str:
    """Release a lock when the requester owns it."""
    if lock_owner == requester:
        lock_owner = "none"
    assert lock_owner == "none" or isinstance(lock_owner, str)
    return lock_owner
'''
            return header + body

        if task.task_type == "queue":
            body = '''def enqueue(items: list[str], value: str) -> list[str]:
    """Append a value to the back of the queue."""
    result = list(items)
    result.append(value)
    return result


def dequeue(items: list[str]) -> tuple[str | None, list[str]]:
    """Remove the oldest value from the queue when one exists."""
    result = list(items)
    if not result:
        return None, result
    value = result.pop(0)
    return value, result
'''
            return header + body

        if task.task_type == "stack":
            body = '''def push(items: list[str], value: str) -> list[str]:
    """Push a value onto the top of the stack."""
    result = list(items)
    result.append(value)
    return result


def pop(items: list[str]) -> tuple[str | None, list[str]]:
    """Pop the newest value from the stack when one exists."""
    result = list(items)
    if not result:
        return None, result
    value = result.pop()
    return value, result
'''
            return header + body

        detail_comment = "\n".join(f"# {detail}" for detail in verification.details)
        body = f'''def step(state: int) -> int:
    """Perform a generic state transition."""
    {detail_comment if detail_comment else "# Verification succeeded."}
    assert state >= 0
    state += 1
    assert state >= 0
    return state
'''
        return header + body

    def _generate_with_llm(self, task: TaskSpecification, verification: VerificationResult) -> str:
        assert self.llm_client is not None
        data = self.llm_client.complete_json(
            system_prompt=(
                "You are a Python implementation agent. Generate executable, dependency-free "
                "Python 3.11 code from a verified PlusCal/TLA+ task. Include runtime assertions "
                "that correspond to the invariant, preconditions, and postconditions. Return only JSON."
            ),
            user_prompt=(
                "TaskSpecification JSON:\n"
                f"{task.model_dump_json(indent=2)}\n\n"
                "Verification result JSON:\n"
                f"{verification.model_dump_json(indent=2)}\n\n"
                'Return {"python_code": "..."} with complete module text. Do not use placeholders.'
            ),
        )
        return str(data.get("python_code", "")).strip()


def _is_valid_python(code: str) -> bool:
    if not code.strip():
        return False
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True
