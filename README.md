# Agentic Python Verifier

## Project Overview

`agentic-python-verifier` is a correctness-first prototype that converts a natural language algorithm description into:

1. a structured task model,
2. a PlusCal specification,
3. a TLA+ verification step, and
4. executable Python code.

The system is intentionally designed for teaching and experimentation in a university formal methods or systems course. It can run fully offline with deterministic fallbacks, or it can call an LLM through Ollama, OpenAI-compatible chat APIs, or Anthropic to synthesize task models, PlusCal/TLA+ specifications, inductive invariants, refinements, and Python code for prompts outside the curated examples.

Supported example domains include:

- bounded counters,
- bank transfers,
- finite state machines,
- mutual exclusion,
- queue operations, and
- stack operations.

## System Architecture

The project uses a small agent pipeline:

- `PlannerAgent`: parses the natural language prompt into a formalized task, using the configured LLM first when available.
- `SpecificationGenerator`: maps the task into a PlusCal/TLA+ module with an invariant, property, and proof-obligation markers.
- `VerifierAgent`: executes TLC when available or a deterministic mock verifier otherwise.
- `RefinerAgent`: improves a failing task/specification using structured verifier feedback.
- `CodeGeneratorAgent`: emits readable Python with assertions and docstrings derived from the verified task.

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

Use Ollama for arbitrary prompts:

```bash
ollama serve
python -m src.main "Implement a two-phase commit coordinator with abort on timeout" \
  --llm-provider ollama \
  --llm-model llama3.1
```

Use an OpenAI-compatible API:

```bash
export LLM_API_KEY=your_api_key
python -m src.main "Implement a bounded retry scheduler with no negative retry count" \
  --llm-provider openai \
  --llm-model gpt-4o
```

Environment variables are also supported:

```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3.1
export LLM_BASE_URL=http://localhost:11434
```

Supported `LLM_PROVIDER` values are `offline`, `ollama`, `openai`, `openai-compatible`, and `anthropic`. `offline` is the default and uses the deterministic local templates.

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

- LLM-generated PlusCal/TLA+ is validated structurally before use, but complex prompts may still need stronger TLC configuration and bounds.
- The mock verifier checks consistency and invariant coverage but is not a substitute for exhaustive model checking.
- Python generation targets clarity and safety rather than performance.
- Future work could add SMT-backed proof-obligation checks, richer TLA+ configs, PlusCal translation automation, and benchmark-driven prompt tuning.
