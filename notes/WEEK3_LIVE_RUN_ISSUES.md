# Week 3 Live-Run Issues (2026-05-28)

First end-to-end run with real LLM tokens after committing Week 3 (`185571b`).
The pipeline machinery is correct (planner runs, bundle synthesises, TLC
fires, repair loop turns, package writer + trace gate are wired). What fails
is **synthesis quality**: the LLM picks PlusCal that pcal.trans rejects, and
the refinement aux module generator emits an INSTANCE shape that TLC's SANY
can't link. Both are fixable next session without touching the gate.

Test suite is green: **182 / 182** pass after Week 3 changes.

---

## Issue 1 — producer_consumer: PlusCal label `Done` is reserved

**Benchmark:** `examples/producer_consumer/prompt.txt`
**Failed at:** Iteration 1, 2, 3 — same root cause every time.
**Symptom in CLI:** `pcal.trans failed for Producer: pcal.trans failed (exit 255)`
**Symptom from `java -cp $JAR pcal.trans Producer_Impl.tla`:**

```
pcal.trans Version 1.11 of 31 December 2020
Unrecoverable error:
 -- Cannot use `Done' as a label.
    line 14, column 5.
```

### What the LLM generated (`generated/work/producer_consumer_system_iter0/Producer_Impl.tla`)

```tla
(* --algorithm Producer
variables generated = << >>, nextItem = 1;
begin
  Loop:
    while nextItem <= 3 do
      generated := Append(generated, nextItem);
      nextItem := nextItem + 1;
    end while;
    Done:               \* <-- reserved label name; pcal.trans rejects
      skip;
end algorithm; *)
```

### Why the repair loop didn't fix it

`_serialise_bundle_failure` at `src/agents/synth_agent.py:268` does include
`result.note` (which carries the pcal error text) in the LLM's tool_result.
So the model literally received "Cannot use `Done' as a label." three times
and still emitted PlusCal with `Done:` each iteration. This is an LLM
prompt-quality problem, not a pipeline plumbing problem.

### Fixes to try next session (smallest → largest)

1. **Add a PlusCal reserved-name rule to `SYNTH_BUNDLE_SYSTEM` in
   `src/llm/prompts.py`.** The PlusCal manual lists reserved labels: `Done`,
   `Error`, `Lbl_N` (auto-generated). Tell the model never to use `Done`,
   `Error`, or any label that pcal.trans would generate as an internal name.
   Recommend `Finish:`, `Idle:`, `End_<X>:` instead.
2. **Surface the pcal error more loudly in `_serialise_bundle_failure`.**
   Currently a pcal failure shows up only as a `note:` line under each
   per-module obligation block. Add a dedicated "pcal.trans rejected the
   PlusCal for <module>: <error>" header so the model can't miss it.
3. **Optional: pre-validate label names** in the synth tool input schema
   (regex blocklist) and reject the tool call before pcal.trans ever runs.
   Lowest effort: a single `re.search(r'^\s*Done\s*:', pluscal)` check that
   returns the blocklist diagnostic as the tool result.

---

## Issue 2 — cache_store: `Refinement_<Parent>.tla` linking fails

**Benchmark:** `examples/cache_store/prompt.txt`
**Failed at:** Iteration 3 (per-module obligations PASS; refinement = error).
**CLI panel:**

```
Per-module obligations:
  BackingStore     PASS
  Cache            PASS
Refinement: error
Trace conformance: skipped (package_unverified)
```

So we got further than producer_consumer — per-impl obligations passed —
but the refinement obligation never linked. Trace gate was correctly skipped
because the bundle wasn't verified.

### What the refinement generator produced
(`generated/work/write_through_cache_iter2/Refinement_WriteThroughCacheSystem.tla`)

```tla
---- MODULE Refinement_WriteThroughCacheSystem ----
EXTENDS WriteThroughCacheSystem

Abs_BackingStore == INSTANCE BackingStore_Abs WITH
    storePresent <- S!storePresent,
    storeVal <- S!storeVal

Abs_Cache == INSTANCE Cache_Abs WITH
    storePresent <- C!storePresent,
    storeVal <- C!storeVal,
    cachePresent <- C!cachePresent,
    cacheVal <- C!cacheVal,
    lastReadValid <- C!lastReadValid,
    lastReadKey <- C!lastReadKey,
    lastReadVal <- C!lastReadVal

RefinementSpec == /\ Abs_BackingStore!Spec
                  /\ Abs_Cache!Spec
====
```

### TLC's complaint (9 semantic errors)

```
line 5, col 23 to col 34 of module Refinement_WriteThroughCacheSystem
Unknown operator: `storePresent'.

line 6, col 19 to col 26 of module Refinement_WriteThroughCacheSystem
Unknown operator: `storeVal'.
... (repeats for cachePresent, cacheVal, lastReadValid, lastReadKey, lastReadVal)
```

### What `BackingStore_Abs.tla` declares

