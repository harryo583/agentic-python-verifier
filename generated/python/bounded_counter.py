"""
PlusCal module: BoundedCounter

Inductive invariant (Inv):
    Inv ==
      /\ counter \in 0..MaxValue
      /\ pc \in {"Loop", "Increment"}

Target property:
    Property == counter <= MaxValue
"""

from typing import Optional


# Module-level state mirroring the PlusCal variables.
counter: int = 0
pc: str = "Loop"
MaxValue: int = 0


def _check_inv() -> None:
    # /\ counter \in 0..MaxValue
    assert counter in range(0, MaxValue + 1), (
        f"Inv violated: counter={counter} not in 0..{MaxValue}"
    )
    # /\ pc \in {"Loop", "Increment"}
    assert pc in {"Loop", "Increment"}, f"Inv violated: pc={pc!r}"


def _step_loop() -> None:
    """Label `Loop`: while TRUE, fall through to Increment."""
    global pc
    _check_inv()
    assert pc == "Loop"
    pc = "Increment"
    _check_inv()


def _step_increment() -> None:
    """Label `Increment`: bounded increment of counter."""
    global counter, pc
    _check_inv()
    assert pc == "Increment"
    if counter < MaxValue:
        counter = counter + 1
    else:
        counter = counter
    pc = "Loop"
    _check_inv()


def run_bounded_counter(max_value: int, steps: Optional[int] = None) -> int:
    """Execute the BoundedCounter algorithm.

    Since the PlusCal algorithm has an infinite `while TRUE` loop, this
    driver runs for a finite number of high-level iterations (`steps`).
    If `steps` is None, it runs until `counter` reaches `MaxValue` and
    then performs a few more iterations to exercise the else-branch.
    """
    global counter, pc, MaxValue

    assert max_value >= 0, "MaxValue must be non-negative"
    MaxValue = max_value
    counter = 0
    pc = "Loop"
    _check_inv()

    if steps is None:
        # Enough iterations to saturate the counter and then exercise the
        # idempotent else-branch a few times.
        steps = max_value + 5

    for _ in range(steps):
        # One iteration of the outer `while TRUE`: Loop -> Increment -> Loop.
        _step_loop()
        _step_increment()
        # Property check (safety) — implied by Inv.
        assert counter <= MaxValue, "Property violated: counter > MaxValue"

    _check_inv()
    return counter


if __name__ == "__main__":
    final = run_bounded_counter(max_value=5)
    print(f"final counter = {final}")
