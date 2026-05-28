# Agentic Python Verifier

**Proof-Driven Python Code Generation via Agentic PlusCal Invariant
Co-Synthesis**
*Harry Wang, Eric Shang Nan Chen*

## What this is

Most LLM code-generation pipelines write code first and try to verify it
afterwards. This project inverts that: an agentic system **co-synthesises a
PlusCal specification and a candidate inductive invariant** for a natural
language requirement, runs three formal proof obligations through TLC, feeds
counterexamples back to the agent for repair, and only after all three
obligations pass does a second agent refine the verified PlusCal into an
executable Python module whose runtime assertions are derived from the
verified invariant.

Scope note: this is a course prototype for finite-domain inductive checking
with TLC. It is meant to show the verification loop and generated artifacts
clearly, not to prove unbounded programs or report live LLM success rates.

## The three proof obligations

For an algorithm with initial-state predicate `Init`, transition relation
`Next`, candidate inductive invariant `Inv`, and target safety property
`Property`, the verifier checks:

| Obligation       | Formula                       | Encoding                                    |
| ---------------- | ----------------------------- | ------------------------------------------- |
| **Initiation / reachable Inv check** | `Init ⇒ Inv` over the generated `Spec` run | `SPECIFICATION Spec / INVARIANT Inv` on the PlusCal module |
| **Consecution**  | `Inv ∧ Next ⇒ Inv'`           | Aux module: `IInit == Inv`, `ISpec == IInit /\ [][Next]_vars`; check `INVARIANT Inv` |
| **Property impl.** | `Inv ⇒ Property`            | Aux module: `PInit == Inv`, `PSpec == PInit /\ [][UNCHANGED vars]_vars`; check `INVARIANT Property` |

If any obligation fails, the parsed counterexample (failing obligation, the
violated predicate, and the state trace) is sent back to the synthesis agent
through Claude's `tool_result` channel, and the agent emits a revised
`(PlusCal, Inv, Property)` triple via the `repair_after_counterexample`
tool. The loop terminates when all three obligations pass or the iteration
cap is reached.

Note: the `init.cfg` encoding runs TLC on the module's full `Spec` with
`INVARIANT Inv`. In practice this checks that reachable states from `Init`
preserve `Inv`; a later reachable transition violation can therefore appear in
that run. The separate consecution module is the explicit inductive one-step
check from arbitrary `Inv` states.

## Pipeline

```text
                 +---------------------------------+
 prompt -------> | SynthesisAgent.propose          |  Claude Opus 4.7
                 | tool: propose_pluscal_with_inv. |  with function calling
                 +---------------+-----------------+
                                 |
                                 v   PlusCal module + Inv + Property + finite CONSTANTS
            +---------------------------------------+
            | Verifier:                             |
            |   pcal.trans  -> TLA+                 |
            |   write Consec_<M>.tla, Prop_<M>.tla  |
            |   write init.cfg / consec.cfg /       |
            |         property.cfg                  |
            |   tlc x 3  -> ProofBundle             |
            +---------------+-----------------------+
                            |
                bundle.all_passed?
            no  /                  \  yes
               v                    v
   +-----------------------+   +---------------------------+
   | SynthesisAgent.repair |   | RefineAgent.to_python     |
   | tool: repair_after_   |   | tool: emit_python_module  |
   | counterexample        |   | (assertions derived from  |
   +-----------+-----------+   |  Inv conjuncts)           |
               |               +-------------+-------------+
               +-> propose ...                |
                                              v
                                   <slug>.py with runtime asserts
```

## Installation

