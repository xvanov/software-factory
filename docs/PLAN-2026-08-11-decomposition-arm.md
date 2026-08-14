# Plan — build a decomposing bench arm, then measure it where decomposition can win

**Status:** proposed, 2026-08-11. Not a pre-registration. Each stage that spends
money gets its own pre-registration before it runs.

## Why this exists

Three sweeps measured the chain and found no lift over a single agent on the same
model (latest: 10/18 vs 12/18, `POSTMORTEM-2026-08-11.md`). But the bench arm's
persona set is:

```python
"factory": FactoryDriverMode(personas=frozenset({"dev", "review"}), ...)
```

**No PM, no SM, no contract.** Every number we have measures chain *plumbing*
around one dev. The product claim — that decomposing work into verified units
beats one agent — **has never been benchmarked.**

And SWE-rebench cannot test it. Measured over our own ten resolving patches:

| | median | mean | max |
|---|---:|---:|---:|
| files changed | **1.5** | 1.6 | 3 |
| hunks | **2.5** | 3.2 | 7 |

Six of ten touch a single file. There is nothing to decompose. RoadmapBench
tasks carry a median of 5 independently-tested targets; a Commit0 repo has dozens
of stripped function bodies. **Task shape is the variable, and ours is pinned at
one unit.**

## The design in one line

Build one new arm that runs the **real chain from a direction**, smoke it on
SWE-rebench (where we predict null — that is the negative control), then measure
it on Commit0 (where decomposition is published to win).

---

# Stage 0 — build the `factory-full` arm

**Spend: $0 (code + tests only). Estimated 3–5 days.**

## 0.1 What "as close to the real factory as possible" means

Today `run_factory` fabricates a `StoryRecord` directly at
`state=StoryState.SM_DONE`, with `direction_id="swebench"`. It starts *after*
the decomposition. The new arm must start *before* it:

```
problem_statement → direction.md → pm-sync (PM triage) → SM → [contract] →
  per story: dev → review → merge gates → next story
→ union diff → grade
```

Concretely:

1. **Write the instance as a direction.** `apps/<bench-app>/directions/<id>/direction.md`
   with the real frontmatter (`title`, `type`, `priority`, `explore: false`,
   `created_at`) and the problem statement under `## Why` + `## Acceptance
   Criteria`. Operator-filed, so it bypasses the machine-filed approval gate.
   **The statement text must stay byte-identical to the other arms'** — the
   template is the only thing that may differ, and that difference must be
   disclosed.
2. **Run the real `pm_sync`** (`factory/chain/pm_sync.py:478`) against the bench
   root instead of hand-building a story.
3. **Add the arm to `_FACTORY_DRIVER_MODES`** with
   `personas=frozenset({"pm", "sm", "dev", "review"})` (plus `contract` — see
   0.3). The table fails loud on an unregistered arm; keep that.
4. **Drive to direction completion, not story completion.** The terminal
   condition becomes "every spawned story is terminal", not "this story is
   terminal".

## 0.2 The four problems that must be solved in code

**(a) N stories → one gradeable diff.** Grading needs a single patch.
*Decision: serialize all stories onto one branch* — story *k+1* starts from
story *k*'s HEAD. Simplest, and the union diff is exactly "what the factory
produced". The alternative (branch-per-story + merge) is closer to production but
drags in merge-conflict handling for no measurement gain. **Disclose the
serialization**, since it removes the parallelism a real direction would have.

**(b) `superseded_by_sibling` is a real outcome, not an error.** 23% of live
sacrifice stories end there (32/138). The driver must record it per story and
still grade the union diff. A direction where 3 of 5 stories are superseded is a
legitimate — and interesting — result.

**(c) Cost scales with story count.** The dev now runs once *per story*. At our
measured $4.50/dev-story, a 5-story direction is ~$22.50/instance against $4.50
today. **This is the dominant budget fact in the whole plan.** Mitigation: a
per-direction story cap passed to PM, and it must be *pre-registered*, not tuned
after seeing results.

