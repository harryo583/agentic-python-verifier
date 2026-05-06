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

## The three proof obligations

For an algorithm with initial-state predicate `Init`, transition relation
`Next`, candidate inductive invariant `Inv`, and target safety property
`Property`, the verifier checks:

| Obligation       | Formula                       | Encoding                                    |
| ---------------- | ----------------------------- | ------------------------------------------- |
| **Initiation**   | `Init ⇒ Inv`                  | `SPECIFICATION Spec / INVARIANT Inv` on the PlusCal module |
| **Consecution**  | `Inv ∧ Next ⇒ Inv'`           | Aux module: `IInit == Inv`, `ISpec == IInit /\ [][Next]_vars`; check `INVARIANT Inv` |
| **Property impl.** | `Inv ⇒ Property`            | Aux module: `PInit == Inv`, `PSpec == PInit /\ [][UNCHANGED vars]_vars`; check `INVARIANT Property` |

If any obligation fails, the parsed counterexample (failing obligation, the
violated predicate, and the state trace) is sent back to the synthesis agent
through Claude's `tool_result` channel, and the agent emits a revised
`(PlusCal, Inv, Property)` triple via the `repair_after_counterexample`
tool. The loop terminates when all three obligations pass or the iteration
cap is reached.

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
--model, -m           Override the Claude model id (default: claude-opus-4-7)
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
  files, and TLC's working artifacts. Useful for debugging a stuck run.

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

Integration tests are gated by environment variables:

```bash
# TLC integration (requires TLA2TOOLS_JAR, no API key needed):
pytest tests/test_tlc_runner.py -m integration

# Live end-to-end (requires both TLA2TOOLS_JAR and ANTHROPIC_API_KEY;
# incurs API costs):
pytest tests/test_e2e.py -m integration
```

## Tool stack

- **LLM backbone:** Claude Opus 4.7 (`claude-opus-4-7`) via the Anthropic
  Python SDK with function calling, with Claude Opus 4.6
  (`claude-opus-4-6`) as the automatic fallback on a `529 OverloadedError`
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
