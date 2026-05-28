"""
PlusCal module: AccountTransfer

Inductive invariant (Inv):
    Inv ==
        /\ a \in 0..Total
        /\ b \in 0..Total
        /\ a + b = Total

Target property (Property):
    Property ==
        /\ a >= 0
        /\ b >= 0
        /\ a + b = Total

This module is a faithful translation of the PlusCal algorithm above.
The `Loop` label is a non-terminating `while TRUE` with a non-deterministic
`either/or` choice; the Python runner exercises the algorithm for a bounded
number of steps using `random` to resolve the non-determinism.
"""

from __future__ import annotations

import random
from typing import Optional


# Module-level state mirrors PlusCal `variables`.
InitA: int = 0
InitB: int = 0
MaxAmount: int = 0
Total: int = 0

a: int = 0
b: int = 0


def _check_inv() -> None:
    """Enforce the conjuncts of Inv."""
    # /\ a \in 0..Total
    assert a in range(0, Total + 1), f"Inv violated: a={a} not in 0..{Total}"
    # /\ b \in 0..Total
    assert b in range(0, Total + 1), f"Inv violated: b={b} not in 0..{Total}"
    # /\ a + b = Total
    assert a + b == Total, f"Inv violated: a+b={a+b} != Total={Total}"


def _init(init_a: int, init_b: int, max_amount: int) -> None:
    """Initialise variables according to the PlusCal `variables` clause."""
    global InitA, InitB, MaxAmount, Total, a, b
    InitA = init_a
    InitB = init_b
    MaxAmount = max_amount
    Total = InitA + InitB
    a = InitA
    b = InitB
    _check_inv()


def step(branch: str, amt: int) -> None:
    """
    One execution of the body of the `Loop` label.

    `branch` selects the `either`/`or` arm:
       - "either": transfer amt from a to b (if a >= amt)
       - "or"    : transfer amt from b to a (if b >= amt)
    """
    global a, b
    # Entry assertion: Inv holds on entry.
    _check_inv()

    assert branch in ("either", "or")
    assert amt in range(1, MaxAmount + 1), \
        f"amt={amt} not in 1..{MaxAmount}"

    if branch == "either":
        # with amt \in 1..MaxAmount do
        #   if a >= amt then a := a - amt; b := b + amt; end if;
        if a >= amt:
            a = a - amt
            b = b + amt
    else:  # branch == "or"
        # with amt \in 1..MaxAmount do
        #   if b >= amt then b := b - amt; a := a + amt; end if;
        if b >= amt:
            b = b - amt
            a = a + amt

    # Exit assertion: Inv still holds.
    _check_inv()


def run_account_transfer(
    init_a: int = 5,
    init_b: int = 5,
    max_amount: int = 3,
    steps: int = 1000,
    seed: Optional[int] = 0,
) -> tuple[int, int]:
    """
    Entry point: initialise the state and execute `steps` iterations of the
    PlusCal `Loop` label, resolving the non-deterministic `either/or` and the
    `with amt \\in 1..MaxAmount` choice using `random`.

    Returns the final (a, b).
    """
    rng = random.Random(seed)
    _init(init_a, init_b, max_amount)

    for _ in range(steps):
        branch = rng.choice(("either", "or"))
        amt = rng.randint(1, MaxAmount)
        step(branch, amt)

    # Property is implied by Inv; double-check.
    assert a >= 0 and b >= 0 and a + b == Total
    return a, b


if __name__ == "__main__":
    final = run_account_transfer()
    print(f"Final state: a={final[0]}, b={final[1]}, total={sum(final)}")