**(d) Merge gates are currently not run** (`swebench_adapter.py:3059`: "this
driver terminates at reviewer_done and runs no merge gates"). *Decision: keep
them off for Stage 1* so the smoke test is comparable to the three existing
sweeps, and revisit at Stage 3. Disclose.

## 0.3 Three things to decide before writing code

| decision | recommendation |
|---|---|
| **`contract` persona** — it is CLI-only (`contract.py:190`), not on the tick path | **Wire it in.** It is part of "what the factory would normally do", and leaving it out makes the arm a strawman. If wiring proves large, exclude it and disclose loudly. |
| **`gate_enforced`** — false on every row today | **Leave false for Stage 1** (comparability). Note that enabling it would block the 7/18 rows whose oracle is vacuous, so it must not be flipped without fixing `oracle_vacuity_is_webapp_shaped` first. |
| **The mute-gate bug** (`gates_speak_a_language_the_dev_cannot_decode`) | **Fix it first — it is ~5 call sites.** A decomposing arm has *more* gate interactions, so shipping the arm on top of a gate that cannot explain itself would poison the measurement. |

## 0.4 Definition of done for Stage 0

- Arm registered; `_factory_driver_mode` still fails loud on unknown arms.
- `--dry-run` prints the direction, the stories PM would emit, and the serialized
  branch plan, and **writes nothing** (the `pm_sync` dry-run purity rule).
- Unit tests: direction authoring, multi-story serialization, union-diff capture,
  `superseded_by_sibling` accounting, story-cap enforcement.
- Full suite green at `-n 4` against the `origin/main` baseline.

---

# Stage 1 — plumbing proof on SWE-rebench

**Spend: ~$20–40. Estimated 0.5 day. This is NOT a measurement.**

Run `factory-full` on **4 instances** of the pinned manifest, chosen as the
cheapest previously-resolving rows (`conan-19735` $0.88, `canvasapi` $0.70,
`pyinfra-1665` $1.01, `keras-22642` $2.37 in the replay).

**Pass criteria — all must hold:**

1. PM emits ≥1 story per direction, and the story count is recorded.
2. Every story reaches a terminal state; no driver-level hang or tick-cap exit.
3. The union diff is captured, non-empty, and `diff_integrity.trustworthy` is
   true — **with the submodule/size assertion added**, since
   `dissolved_submodule_becomes_unappliable_diff` shows the current predicate
   passes a 575 KB unappliable patch.
4. Grading runs and produces an outcome for each row.
5. Cost per instance recorded, so Stage 3 can be priced from data instead of
   inference.

**What the result means.** We predict **null or slightly negative** here — the
tasks are single-unit, so PM either emits one story (identical to today) or
splits artificially. **A null is a pass, not a failure.** If PM reliably emits
one story on a 1-file bug, that is itself a good sign the triage is sane.

**Stop condition:** if any pass criterion fails, fix and re-run Stage 1 before
spending on Commit0.

---

# Stage 2 — Commit0 harness and reference control

**Spend: $0 model (docker + CPU only). Estimated 2–3 days.**

Commit0 is Python + pytest end to end, so `_GRADE_SCRIPT`, per-node PASSED
grading, the oracle store, the report tables and the statistics transfer.

**2.1 Kill the contamination first — this is non-negotiable.** The gold
implementation is a **branch of the repo the harness clones**;
`clone_repo` does a full clone with no depth, no `--single-branch`, and never
drops the remote, so `git show origin/master:<file>` hands the agent the answer.
The upstream fix (Feb 2026) landed **only** in the containerized test
environment, not the `commit0 setup` → `agent run` path. Strip the remote and
history after clone, and apply it **identically to every arm**. Assert it in the
harness, and fail the run if a remote is present.

**2.2 Reference control before any arm.** Grade the reference implementation to
prove the harness scores it as solved. Our SWE-rebench selftest caught three bugs
that each faked a 0% score; this is the same insurance. Free — docker only.

**2.3 Pick the subset by size, and pre-register it.** `SPLIT_LITE` is 16 repos.
Pick the **3 smallest by function-body count** for the pilot, named in advance.

**2.4 Fix the metric trap if RoadmapBench is ever revisited:**
`compute_metrics.py` hardcodes `TOTAL_TASKS = 115` as the denominator regardless
of how many tasks ran — a 41-task subset silently reports ~0.36× the true score.
Not needed for Commit0; recorded so it is not rediscovered.

---

# Stage 3 — Commit0 pilot

**Spend: ~$40–80. Estimated 0.5 day.**

Three repos × two arms (`factory-full` vs `openhands` single agent), paired,
same model (`azure/deepseek-v4-pro`), continuous scoring.

**Budget honesty.** At our measured $4.50/dev-story and a 4-story cap, three
repos cost ~$54 for the chain arm plus ~$9 for the control. **If the story cap
binds at 4 and repos need more, cost rises linearly.** The cap is the control
knob and it is pre-registered, not tuned.

**Scoring.** Continuous mean score with a **paired t-test**, matching CAID's own
analysis — not binary resolve. Report the paired difference and its CI. Never a
published rate: Commit0 reimplements famous PyPI libraries that predate every
model cutoff, so the only defensible claim is a within-corpus paired comparison
at a fixed model.

**What we can and cannot see at n=3.** Nothing statistical. Stage 3's job is
**cost measurement + a pattern check**: does the chain's score differ visibly,
and does PM produce sensible units on a many-function repo?

---

# Stage 4 — decision point

**Spend: ~$150–250 if taken.**

Extend to all 16 `SPLIT_LITE` repos, both arms, and re-run the SWE-rebench leg as
the **negative control**.

The claim worth making is not one positive result — it is the **interaction**:

> same arm, same model: wins on many-unit tasks, does not win on one-unit tasks.

That is a far stronger statement than any single rate, and it is exactly what the
two legs together produce.

**Powered for:** a large effect only. CAID's frontier delta was +6.0 pp and its
own paper could not resolve +3.6 pp at n=16. **Pre-register that a null at n=16
means "no large effect", never "no effect".** Our regime is the encouraging one —
CAID's largest delta (+14.7 pp) was on its *weakest* model.

---

# Budget summary

| stage | spend | days | produces |
|---|---:|---:|---|
| 0 — build the arm | **$0** | 3–5 | the arm + tests |
| 1 — SWE-rebench smoke | **$20–40** | 0.5 | plumbing proof, real per-story cost |
| 2 — Commit0 harness | **$0** | 2–3 | de-contaminated harness + reference control |
| 3 — Commit0 pilot (3 repos) | **$40–80** | 0.5 | cost data + first pattern |
| **subtotal to a decision** | **$60–120** | **6–9** | |
| 4 — full 16 repos + control leg | $150–250 | 1 | the interaction result |

**The honest headline: $30–40 buys a plumbing proof, not a signal.** A real
Commit0 signal is ~$150–250, and that is a consequence of the design — a
decomposing arm runs the dev once per story, so cost scales with the very thing
we are testing. Stages 1 and 3 are structured so you can stop after either.

# Risks

1. **Cost blowout from story count** — the dominant risk. Mitigated by a
   pre-registered cap, and Stage 1 measures the real multiplier before Stage 3.
2. **PM splits a single-unit task and loses to `superseded_by_sibling`** — a real
   possible outcome on SWE-rebench, and worth reporting rather than tuning away.
3. **The chain's known defects poison the new arm.** Mute gates, the 0444 lock
   deadlock, a verdict layer at chance — all benchmark-independent, all bite
   *harder* with more units. Fixing the mute gate is a Stage 0 prerequisite for
   this reason.
4. **Goalpost-moving.** Changing suites after a negative result looks like — and
   can be — motivated reasoning. Defence: pre-register each spending stage,
   publish nulls, and **keep SWE-rebench's 10/18 as the standing record** rather
   than retiring it.
