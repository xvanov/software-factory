# SOTA research notes — software-factory vs. harness engineering, July 2026

> **What this is.** The external-research portion of a nine-agent audit run
> 2026-07-24 (four agents audited this repo's internals, five swept the
> external state of the art). The internal-defect findings and the
> point-in-time production numbers from that audit have been removed from
> this file — they were fixed the same day (PR #113) and are summarized in
> memory at
> `/home/k/.claude/projects/-home-k-software-factory/memory/sota_audit_2026_07_24.md`.
> What remains here is the durable part: literature citations and
> cross-system comparisons that inform future architecture decisions. Treat
> specific internal claims below (e.g. "we are ahead/behind on X") as
> directional, not current-state-verified — re-check the code before acting.

---

## The thesis, restated with external evidence

Our claim: *harness quality beats model size; cheap models plus loops and backpressure
beat frontier models plus a thin harness, far cheaper.*

**Confirmed — harness variance exceeds model variance.**

- Claw-SWE-Bench (arXiv 2606.12344), 350 real issues, 43 repos, model held fixed,
  five harnesses swapped: pass@1 spread **12.5 pp on GLM 5.1, 27.4 pp on
  Qwen 3.6-flash**. Model spread with harness fixed: 29.4 pp. Harness choice ≈ one
  model tier, and matters *more* the weaker the model.
- LangChain held gpt-5.2-codex fixed and changed only prompts/tools/middleware:
  **52.8% → 66.5% on Terminal-Bench 2.0**, rank ~30 → top-5.
- Cheap+good beats strong+generic, directly: Qwen 3.6-flash + OpenClaw **66.0% at
  ~$0.20/task** beats GLM 5.1 + GenericAgent **63.1% at ~$0.25**.

**Confirmed — repeated sampling against an executable verifier beats frontier
single-pass.** DeepSeek-Coder-V2 on SWE-bench Lite: 15.9% @1 sample → **56% @250**,
vs 43% single-sample SOTA, at under a third the price (arXiv 2407.21787). Scoped by
its own authors to domains where automatic verification exists.

**Not confirmed — "cheaper model ⇒ cheaper end to end."** This is where our framing
needs correcting. From the only end-to-end $/merged-PR study found (12 models × 3
harnesses, frozen repo, constant frontier review gate,
`blog.insight-services-apac.dev/2026/07/06/cost-to-a-merged-feature`):

> As the coder gets cheaper, its output needs more review, so the gate pays more to
> bring it up to the bar.

Coding cost fell **340×** from the most to least expensive coder; **total merge cost
fell only ~1.8×**. Cheapest merge was a *mid*-tier model at 1 cycle ($5.56), not the
near-free model at 4 cycles ($17.03). **Cycle count, not token price, is the cost
driver.** Corollaries with numbers:

- Augment's break-even: if cheap output needs correction >20% of the time, a 3× price
  advantage is gone.
- Retries are quadratic in context, not linear in steps: 1.7–1.9× tokens at 3 steps,
  2.2–2.5× at 5 (tianpan.co retry-budget analysis).
- Across 1,127 real agent runs ($4,281): **context re-reads were 52.1% of spend**;
  retries only 3.4%. Cheap models don't touch that. Prefix-stable caching does.
- The LLM review gate is **fidelity-neutral**: in the study above, one implementation
  passed frontier review while failing 20 unit tests.

**The defensible formulation is therefore: cheap generator + *deterministic* verifier +
hard convergence caps.** That is what this factory actually implements — the
authoritative gate is `pytest` re-run by the harness plus a live smoke boot, with the
LLM reviewer layered on top rather than load-bearing. We built it the right way round.
The README's "harness quality beats model size" should keep its headline but stop
implying the saving comes from the model tier; it comes from gate discipline and cycle
caps.

**Wall clock is the honest cost we underweight.** Our own campaign: 40 min vs 14 min
(3×). The field's figure: open-weight models merged at $18–$29 but took 69–176 min vs
Opus 26 min. At any nonzero engineer-attention cost, cheap-and-slow loses.

---

## Where we were ahead of published practice (as of 2026-07-24 — re-verify before citing)

**1. The runtime smoke gate.** Nothing merges on green unit tests alone; `smoke-green`
boots the PR's own code on an isolated port and drives the core journey. The 2026 canon
converges on exactly this ("a feature is done when it runs live") but few systems
implement it as a merge blocker. It has caught real green-but-unbootable output, which
is why it exists.

**Correction 2026-08-04.** This section used to justify the gate with "Claude Code
failed t3 and t5 by declaring done with its own new tests red". **That claim is
falsified** — the recovered CLI transcripts show t3 ending on three consecutive
`460 passed` runs and t5 on `446 passed`. See `bench/CAMPAIGN-2026-07-17.md`'s
superseded-by header. Keep the gate on its own merits; do not justify it with a
Claude failure that did not happen.

**2. Parallel-agent conflict handling.** A study of 33,596 agent PRs across 2,807 repos
found **79.4% opened concurrently with another agent PR**, replayed conflict rates of
19.8% intra-agent and **41.7% cross-agent**, with the authors noting agents "operate
independently and in isolation, without knowledge that other agents are simultaneously
altering the same files." We have per-story git worktrees, `freshen_behind_prs`,
conflict-rebuild-on-fresh-branch, and per-app docs serialization. We solved a problem
the field has documented and not fixed.

**3. Reviewer drift control.** `handlers.py` implements a *finality drift
clamp*: from cycle 3, blocking findings at file locations not raised in the previous
cycle are clamped to non-blocking unless flagged `regression`, with the deterministic
slop detector explicitly exempt. Convergence is measured by findings-signature
stability, not raw cycle count. No published multi-agent review system instruments
goalpost-drift this way. Keep it.

**4. Independence invariants in routing.** `routes.yaml` enforces reviewer ≠ dev model
and acceptance_author ≠ dev family, deliberately, with rationale in comments. The
field's finding that **93.4% of flagged locations are caught by exactly one tool** (146
PRs, four AI reviewers) supports heterogeneity — though it also implies a *single*
reviewer should be treated as a sensor, not a verdict, which we do not do.

