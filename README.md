# Agentic Python Verifier

**Proof-Driven Multi-Module Python via Agentic TLA+ Co-Synthesis**
*Harry Wang, Eric Shang Nan Chen*

## What this is

Most LLM code-generation pipelines write code first and try to verify it
afterwards. This project inverts that order. From a natural-language
requirement an agentic system:

1. **Plans** a multi-module decomposition (parent + abs+impl per child),
2. **Co-synthesises** the TLA+/PlusCal source plus inductive invariants for
   every module,
3. **Verifies** four classes of TLC proof obligations (three per impl plus a
   cross-module refinement obligation) and feeds counterexamples back to the
   agent for repair,
4. **Refines** the verified bundle into a Python package whose `icontract`
   decorators encode each module's invariant at runtime,
5. **Trace-conformance checks** the executable Python against each child's
   abstract spec by running it once with a seeded budget, capturing every
   action+state as JSONL, and replaying that JSONL through TLC.

The framing target is the 2025 **DafnyComp** benchmark (arXiv 2509.23061),
which showed LLMs collapse from ~58% verification on single-function tasks
to **3.69%** on multi-function compositional tasks. This pipeline is the
TLA+-side attack on that gap.

## The four proof obligations (compositional)

For each impl module with `Init`, `Next`, candidate inductive invariant `Inv`,
and target safety property `Property`:

| Obligation       | Formula                | Encoding |
| ---------------- | ---------------------- | -------- |
| **Initiation**   | `Init ⇒ Inv`           | `SPECIFICATION Spec / INVARIANT Inv` on `<Name>_Impl.tla` |
| **Consecution**  | `Inv ∧ Next ⇒ Inv'`    | Aux `Consec_<Name>_Impl.tla`: `IInit == Inv`, `ISpec == IInit /\ [][Next]_vars` |
| **Property impl.**| `Inv ⇒ Property`      | Aux `Prop_<Name>_Impl.tla`: `PInit == Inv`, `PSpec == PInit /\ [][UNCHANGED vars]_vars` |

Plus one per bundle:

| Obligation       | Formula                | Encoding |
| ---------------- | ---------------------- | -------- |
| **Refinement**   | each `Impl` refines `Abs` via `abstraction_map` | Aux `Refinement_<Parent>.tla` per Hillel Wayne's ADT pattern: `Abs_<Name> == INSTANCE <Name>_Abs WITH ...`; check `PROPERTY RefinementSpec == /\ Abs_<Name>!Spec` |

Failures surface through `src/formal/counterexample_parser.py` and are sent
back to the synthesis agent via Anthropic's `tool_result` channel; the agent
emits a repaired bundle through the `repair_module_bundle` tool. The loop
terminates when all obligations pass or the iteration cap is reached.

## Trace conformance (Week 3)

After refinement, the emitted Python package is subprocessed once with a
fixed seed and step budget. The shim's `log_action(name, state)` appends a
JSONL line per atomic action. For each child class:

1. Filter the JSONL by the `<Class>.<Action>` prefix → per-child trace
2. Render `Trace_<Name>.tla` per Cirstea et al. 2024 §3.2 (arXiv 2404.16075):
   ```tla
   ---- MODULE Trace_<Name> ----
   EXTENDS <Name>_Abs, Sequences, Naturals, TLC
   Trace == << [event |-> "...", <abs_var> |-> <val>, ...], ... >>
   VARIABLE l
   IsEvent(e) ==
       /\ l \in 1..(Len(Trace) - 1)
       /\ Trace[l + 1].event = e
       /\ <abs_var>' = Trace[l + 1].<abs_var>
       /\ l' = l + 1
   TraceInit  == l = 1 /\ <abs_var> = Trace[1].<abs_var> /\ ...
   TraceNext  == \/ IsEvent("Enqueue") /\ Enqueue
                 \/ IsEvent("Dequeue") /\ Dequeue
   TraceSpec  == TraceInit /\ [][TraceNext]_<<l, <vars>>>
   ====
   ```
