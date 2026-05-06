# Agentic Python Verifier

## Project Overview

`agentic-python-verifier` is a correctness-first prototype that converts a natural language algorithm description into:

1. a structured task model,
2. a PlusCal specification,
3. a TLA+ verification step, and
4. executable Python code.

The system is intentionally designed for teaching and experimentation in a university formal methods or systems course. It runs locally without requiring any external LLM API and falls back to deterministic mock behavior when TLC is unavailable.

Supported example domains include:

- bounded counters,
- bank transfers,
- finite state machines,
- mutual exclusion,
- queue operations, and
- stack operations.

## System Architecture

The project uses a small agent pipeline:

- `PlannerAgent`: parses the natural language prompt into a formalized task.
- `SpecificationGenerator`: maps the task into a PlusCal/TLA+ module.
- `VerifierAgent`: executes TLC when available or a deterministic mock verifier otherwise.
- `RefinerAgent`: improves a failing task/specification with rule-based feedback.
- `CodeGeneratorAgent`: emits readable Python with assertions and docstrings.

## ASCII Diagram of the Pipeline

```text
+-------------------------------+
| Natural Language Specification|
+---------------+---------------+
                |
                v
      +---------+----------+
      | Planner Agent      |
      | Structured Task    |
      +---------+----------+
                |
                v
      +---------+----------+
      | Spec Generator     |
      | PlusCal + TLA+     |
      +---------+----------+
                |
                v
      +---------+----------+
      | Verifier Agent     |
      | TLC or Mock TLC    |
      +----+-----------+---+
           |           |
        pass|           |fail
           v           v
   +-------+---+   +---+--------+
   | Code Gen |   | Refiner     |
   | Python   |   | Feedback    |
   +-------+--+   +---+--------+
           |          |
           +----------+
                retry
```

## Installation Instructions

```bash
pip install -r requirements.txt
```

Python 3.11 or newer is required.

## Usage Examples

Run the end-to-end pipeline:

```bash
python -m src.main "Implement a bounded counter from 0 to 10"
```

Write artifacts to custom paths:

```bash
python -m src.main "Implement a bank transfer that preserves total balance" --output generated
```

Request explicit verification status output:

```bash
python -m src.main "Implement a simple queue with enqueue and dequeue" --verify --verbose
```

## Example Outputs

Example natural language prompt:

```text
Implement a bounded counter from 0 to 10
```

Example generated PlusCal snippet:

```tla
--algorithm BoundedCounter
variables counter = 0;
begin
  Increment:
    if counter < 10 then
      counter := counter + 1;
    end if;
end algorithm;
```

Example generated Python snippet:

```python
def increment(counter: int, max_value: int = 10) -> int:
    """Increment a bounded counter without exceeding its maximum."""
    assert 0 <= counter <= max_value
    if counter < max_value:
        counter += 1
    assert 0 <= counter <= max_value
    return counter
```

## Instructions for Installing TLA+ and TLC

This project works without TLC, but real model checking is supported when TLC is available on your machine.

1. Install Java 11 or newer.
2. Download the TLA+ tools from the official TLA+ release distribution.
3. Ensure the `tla2tools.jar` file is available locally.
4. Set `TLA_TLC_JAR` in your environment to the absolute path of `tla2tools.jar`.

Example:

```bash
export TLA_TLC_JAR=/absolute/path/to/tla2tools.jar
```

When `TLA_TLC_JAR` is configured, the verifier will attempt a real TLC run. Otherwise it will use a deterministic mock verifier.

## Limitations and Future Work

- The natural language planner is rule-based rather than LLM-powered.
- PlusCal generation relies on curated templates for supported problem classes.
- The mock verifier checks consistency and invariant coverage but is not a substitute for exhaustive model checking.
- Python generation targets clarity and safety rather than performance.
- Future work could add richer template synthesis, SMT-backed refinement, richer TLA+ configs, and optional OpenAI or Anthropic adapters.