```tla
---- MODULE BackingStore_Abs ----
EXTENDS Naturals
CONSTANTS Keys, Vals       \* <-- abs has CONSTANTS too
VARIABLES storePresent, storeVal
```

### Root cause hypothesis

The Abs module declares **both** `CONSTANTS Keys, Vals` **and** `VARIABLES
storePresent, storeVal`. Our refinement generator (`src/formal/refinement.py`)
only emits `WITH` substitutions for the variables in `impl.abstraction_map`,
not for the abs module's CONSTANTS. So SANY sees an instance where `Keys`
and `Vals` aren't substituted; whether that *also* causes the
"`Unknown operator: storePresent`" message needs verification — possibly a
cascading parse error.

A second suspect: the RHS `S!storePresent`. The parent does `S == INSTANCE
BackingStore_Impl WITH storePresent <- storePresent, ...`, so
`S!storePresent` evaluates to the parent's own `storePresent` variable.
That should be fine, but the abstraction_map being identity is wasteful
(equivalent to writing `storePresent <- storePresent`).

### Fixes to try next session

1. **Substitute abs CONSTANTS in `_render_instance`**
   (`src/formal/refinement.py:101`). When the abs module declares CONSTANTS,
   the WITH must bind each one to either a CONSTANT of the parent or to a
   concrete value. The simplest plan: copy the parent's CONSTANTS into every
   `Abs_<Name> == INSTANCE` block. Specifically, parse the abs source's
   `CONSTANTS X, Y, ...` line and emit `X <- X, Y <- Y, ...` clauses in the
   WITH before the abstraction_map entries.
2. **Re-run TLC on the cache_store iter2 work dir** after the
   refinement.py fix to confirm the constants substitution alone resolves the
   "`Unknown operator`" cascade. If it doesn't, the WITH LHS resolution is
   the actual bug and we need to look at it harder.
3. **Add a refinement-generator unit test** with an abs that declares both
   CONSTANTS and VARIABLES (the existing `tests/test_refinement.py` only
   covers VARIABLES-only abs). The test should run SANY on the generated
   module to confirm it links.
4. **Tighten `SYNTH_BUNDLE_SYSTEM` to forbid identity abstraction_maps.**
   Per the Hillel Wayne ADT pattern the abstraction map should be a real
   abstraction (often a projection, not identity). When the LLM picks
   identity it usually means the abs module is just a copy of the impl with
   trivial wrapping, which defeats refinement checking. Recommend the model
   make the abs strictly weaker than the impl (fewer variables, coarser
   actions).

---

## Cross-cutting observation: repair loop doesn't converge on synth bugs

For both benchmarks the loop ran 3 iterations and the same root cause
persisted across all 3. The repair feedback IS informative — it includes
the pcal error and the TLC semantic errors — but the LLM isn't fixing the
specific class of bug in question. Two possible interventions:

- **Stronger system-prompt rules** for the failure classes the model
  repeatedly hits: reserved PlusCal labels (Issue 1) and INSTANCE WITH
  shape (Issue 2). Both are deterministic, mechanical rules the model can
  follow without reasoning.
- **A "you already tried this" memory.** Right now repair_bundle's history
  carries the prior bundle, but the model may regenerate something nearly
  identical because it doesn't recognise the structural similarity. We could
  inject a one-liner reminder: "you tried <slug> on iteration <N> and the
  same obligation failed with the same error; do NOT submit the same
  PlusCal/abstraction shape again."

---

## What we DID confirm works end-to-end on real LLM calls

- PlannerAgent decomposes both producer_consumer (3 modules) and cache_store
  (2 modules) into well-shaped DecompositionPlans on the first try.
- SynthesisAgent emits a full ModuleBundle (parent + abs+impl per child)
  that the verifier picks up correctly.
- Verifier successfully runs pcal.trans on the modules that don't trip
  reserved-label errors (BackingStore + Cache in cache_store).
- All three per-impl obligations (Init / Consec / Property) pass on
  cache_store iter 3.
- CLI's compositional panel renders correctly with the new "Trace
  conformance: skipped (package_unverified)" line.
- Trace gate is correctly NOT invoked on unverified bundles (per the
  pipeline design — `trace_skipped_reason="package_unverified"`).

---

## Next-session checklist

In order of expected payoff:

- [ ] Fix `src/formal/refinement.py` to substitute abs CONSTANTS in WITH
      (Issue 2). Add a SANY-checked unit test.
- [ ] Add the reserved-label and identity-abstraction rules to
      `SYNTH_BUNDLE_SYSTEM` in `src/llm/prompts.py` (Issues 1 & 2).
- [ ] Re-run cache_store live. If refinement now passes, the trace gate
      will fire automatically — confirm we get a real TraceResult per
      child.
- [ ] Re-run producer_consumer live with the label-rule prompt tweak.
- [ ] If either still fails, look at `_serialise_bundle_failure` and
      promote pcal/SANY errors to dedicated headers.
- [ ] Finally: `python scripts/run_benchmarks.py --out report/bench_results.csv`
      to sweep all 6 compositional benchmarks for the final-report table.