Python 3.11+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You also need [TLA+ tools](https://github.com/tlaplus/tlaplus/releases). The
`tla2tools.jar` distributable supplies both `pcal.trans` (the PlusCal-to-TLA+
translator) and `tlc2.TLC` (the model checker), so a single download covers
both binaries the verifier shells out to.

```bash
export TLA2TOOLS_JAR=/absolute/path/to/tla2tools.jar
export ANTHROPIC_API_KEY=sk-ant-...
```

(`TLA_TLC_JAR` is also accepted as a backward-compatible alias.)

## Usage

```bash
python -m src.main "Implement a bounded counter from 0 to 10 that never exceeds the bound."
```

Options:

```
--output, -o          Output directory (default: ./generated)
--max-iterations, -n  Max repair iterations (default: 5; range 1-20)
--model, -m           Override the Claude model id (default: claude-opus-4-1-20250805)
--verbose, -v         Verbose logging
```

The CLI exits with code `0` when all three obligations pass and the Python
module has been written, code `1` when the iteration cap is exhausted
without verification, and code `2` when configuration is missing
(`ANTHROPIC_API_KEY` or `TLA2TOOLS_JAR`).

Outputs:
- `generated/tla/<slug>.tla` — the verified PlusCal module with its
  `\* BEGIN TRANSLATION` block inlined by `pcal.trans`.
- `generated/python/<slug>.py` — Python implementation with runtime
  `assert` statements derived from the conjuncts of `Inv`.
- `generated/work/<slug>_iter<N>/…` — per-iteration scratch dir containing
  the auxiliary `Consec_<Module>.tla`, `Prop_<Module>.tla`, three `.cfg`
  files, TLC's working artifacts, and lightweight reports:
  `proposal.json`, `proof_bundle.json`, `iteration_summary.md`, plus
  `repair.json` / `repair_summary.md` when a repair was requested.

The final terminal panel reports the status of the three checks:

- `Init: passed` means TLC found no reachable state from `Spec` that violates
  `Inv` during the initiation/reachable-invariant run.
- `Consec: passed` means every enumerated `Inv` state is preserved by one
  `Next` step.
- `Property: passed` means every enumerated `Inv` state satisfies `Property`.

Any `failed`, `timeout`, or `error` status means the run is not a proof. Inspect
the matching `generated/work/<slug>_iter<N>/` directory and TLC stdout captured
in the returned `ProofBundle` when debugging from Python.

## Benchmark prompts

The `examples/` directory contains small finite-state prompts intended for
manual runs and course evaluation. They are deliberately bounded so the agent
can emit finite `CONSTANTS` and TLC can enumerate the state space:

```bash
python -m src.main "$(cat examples/bounded_counter.txt)" -o generated/bounded_counter
python -m src.main "$(cat examples/bank_transfer.txt)" -o generated/bank_transfer
python -m src.main "$(cat examples/resource_semaphore.txt)" -o generated/resource_semaphore
python -m src.main "$(cat examples/ring_buffer.txt)" -o generated/ring_buffer
```

These commands require `ANTHROPIC_API_KEY` and `TLA2TOOLS_JAR`. They may incur
API costs and their live outcomes are model-dependent, so the repository does
not claim fixed pass rates for them. For deterministic grading, use the offline
test suite below.

## Project layout

```
src/
  agents/
    synth_agent.py     LLM co-synthesis: propose + repair tools
    refine_agent.py    LLM PlusCal -> Python with derived asserts
    verifier.py        Orchestrates the three TLC obligations
  formal/
    pcal_translator.py Wraps `java -cp tla2tools.jar pcal.trans <file>`
    tlc_config.py      Generates init.cfg / consec.cfg / property.cfg and
                       the auxiliary Consec_<M>.tla / Prop_<M>.tla modules
    tla_runner.py      Wraps `java -cp tla2tools.jar tlc2.TLC -config ...`
    counterexample_parser.py
                       Parses TLC stdout/stderr into structured
                       ObligationResult / Counterexample
  llm/
    anthropic_client.py Anthropic SDK wrapper with prompt caching
    tools.py            JSONSchema for the three function-calling tools
    prompts.py          System prompts for synth / repair / refine
  models/
    task.py            TaskRequest, PipelineResult
    synthesis.py       Constants, SynthesisProposal, RepairProposal
    proof.py           TraceState, Counterexample, ObligationResult,
                       ProofBundle
  config.py            Settings + fail-fast on missing key/jar
  main.py              Pipeline orchestrator (the agent loop)
  cli.py               Typer CLI

examples/              Benchmark prompts (bounded_counter, bank_transfer)
tests/                 Unit + mocked-pipeline + gated integration tests
```

## Testing

The offline suite mocks the Anthropic SDK at the boundary and uses captured
TLC trace fixtures, so it runs without an API key or `tla2tools.jar`:

```bash
pytest tests/ -m "not integration"
```

Expected offline behavior: all non-integration tests should pass on a normal
Python 3.11+ environment after installing `requirements.txt`. These tests cover
configuration errors, tool-call parsing, proposal/repair/refine flow with a
mocked client, TLC config generation, and TLC-output parsing. They do not invoke
Claude, `pcal.trans`, or live TLC.

Integration tests are gated by environment variables:

```bash
# TLC integration (requires TLA2TOOLS_JAR, no API key needed):
pytest tests/test_tlc_runner.py -m integration

# Live end-to-end (requires both TLA2TOOLS_JAR and ANTHROPIC_API_KEY;
# incurs API costs):
pytest tests/test_e2e.py -m integration
```

The TLC integration checks local fixture modules only. The live end-to-end test
is intentionally gated and should be treated as an optional smoke test rather
than a reproducible benchmark result.

See `docs/evaluator_guide.md` for a compact walkthrough of what to inspect in
generated outputs.

## Tool stack

- **LLM backbone:** Claude Opus 4.1 (`claude-opus-4-1-20250805`) via the Anthropic
  Python SDK with function calling, with Claude Opus 4
  (`claude-opus-4-20250514`) as the automatic fallback on a `529 OverloadedError`
  (override either via `ANTHROPIC_MODEL` / `ANTHROPIC_FALLBACK_MODEL`).
  Three tools: `propose_pluscal_with_invariant`,
  `repair_after_counterexample`, `emit_python_module`. The system prompt
  is wrapped in `cache_control: ephemeral` so repeated repair iterations
  hit the prompt cache.
- **Verification engine:** TLC model checker (`tlc2.TLC`), invoked as a
  subprocess with `-config <obligation>.cfg -workers auto -deadlock`.
- **PlusCal support:** the official `pcal.trans` translator, also bundled
  in `tla2tools.jar`.

## Known limitations

- **Finite-domain inductive checking only.** The synthesis agent is asked
  to supply small finite `CONSTANTS` (e.g. `MaxValue ∈ {3, 5, 10}`). True
  unbounded inductiveness would need TLAPS, which is out of scope for this
  prototype.
- **TLC proves the emitted finite TLA+ model, not the natural language
  prompt.** The LLM may formalize the task incorrectly. Evaluators should read
  the generated `.tla`, `Inv`, `Property`, and Python assertions before treating
  a run as meaningful.
- **`Inv` must be expressible as an initial-state predicate.** Each
  variable must appear under explicit set membership (`counter \in
  0..MaxValue`, not just `counter >= 0 /\ counter <= MaxValue`). The
  system prompt instructs the agent on this, and the parser surfaces TLC's
  "identifier ... is undefined" message as a repairable error so the agent
  can fix it.
- **TLC may diverge** if `Inv` quantifies over an unbounded set despite
  finite CONSTANTS. Mitigated by a configurable timeout
  (`TLC_TIMEOUT_S`, default 120s) which surfaces as
  `ObligationResult.status="timeout"` and is fed back to the agent for
  repair.
- **Anthropic responses are non-deterministic.** Reproducibility comes
  from the verified `.tla` + `Inv` artifact, not from the LLM dialog. The
  test suite mocks the client at the SDK boundary.

## License

MIT (see `LICENSE`).