3. Run TLC with `SPECIFICATION TraceSpec / INVARIANT Inv`. TLC 2.19 has no
   `POSTCONDITION`, so conformance is inferred from stdout:
   - `Model checking completed. No error has been found.` plus
     `depth = Len(Trace)` → **conforms**
   - `depth = K < Len(Trace)` → **diverged at step K+1** (a recorded
     transition isn't permitted by the abs spec)
   - `Error: Invariant Inv is violated.` → **invariant_violated** at the last
     `State N:` block in the counterexample
   - timeout / unrecognised output → `tlc_timeout` / `tlc_error`

Per-child results land in `CompositionalPipelineResult.traces`. **Trace
failures are advisory only** — the pipeline `status` is unchanged. The
rationale is that the static obligations already prove refinement over *all*
behaviours; the trace gate is runtime evidence that the actual Python
execution stays inside that refinement.

## Pipeline

```
                  +---------------------------------+
prompt --------> | PlannerAgent.decompose          | Claude Opus 4.7
                  | tool: propose_decomposition     | (≤2 retries on schema)
                  +---------------+-----------------+
                                  v   DecompositionPlan
                  +---------------------------------+
                  | SynthesisAgent.propose_bundle   |
                  | tool: propose_module_bundle     |
                  +---------------+-----------------+
                                  v   ModuleBundle (parent + abs+impl per child)
            +-------------------------------------------+
            | Verifier.check_bundle:                    |
            |   for each impl: pcal.trans + 3 TLC runs  |
            |   for parent:    Refinement_<P>.tla       |
            |                  + TLC                    |
            +---------------+---------------------------+
                            |
              all_passed? no -> repair_bundle -> propose
                          yes
                            v
            +---------------------------------------+
            | RefineAgent.to_python_package         |
            | one LLM call per impl + one for app   |
            | icontract decorators + log_action     |
            +---------------+-----------------------+
                            v
            +---------------------------------------+
            | TraceGate.check (Week 3):             |
            |   subprocess python <pkg>/app.py      |
            |   read trace.jsonl                    |
            |   per child: render + TLC + classify  |
            +---------------+-----------------------+
                            v
                  CompositionalPipelineResult
                  (status, proof, traces, paths)
```

The legacy single-module pipeline (`run_pipeline`, `--legacy`) is preserved
for the bounded_counter / account_transfer baselines.

## Installation

Python 3.11+ is required.

```bash
pip install -r requirements.txt
```

You also need [TLA+ tools](https://github.com/tlaplus/tlaplus/releases). The
`tla2tools.jar` distributable supplies both `pcal.trans` and `tlc2.TLC`.

```bash
export TLA2TOOLS_JAR=/absolute/path/to/tla2tools.jar
export ANTHROPIC_API_KEY=sk-ant-...

# Optional tertiary fallback when both Anthropic Opus tiers return 529:
export OPENAI_API_KEY=sk-...
```

## Usage

```bash
# Compositional (default):
python -m src.cli "Implement a multi-account ledger with audit-log integrity."

# Skip the Week-3 trace gate (static obligations only):
python -m src.cli "..." --skip-trace-gate

# Legacy single-module path (for baseline regen):
python -m src.cli "Implement a bounded counter 0..10..." --legacy
```

Options:

```
--output, -o            Output directory (default: ./generated)
--max-iterations, -n    Max repair iterations (default: 5; range 1-20)
--model, -m             Override the Claude model id (default: claude-opus-4-7)
--compositional/--legacy  Pipeline choice (default: compositional)
--skip-trace-gate/--no-skip-trace-gate  Disable the Week-3 trace gate
--verbose, -v           Verbose logging
```

Exit codes: `0` on `status="verified"`, `1` on `unverified` or
`planner_failed`, `2` on missing configuration.

Outputs:

- `generated/tla/<slug>/{Parent.tla, <Name>_Abs.tla, <Name>_Impl.tla, ...}`
  — the verified bundle with `pcal.trans` inlined.
- `generated/python/<slug>/{__init__.py, _trace.py, app.py, <mod>.py, ...}`
  — the refined package. The parent app exposes `run(steps: int = 50)`.
- `generated/work/<slug>_iter<N>/` — per-iteration TLC scratch dir.
- `generated/work/<slug>_iter<N>/trace/` — trace gate's `trace.jsonl`,
  `_trace_driver.py`, and per-child `Trace_<Name>.tla` + `.cfg`.

## Benchmark sweep

```bash
python scripts/run_benchmarks.py --out report/bench_results.csv
python scripts/run_benchmarks.py --only producer_consumer
python scripts/run_benchmarks.py --skip-trace-gate --max-iterations 5
```

CSV columns: `slug, status, iterations, n_modules, n_impls, ref_status,
per_module_pass, per_module_fail, trace_conform, trace_diverged,
trace_inv_violated, trace_other, pipeline_seconds, total_tlc_seconds,
error_note`. A Markdown summary is also printed to stdout.

## Benchmark suite

Two legacy single-module baselines + six compositional benchmarks under
`examples/`:

| Slug                  | Modules                          | Property |
| --------------------- | -------------------------------- | -------- |
| `bounded_counter`     | (single)                         | bounded within 0..10 |
| `bank_transfer`       | (single)                         | sum preserved |
| `producer_consumer`   | Queue (abs+impl), Producer, Consumer | no item lost; bounded queue |
| `cache_store`         | Cache (abs+impl), Store          | read-after-write consistency |
| `bank_audit`          | Account, Ledger, Transfer        | sum preserved; ledger ⇔ balance |
| `two_phase_commit`    | ResourceManager, Coordinator     | agreement; no commit→abort regression |
| `leader_log`          | Node, Election                   | ≤1 leader/term; log/term monotonicity |
| `rw_lock`             | RwLock, Client                   | mutex on write; reader_count consistent |

Each new benchmark ships `prompt.txt` plus `expected_modules.yaml` (reference
decomposition; used for evaluation diff, not driven into the pipeline).

## Project layout

```
src/
  agents/
    planner_agent.py    LLM decomposition: propose_decomposition tool
    synth_agent.py      LLM co-synthesis: propose/repair (single + bundle)
    refine_agent.py     LLM refinement: to_python (legacy) + to_python_package
    trace_gate.py       Subprocess driver + per-child TLC fan-out (Week 3)
    verifier.py         Orchestrates per-module + refinement obligations
  formal/
    pcal_translator.py  Wraps `java -cp tla2tools.jar pcal.trans`
    tla_runner.py       Wraps `java -cp tla2tools.jar tlc2.TLC`
    counterexample_parser.py  TLC stdout -> ObligationResult/Counterexample
    tlc_config.py       Generates init/consec/property .cfg + aux modules
    refinement.py       Generates Refinement_<Parent>.tla per Hillel Wayne
    trace_renderer.py   JSONL -> Trace_<Name>.tla per Cirstea et al. 2024
    trace_postcondition.py  TLC stdout -> TraceOutcome (depth-parsing)
  llm/
    anthropic_client.py Anthropic SDK wrapper + prompt caching + fallback
    openai_adapter.py   OpenAI tertiary adapter (translates tool_use shape)
    tools.py            JSONSchema for every function-calling tool
    prompts.py          System prompts: planner, synth, refine, app
  models/
    task.py             TaskRequest, PipelineResult, CompositionalPipelineResult
    decomposition.py    DecompositionPlan, ModuleSpec, AbstractInterface
    synthesis.py        Constants, SynthesisProposal, RepairProposal
    bundle.py           ModuleBundle, CompositionalProofBundle,
                        PythonPackage, TraceResult
    proof.py            TraceState, Counterexample, ObligationResult, ProofBundle
  config.py             Settings + fail-fast on missing key/jar
  main.py               Pipeline orchestrators (legacy + compositional)
  cli.py                Typer CLI

scripts/run_benchmarks.py   Sweep examples/* -> CSV + Markdown summary
examples/                   Benchmark prompts + expected_modules.yaml
tests/                      Unit + mocked + TLC-gated + LLM-gated integration
```

## Testing

The offline suite mocks the Anthropic SDK and uses captured TLC stdout
fixtures, so it runs without an API key or `tla2tools.jar`:

```bash
pytest tests/
```

TLC integration tests exercise the trace renderer end-to-end against a real
`tla2tools.jar`:

```bash
TLA2TOOLS_JAR=/path/to/tla2tools.jar pytest tests/test_trace_gate_tlc.py
```

Live end-to-end requires `ANTHROPIC_API_KEY` and `TLA2TOOLS_JAR` (incurs API
costs):

```bash
pytest tests/test_e2e.py
```

## Tool stack

- **LLM backbone:** Claude Opus 4.7 (`claude-opus-4-7`) via the Anthropic
  Python SDK with function calling. Three-tier overload fallback chain:

      claude-opus-4-7  --(529)-->  claude-opus-4-6  --(529)-->  gpt-5.4
        ANTHROPIC_MODEL              ANTHROPIC_FALLBACK_MODEL    OPENAI_MODEL

  System prompts are wrapped in `cache_control: ephemeral` so repair
  iterations hit the Anthropic prompt cache.
- **Verification engine:** TLC 2.19 (`tlc2.TLC`), invoked as a subprocess
  with `-config <obligation>.cfg -workers auto -deadlock`. TLC's stdout is
  parsed for both static-obligation and trace-conformance outcomes.
- **Composition pattern:** Hillel Wayne's ADT refinement
  (https://www.hillelwayne.com/post/tla-adt/) — children are named
  `INSTANCE`s of `<Name>_Abs` with `WITH` substitutions; refinement is
  `RefinementSpec == /\ Abs_<Name>!Spec`.
- **Runtime contracts:** `icontract` decorators on every emitted class
  (`@invariant` per Inv conjunct, `@require` / `@ensure` per method).
- **Trace pattern:** Cirstea et al. 2024 (arXiv 2404.16075) — JSONL action
  log + per-child Trace_<Name>.tla replayed against the abs spec via TLC.

## Known limitations

- **Finite-domain inductive checking only.** Synthesis is asked to supply
  small finite `CONSTANTS`. True unbounded inductiveness needs TLAPS, which
  is out of scope.
- **`Inv` must be expressible as an initial-state predicate.** Each variable
  must appear under explicit set membership. TLC's "identifier ... is
  undefined" is surfaced as a repairable error.
- **Trace gate scope is per-child Abs**, not parent-level. The composed
  parent spec's `Inv` is verified statically by the refinement obligation;
  the trace gate adds runtime evidence at the child level. Parent-level
  trace replay would require richer LLM coupling of Python state to parent
  TLA+ vars.
- **Parametric abs actions are degraded.** When an abs operator takes
  arguments (e.g. `Enqueue(item) == ...`), the trace gate cannot reliably
  invent the parameter domain, so it drops the action-relation conjunct and
  keeps only `IsEvent` + the per-state `Inv` check. Nullary abs actions get
  the full conformance check (`IsEvent /\ <action-relation>`).
- **Trace gate assumes determinism.** The emitted parent app is required to
  seed `random` at module import; the subprocess runs under
  `PYTHONHASHSEED=0`. Threading or unseeded RNG is out of scope.

## License

MIT (see `LICENSE`).
