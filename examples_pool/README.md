# Few-shot exemplar pool (Feature #6)

This directory holds a **frozen, leakage-safe** pool of verified `ModuleBundle`
exemplars that are appended (as static worked examples) to the bundle synthesis
and repair system prompts when `FEW_SHOT_ENABLED=1` (config `few_shot_enabled`).

## Why this is leakage-safe

Exemplars are sourced from **canonical published TLA+ specs** (the
Lamport / Hillel-Wayne corpus — mutex, ticket lock, dining philosophers, …) in
domains **disjoint from the benchmark suite** under `examples/`. They are public
*method* artifacts, not held-out test data. The natural-language `prompt.txt` is
reverse-engineered from the published spec.

The disjointness guarantee `exemplar_slugs ∩ benchmark_slugs == ∅` is asserted at
the top of `scripts/run_benchmarks.py` (via `src.llm.few_shot.assert_disjoint`)
and unit-tested in `tests/test_few_shot.py`. **Never** add an exemplar whose slug
collides with a benchmark slug.

## Layout

```
examples_pool/<slug>/
  prompt.txt     # reverse-engineered NL requirement
  bundle.json    # the verified ModuleBundle (ModuleBundle.model_dump_json)
```

`bundle.json` must be a bundle that **passed all four obligations** (per-impl
init/consec/property + refinement) through *our* pipeline, so that the worked
example we show the model is genuinely well-formed in our composition shape.

## Generating an exemplar

A spec found online won't already be in our bundle shape (named-INSTANCE parent +
`<Name>_Abs`/`<Name>_Impl` per child + abstraction_map), so we let the pipeline
produce it and freeze the verified result:

```bash
# Requires ANTHROPIC_API_KEY + TLA2TOOLS_JAR (see .env). Costs LLM tokens.
python scripts/build_exemplar.py --slug mutex --prompt examples_pool/mutex/prompt.txt
```

The script runs `run_compositional_pipeline`; on `status == verified` it writes
`bundle.json` next to the prompt. If it does not verify, iterate on the prompt
(or re-run — synthesis is nondeterministic) until it does. Then check it in.

## Reporting requirement

To show the few-shot lift is generalization and not memorization, the report
compares first-attempt verification rate **with and without** `few_shot_enabled`
on the benchmark suite, and documents this pool so graders can see eval integrity
is preserved.