**5. Anti-gaming fences invented independently.** `bench/**` and `factory/manager/**`
are on the forbidden-self-edit list. Weng's rule — keep "the runs directory, tracer,
verifier, and LLM configuration read-only" to the self-improving agent — is the same
insight. We got there first.

---

## Honest limits of this audit

- Throughput, revert and reliability figures from the 2026-07-24 pass were re-derived by
  a measurement agent and spot-verified by the author, but are now stale — see memory
  for current numbers before citing anything time-bound from that pass.
- Long-range systemd journal history for `factory-tick@sacrifice` rotates out;
  `ticks.ndjson` is the only durable record for that kind of retrospective.
- **External numbers above 80% on any SWE-bench variant should be treated as
  contaminated or unverifiable.** OpenAI's 2026-07-08 audit found ~30% of SWE-bench
  Pro's public tasks broken and retracted its recommendation; Cursor found Pro scores
  collapse when agents lose internet and git history, with some agents retrieving gold
  patches. swebench.com's own leaderboards are JS-rendered and could not be fetched;
  verified figures come from aggregators or from papers reporting their own runs.
- Several research agents reported that their fetch pipeline silently substituted proper
  nouns. Sources here are cited by **URL**, not by rendered title, for that reason.
- Model names post-dating May 2026 (Claude Mythos 5, GPT-5.6 Sol, Kimi K3, Muse Spark,
  Inkling) are reported as sourced, not independently confirmed.
- **The "we beat Claude Code cheaply" caveat is now moot — it has been measured, and we
  do not.** `bench/CAMPAIGN-2026-07-17.md` is superseded. Externally graded on
  SWE-rebench with a hidden oracle (2026-08-04, n=19, k=1): Claude Code on
  `claude-opus-5` resolves **79%** [54%, 94%], the factory chain **37%** [16%, 62%],
  paired McNemar exact **p=0.008**. Worse for the thesis, a single OpenHands agent on
  the factory's *own* model resolves **44%** [20%, 70%] — the chain shows **no
  measurable lift** over it (p=0.625) at 2.3× the cost per resolved instance. What
  produced the apparent lift was tooling, not orchestration (44% vs 6% for a no-tools
  loop, p=0.031). Full result: `bench/swebench/results.md`.
- **Contamination is not the explanation for Claude's lead.** `claude-opus-4-8`
  (published cutoff Jan 2026) scores 74% against `claude-opus-5`'s 79% on the same
  harness, p=1.000, even though all 19 instances predate opus-5's cutoff. The relevant
  caveat is the opposite one: `factory` vs any `claude-*` varies harness **and** model,
  so it is a reference point, not a scaffold deficit.

## What the field says is unsolved — i.e. don't expect to fix these

- **Verification, not generation, is the frontier.** No fixed reward function survives
  continued capability growth; verification must co-evolve. Adding a quality judge plus
  trajectory monitor moved hacked-resolved **28.57% → 0.56%** and clean-resolved
  **40.22% → 60.53%** — ~30% of unmonitored "successes" were exploits (arXiv 2606.26300).
- **Ultra-long-horizon autonomy is under 30%.** SWE-Marathon, 20 tasks of 40–400 human
  hours, 1,300 trials: no configuration passed 30%. Failure mix: 41.6% implementation,
  31.4% timeout, 15.4% reward hacking, 7.6% premature termination.
- **Auto-designed multi-agent systems are retired.** MAS-Zero GPT-5 scored 45.52% at
  $998 vs plain CoT-SC GPT-5 at 57.09% for $286. *Expert*-architected role splits still
  win — which is what our persona pipeline is. Don't let the FMS search topologies.
- **Harnesses may be depreciating assets.** The strongest dissent holds that harness
  components encode expiring assumptions and should be deletable within hours, with
  ~90-day replacement cycles; O'Reilly's "Kirby effect" describes frontier models
  swallowing scaffolding wholesale. Weng takes the opposite view. Unresolved — but it
  argues for keeping the *gates* (durable) and holding the *prompt scaffolding* loosely.
- **Self-evolution is model-specific.** GSME: "evolved harnesses are model-specific;
  the loop is what transfers." Harness-*updating* ability is roughly flat across model
  scale, while harness-*benefit* is non-monotonic and peaks at **mid-tier** models — so
  cheap proposers are fine, but don't assume a patch tuned on deepseek helps codex.
- **What a real self-improvement loop needs, per the literature** (relevant if
  `factory/manager/`'s self-improvement layer is revisited): an outcome archive keyed on
  **(where × why)**, not per-node score (HGM: selecting on clade-aggregate descendant
  performance beat DGM's per-node selection, 56.7% vs 53.3%, at 42% of the CPU cost);
  three gates in order of transferability — **validity** (re-run infra failures, keep in
  denominator), **activation** (credit a patch only if its instrumentation beacon
  actually fired), **significance** (paired significance test on a sealed split never
  consulted during search); and file-state patch collection over model-emitted unified
  diffs (Claw-SWE-Bench: 69.1% → <1.5% apply failures switching transport).
