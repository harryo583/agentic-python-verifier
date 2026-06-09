# Efficiency A/B results (corrected for credit-exhausted runs)

Each condition isolates one lever; flags otherwise default. `-n 6`. Cost is the
`est_usd` planning estimate from the #0 instrumentation (Opus placeholder prices).

**Data integrity note.** The Anthropic credit balance was exhausted during the
sweep. This invalidated **`ab_reroll_run3` entirely** (all 6 benchmarks returned
HTTP 400 "credit balance too low") — that run is **excluded**. Three other rows
crashed on *malformed LLM bundle output* (uncaught Pydantic/KeyError, not
infrastructure): `off_run2/producer_consumer`, `off_run3/cache_store`,
`dedup_run2/two_phase_commit`. Those are genuine non-verifications and are kept in
the denominator. Net: OFF and DEDUP have N=3 (18 runs), **REROLL has only N=2 (12
runs)**.

| condition | verified | rate | mean iters | mean $/run | LLM-crash |
|---|---|---|---|---|---|
| OFF (baseline) | 12/18 | 67% | 4.62 | 2.90 | 2 |
| DEDUP (`REPAIR_HISTORY_MODE=latest`) | 10/18 | 56% | 4.88 | 2.52 | 1 |
| REROLL-stuck (`REPAIRS_PER_CHAIN=0`), N=2 | 9/12 | 75% | 5.08 | 2.91 | 0 |

### Per-benchmark verified / valid-runs
| benchmark | OFF | DEDUP | REROLL |
|---|---|---|---|
| bank_audit | 2/3 | 3/3 | 2/2 |
| cache_store | 2/2 | 2/3 | 1/2 |
| leader_log | 1/3 | 1/3 | 1/2 |
| producer_consumer | 2/2 | 1/3 | 2/2 |
| rw_lock | 3/3 | 3/3 | 2/2 |
| two_phase_commit | 2/3 | 0/2 | 1/2 |

### Per-stage mean cost / input tokens (OFF vs DEDUP)
| stage | OFF $ | DEDUP $ | OFF in-tok | DEDUP in-tok |
|---|---|---|---|---|
| planner | 0.077 | 0.079 | 2473 | 2328 |
| synth_bundle | 0.352 | 0.354 | 1345 | 1363 |
| **repair_bundle** | **2.070** | **1.797** | **17531** | **8617** |
| refine_child | 0.302 | 0.267 | 3667 | 3335 |
| refine_parent | 0.236 | 0.232 | 4004 | 3659 |

## Conclusion (honest)

1. **No statistically distinguishable convergence difference.** Verification rates
   (OFF 67%, DEDUP 56%, REROLL 75%) span ~20 points, but with 12–18 observations and
   per-benchmark rates swinging 0/3–3/3, the binomial noise (SD ≈ 2 runs, ±11–14%)
   swamps the gap. **No condition is significantly better or worse than baseline.**
   (An earlier read that called REROLL *worse* was wrong — it counted the 6
   credit-exhausted crashes in `reroll_run3` as REROLL failures.)

2. **Dedup gives a modest, real cost cut.** It halved `repair_bundle` *input* tokens
   (17.5k → 8.6k) as designed, lowering mean cost ~13% ($2.90 → $2.52). The effect is
   modest, not dramatic, because **Opus output tokens dominate cost and dedup doesn't
   touch them.** (My earlier "~50% cut" was an artifact of the aggressive-reroll config
   shrinking history, not dedup.)

3. **Reroll-stuck neither clearly helped nor hurt** on its 2 valid runs; it fired but
   the fresh starts converge about as often as they fail — consistent with the failures
   being fresh coin-flips, not anchoring that a reroll reliably escapes.

4. **The binding constraint is synthesis nondeterminism**, not repair-loop mechanics:
   the same prompt+model verifies 0/3–3/3. Loop tuning (history shape, reroll policy)
   can't move that; the leverage is in synthesis quality (model/prompt/exemplars) or
   drawing more samples.

5. **Robustness gap surfaced.** 3 runs crashed because the LLM emitted a malformed
   `ModuleBundle` (missing `parent`, empty `modules`, bad constant type) and the pipeline
   raised instead of recording a failed iteration. Worth catching in
   `_bundle_from_tool_input` / `propose_bundle` so a garbage bundle becomes a repairable
   failure rather than a crashed benchmark.

## For the report

- Headline quantified finding (from #0 instrumentation): **`repair_bundle` is ~$2.07 of
  the ~$2.90 per-run spend — repair is the cost center**, confirming the brief's premise
  with numbers.
- The efficiency interventions are **default-off and harmless**; the controlled A/B is the
  evidence base for *not* enabling them by default, and for redirecting effort from
  loop-tuning to synthesis quality.
- Caveat the underpowered REROLL arm (N=2, one run lost to credit exhaustion) explicitly.
