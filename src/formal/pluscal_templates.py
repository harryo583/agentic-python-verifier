"""PlusCal/TLA+ templates for supported task classes."""

from __future__ import annotations

from jinja2 import Template

from src.models.task import TaskSpecification


COUNTER_TEMPLATE = Template(
    """------------------------------ MODULE {{ task.name }} ------------------------------
EXTENDS Integers

CONSTANTS MinValue, MaxValue

(* --algorithm {{ task.name }}
variables counter = {{ minimum }};
begin
  Increment:
    if counter < {{ maximum }} then
      counter := counter + 1;
    end if;
end algorithm; *)

Invariant == counter >= {{ minimum }} /\\ counter <= {{ maximum }}
Property == Invariant

\\* Proof obligations:
\\* Initiation: Init => Invariant
\\* Consecution: Invariant /\\ Next => Invariant'
\\* Property Implication: Invariant => Property

=============================================================================
"""
)

BANK_TRANSFER_TEMPLATE = Template(
    """------------------------------ MODULE {{ task.name }} ------------------------------
EXTENDS Integers

(* --algorithm {{ task.name }}
variables source = {{ source }}, target = {{ target }}, amount = {{ amount }};
begin
  Transfer:
    if amount >= 0 /\\ source >= amount then
      source := source - amount;
      target := target + amount;
    end if;
end algorithm; *)

Invariant == source >= 0 /\\ target >= 0 /\\ source + target = {{ total }}
Property == Invariant

\\* Proof obligations:
\\* Initiation: Init => Invariant
\\* Consecution: Invariant /\\ Next => Invariant'
\\* Property Implication: Invariant => Property

=============================================================================
"""
)

STATE_MACHINE_TEMPLATE = Template(
    """------------------------------ MODULE {{ task.name }} ------------------------------
EXTENDS Sequences

(* --algorithm {{ task.name }}
variables state = "{{ initial_state }}", event = "start";
begin
  Transition:
    if state = "IDLE" /\\ event = "start" then
      state := "RUNNING";
    elsif state = "RUNNING" /\\ event = "stop" then
      state := "STOPPED";
    end if;
end algorithm; *)

Invariant == state \\in {"IDLE", "RUNNING", "STOPPED"}
Property == Invariant

\\* Proof obligations:
\\* Initiation: Init => Invariant
\\* Consecution: Invariant /\\ Next => Invariant'
\\* Property Implication: Invariant => Property

=============================================================================
"""
)

MUTEX_TEMPLATE = Template(
    """------------------------------ MODULE {{ task.name }} ------------------------------
EXTENDS Sequences

(* --algorithm {{ task.name }}
variables lock_owner = "{{ unlocked }}", requester = "p1";
begin
  Acquire:
    if lock_owner = "{{ unlocked }}" then
      lock_owner := requester;
    end if;
  Release:
    if lock_owner = requester then
      lock_owner := "{{ unlocked }}";
    end if;
end algorithm; *)

Invariant == lock_owner = "{{ unlocked }}" \\/ lock_owner \\in {"p1", "p2"}
Property == Invariant

\\* Proof obligations:
\\* Initiation: Init => Invariant
\\* Consecution: Invariant /\\ Next => Invariant'
\\* Property Implication: Invariant => Property

=============================================================================
"""
)

QUEUE_TEMPLATE = Template(
    """------------------------------ MODULE {{ task.name }} ------------------------------
EXTENDS Sequences

(* --algorithm {{ task.name }}
variables items = <<>>;
begin
  Enqueue:
    items := Append(items, "x");
  Dequeue:
    if Len(items) > 0 then
      items := Tail(items);
    end if;
end algorithm; *)

Invariant == items \\in Seq({"x", "y", "z"})
Property == Invariant

\\* Proof obligations:
\\* Initiation: Init => Invariant
\\* Consecution: Invariant /\\ Next => Invariant'
\\* Property Implication: Invariant => Property

=============================================================================
"""
)

STACK_TEMPLATE = Template(
    """------------------------------ MODULE {{ task.name }} ------------------------------
EXTENDS Sequences

(* --algorithm {{ task.name }}
variables items = <<>>;
begin
  Push:
    items := Append(items, "x");
  Pop:
    if Len(items) > 0 then
      items := SubSeq(items, 1, Len(items) - 1);
    end if;
end algorithm; *)

Invariant == items \\in Seq({"x", "y", "z"})
Property == Invariant

\\* Proof obligations:
\\* Initiation: Init => Invariant
\\* Consecution: Invariant /\\ Next => Invariant'
\\* Property Implication: Invariant => Property

=============================================================================
"""
)

GENERIC_TEMPLATE = Template(
    """------------------------------ MODULE {{ task.name }} ------------------------------
EXTENDS Integers

(* --algorithm {{ task.name }}
variables state = 0;
begin
  Step:
    state := state + 1;
end algorithm; *)

Invariant == state >= 0
Property == Invariant

\\* Proof obligations:
\\* Initiation: Init => Invariant
\\* Consecution: Invariant /\\ Next => Invariant'
\\* Property Implication: Invariant => Property

=============================================================================
"""
)


def render_pluscal(task: TaskSpecification) -> str:
    """Render a TLA+ module containing a PlusCal algorithm for the task."""

    if task.task_type == "bounded_counter":
        minimum = int(task.parameters.get("min_value", 0))
        maximum = int(task.parameters.get("max_value", 10))
        return COUNTER_TEMPLATE.render(task=task, minimum=minimum, maximum=maximum)
    if task.task_type == "bank_transfer":
        source = int(task.parameters.get("default_source", 100))
        target = int(task.parameters.get("default_target", 50))
        amount = int(task.parameters.get("default_amount", 10))
        return BANK_TRANSFER_TEMPLATE.render(
            task=task,
            source=source,
            target=target,
            amount=amount,
            total=source + target,
        )
    if task.task_type == "state_machine":
        return STATE_MACHINE_TEMPLATE.render(
            task=task,
            initial_state=task.parameters.get("initial_state", "IDLE"),
        )
    if task.task_type == "mutual_exclusion":
        return MUTEX_TEMPLATE.render(task=task, unlocked=task.parameters.get("unlocked", "none"))
    if task.task_type == "queue":
        return QUEUE_TEMPLATE.render(task=task)
    if task.task_type == "stack":
        return STACK_TEMPLATE.render(task=task)
    return GENERIC_TEMPLATE.render(task=task)
