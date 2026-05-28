# Evaluator Guide

This repository demonstrates a finite-domain proof loop:

1. An LLM emits a PlusCal algorithm, candidate inductive invariant `Inv`,
   safety predicate `Property`, and finite `CONSTANTS`.
2. The verifier translates PlusCal with `pcal.trans`.
3. TLC checks three obligations: a reachable invariant run from `Spec`, an
   explicit one-step inductiveness check `Inv /\ Next => Inv'`, and
   `Inv => Property`.
4. Only after all three pass does the refinement agent emit Python with
   runtime assertions derived from `Inv`.

The project should be evaluated as a finite TLC-based inductive checker. It
does not claim unbounded proofs, TLAPS proofs, or stable live Anthropic results.

## Offline Evaluation

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run deterministic tests:

```bash
pytest tests/ -m "not integration"
```

These tests require no API key and no `tla2tools.jar`. They validate the Python
orchestration, data models, mocked agent loop, config generation, and TLC-output
parsing against local fixtures.

## Gated Integration Tests

Run local TLC integration with a downloaded TLA+ tools jar:

```bash
export TLA2TOOLS_JAR=/absolute/path/to/tla2tools.jar
pytest tests/test_tlc_runner.py -m integration
```

Run the optional live end-to-end smoke test:

```bash
export TLA2TOOLS_JAR=/absolute/path/to/tla2tools.jar
export ANTHROPIC_API_KEY=sk-ant-...
pytest tests/test_e2e.py -m integration
```

The live test can incur API costs and can vary because it depends on model
responses. Do not treat a single live run as a benchmark pass rate.

## Manual Benchmark Prompts

Prompt files live in `examples/`. They are intentionally small:

- `bounded_counter.txt`: one integer counter bounded by a finite maximum.
- `bank_transfer.txt`: two-account transfer with fixed finite total.
- `resource_semaphore.txt`: finite clients and finite semaphore capacity.
- `ring_buffer.txt`: capacity-bounded queue over a finite item set.

Example manual run:

```bash
python -m src.main "$(cat examples/bounded_counter.txt)" -o generated/bounded_counter
```

Use separate output directories for separate prompts so their artifacts are easy
to compare.

## Interpreting Outputs

For a verified run, inspect:

- `generated/<case>/tla/<slug>.tla`: translated TLA+ module. Check that the
  PlusCal algorithm, `Inv`, `Property`, and finite constants match the prompt.
- `generated/<case>/python/<slug>.py`: refined Python module. Check that its
  assertions correspond to the top-level conjuncts of `Inv`.
- `generated/<case>/work/<slug>_iter<N>/`: per-attempt working directory with
  the main TLA+ module, `Consec_<Module>.tla`, `Prop_<Module>.tla`, and
  `init.cfg`, `consec.cfg`, `property.cfg`, plus JSON/Markdown summaries for
  the proposal, proof bundle, and any repair request.

Status meanings:

- `passed`: TLC found no violation for that obligation in the finite model.
- `failed`: TLC produced a counterexample trace.
- `timeout`: TLC exceeded `TLC_TIMEOUT_S`.
- `error`: translation, invocation, or evaluation failed.

A run is considered verified only when all three obligations are `passed` and
the Python module is written.

## Limitations To Check

- The proof applies to the generated finite TLA+ model, not directly to the
  English prompt.
- The invariant must enumerate variable domains so TLC can use it as an initial
  predicate for consecution and property checks.
- Large or unbounded domains can make TLC slow or non-terminating.
- Python refinement is assertion-guided but not separately proven equivalent to
  the PlusCal algorithm.
