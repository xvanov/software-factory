# Personas — contracts, model tiers, and breakpoints

## Overview

`factory/personas/*.md` are load-bearing protocol specs: each defines what a
persona receives, what output schema it must emit (or what files it must
land via tool calls), and what downstream stage consumes that artifact.
`factory/personas/loader.py` parses every file as optional-YAML-frontmatter
+ markdown body (every current file has no frontmatter and parses as
all-defaults); `load_persona()`/`read_persona_prompt()` strip frontmatter
before it reaches a model. Model routing is external: `factory/routes.yaml`
maps persona name → LiteLLM model id, so retiering a persona is a YAML edit,
not a prompt change. 20 persona `.md` files exist; `available_personas()`
treats the directory's `*.md` glob as the registry.

## Key concepts

- **Two execution modes.** JSON-only personas (`pm`, `analyst`, `architect`,
  `sm`, `ux_designer`, `test_designer`, `acceptance_author`, `reviewer`,
  `tech_writer`, `release_manager`, `bug_hunter`, `ralph`, `security`,
  `ux_auditor`, `factory_improver`, the manager stack,
  `factory_self_context`) return one JSON object via `text_run` — the chain
  reads the return value, never a file. Tool-using personas (`dev`,
  `test_implementer`, `onboarder`) run in an OpenHands sandbox and must land
  changes via file-edit/Bash calls; the chain checks `git diff`/`git
  status`/exit code after the sandbox exits, so chat-only "I changed X" is a
  failed run.
- **Canonical handoff chain (`chain_kind="tdd"`, default):** `pm` triages +
  decomposes a `Direction` → `architect` (only above the architectural
  threshold) rewrites current-state/diagrams → `sm` writes one BMAD story
  file per child story (calling `ux_designer` first when a frontend story's
  `flow.md` has gaps) → `acceptance_author` authors a spec-blind oracle test
  at spawn time → `test_designer` plans tests → `test_implementer` writes
  the red tests → `dev` implements against them (owns code AND tests) →
  `reviewer` verdicts the PR → `tech_writer` rewrites context after approval
  → merge gates (incl. the acceptance oracle) → auto-merge →
  `release_manager` validates/structures the deploy plan.
- **Docs chain (`chain_kind="docs"`):** `sm` (docs mode) → `onboarder` →
  `factory/context/enforcer.py` → PR. Skips test_design/test_impl/dev/
  reviewer — for stories whose entire deliverable is canonical docs.
- **`analyst`** is a side-branch off `pm` for epic-shaped directions
  (phases/metrics/risks); it does not replace PM's `child_stories` — both
  lists go to the user.
- **Independent acceptance oracle (`acceptance_author`, WS1.2).** Authored
  at story-spawn time (pm-sync), from the spec alone — never the dev's code
  or tests. Stored under `state/acceptance/<app>/<story_id>/`, outside the
  app repo and the dev's worktree, so the dev sandbox has no path to it.
  `StoryRecord.acceptance_test_ref` holds the stored ref; whether one is
  required is fixed at spawn (`gates.acceptance_oracle AND
  direction.acceptance`), independent of whether authoring later succeeds.
- **EARS mode.** `sm` decomposes every verbatim AC into
  `### Testable Claims (EARS)` (`AC<n>.<m>: WHEN … SHALL …`). When EARS
  claims are present, `acceptance_author` encodes them as Hypothesis
  `@given(...)` property tests instead of single examples.
- **Scheduled / finding-only personas** never touch code: `bug_hunter`
  (daily, static-analysis tools), `ralph` (hourly, spec/context drift),
  `security` (weekly + on `(security)`-tagged directions), `ux_auditor`
  (daily/per-deploy; v1 wiring is `text_run` against the static prelude —
  the live-browser/Playwright sandbox path is reserved, not yet live),
  `factory_improver` (daily), and the manager ladder `manager_watcher` →
  `manager_summarizer` → `manager_diagnostician`. All return JSON; handlers
  turn that into filed directions or pinned-issue/proposal updates — never
  a persona-opened GitHub issue or direct patch.
- **Shared canonical-paths contract.** `architect`, `sm`, `tech_writer`,
  `dev`, `onboarder` share one allowlist (`prd.md`, `context/project.md`,
  `context/current-state.md`, `context/architecture-diagrams.md`,
  `context/navigation.md`, `context/glossary.md`,
  `context/sprint-status.yaml`, `context/modules/*.md`, `stories/*.md`) and
  one forbidden list (`context/decisions/*`, `context/changelog.md`,
  `context/history.md`, `context/old-*`, `context/archive/*`,
  `docs/decisions/*`, `docs/adr/*`). Rewrites are full-file replacements —
  no append, no "we used to do X" framing; `factory/context/enforcer.py`
  rejects the ENTIRE output if any emitted path is non-canonical/forbidden.
- **Architectural-threshold routing.** `architect` runs when PM's result has
  `len(child_stories) >= 3`, OR any child scope is `infra`, OR a title
  mentions `schema`/`migration`/`dependency`/`rewrite`/`architecture`.
- **Dev/test enforcement is diff-based, not self-reported** — see Failure
  modes/Escalation paths below. Note: dev.md's *only* current escape hatch
  for a bad AC is `SELF_SUMMARY:`; there is no literal
  `TESTS_NEED_CLARIFICATION:` output-prefix requirement in the current
  prompt, though `factory_improver.md` still lists strengthening that
  language as an open heuristic.
- **Review convergence is chain-capped**, not persona-enforced — the
  dev↔reviewer loop is hard-capped at 3 cycles regardless of what `reviewer`
  finds; see Escalation paths.
- **Every persona has an explicit null/refusal path.** `pm` → `child_stories:
  []` on insufficient backpressure; `release_manager` → `deploy_plan: []`
  on a missing mandatory command, destructive shell pattern, or >32 steps;
  `bug_hunter`/`ralph`/`security`/`ux_auditor` → empty findings rather than
  invented work; `manager_diagnostician` → `escalate_to_human: true` with an
  emptied `suggested_patch` rather than a low-confidence patch.

## Key files

- `factory/routes.yaml` — model routing, per-model output-token caps,
  sandbox LLM-constructor overrides. `factory/model_router.py` reads it.
- `factory/personas/loader.py` — frontmatter/body parsing + persona
  registry; `factory/personas/validator.py` — output-schema validation.
- `factory/personas/{pm,analyst,architect,sm,ux_designer}.md` — direction
  triage through story prep (see chain diagram above for each one's role).
- `factory/personas/acceptance_author.md` — spec-blind oracle author;
  `factory/chain/acceptance.py` is the calling code.
- `factory/personas/{test_designer,test_implementer,dev,reviewer}.md` — the
  TDD implementation loop.
- `factory/personas/tech_writer.md`, `onboarder.md` — post-approval and
  one-time (phase-budgeted: ≤30 reads, ≤50 tool calls) context rewrites.
- `factory/personas/release_manager.md` — validates/structures the deploy
  plan; refuses on missing safety commands or destructive patterns.
- `factory/personas/{bug_hunter,ralph,security,ux_auditor}.md` — scheduled,
  code-untouching finding generators.
- `factory/personas/{factory_improver,manager_watcher,manager_summarizer,
  manager_diagnostician}.md` — factory self-observation + FMS escalation
  stack (L1→L2→L3; only L3 has halt authority).
- `factory/personas/factory_self_context.md` — generates this class of
  context-module doc for the factory's own subsystems.

## Failure modes

- **JSON/protocol mismatch.** A JSON-only persona emits prose, wrong schema,
  or a field outside contract. Symptom: chain parser rejects it, downstream
  stage never starts. Highest-risk: `sm` (20k-token hard cap — must
  self-truncate with `TRUNCATED_INDICATOR`), `manager_diagnostician` (must
  emit a valid unified diff or L4's `git apply` drops the proposal as
  `invalid`).
- **No-op tool-persona runs.** `dev`/`test_implementer`/`onboarder` describe
  changes in chat but call no file-edit tool. Symptom: empty `git diff`/
  `git status` after sandbox exit; run marked failed (onboarder specifically
  checks `git status --porcelain`).
- **Forbidden/non-canonical path writes.** `architect`/`sm`/`tech_writer`/
  `dev`/`onboarder` emit a path outside the canonical set. Symptom:
  `factory/context/enforcer.py` rejects the ENTIRE output.
- **Oversized/mis-sized PM decomposition.** A child story exceeds the hard
  caps (>5 new files / >2 modified / >200 iterations) — horizontal
  scope-grouping instead of vertical slicing (PM's own D007 anti-example).
  Symptom: chain rejection, or a dev sandbox that exhausts 600 iterations.
- **False-red / unsatisfiable tests.** `test_implementer` accepts a
  collection-time `ImportError`/broken-`conftest` failure as "red"; or
  `test_designer`/`test_implementer` assert against an aspirational
  `api_spec.md` example instead of the real delegated-to contract. Symptom:
  dev gets an unusable or unsatisfiable baseline; the story stalls
  regardless of dev quality.
- **Dev/test contract violation.** Dev edits a frozen test (diff-detected)
  or exhausts retries. Symptom: chain routes to terminal
  `BLOCKED_TESTS_NEED_CLARIFICATION` (recovery transition:
  `BLOCKED_TESTS_NEED_CLARIFICATION → SM_DONE` once a human clarifies).
- **Acceptance-oracle independence break.** If `acceptance_author` were ever
  wired to see the dev's code/tests, the oracle stops being an honest spec
  judge. The control is architectural (state storage outside the worktree),
  not a prompt instruction the model could be argued out of.
- **Truncated output from token caps.** Configured caps: `deepseek/
  deepseek-chat` and `deepseek-coder` = 8192; `azure/gpt-5.4` = 16384;
  `azure/deepseek-v4-pro` = 8192; `azure/gpt-5.3-codex` = 16384; unlisted
  models fall back to 8192. Large-payload personas (`sm`, `architect`,
  manager stack) can still overflow on a verbose response. Symptom: partial
  JSON, `JSONDecodeError`, or a `finish_reason=length` string —
  `manager_watcher.md` treats that exact string as escalation-worthy on
  first occurrence because the diagnosis is self-evident.
- **Missing-route silent fallback.** `test_designer` and
  `factory_self_context` have NO entry in `routes.yaml`'s `routes:` or
  `azure_routes:` blocks — they resolve via `defaults.azure_fallback`
  (`azure/gpt-5.4`) / `defaults.fallback` (`deepseek/deepseek-chat`).
  Deliberate router feature, but these two move silently if the defaults
  change, with no explicit line in the routing file.
- **Provider-key degradation.** `model_router.route()` silently degrades any
  route whose provider API key is missing to the active block's fallback
  (warned once per persona+model) — a misconfigured `.env` changes which
  model runs a persona without failing loudly.
- **Unsafe deploy-plan acceptance.** The refusal in `release_manager` (missing
  safety command / destructive shell substring) is prompt-enforced
  (`deploy_plan: []` + `rationale`); no second code-side check is described
  in the persona file itself.

## Escalation paths

- **`dev` test conflict:** touching a frozen test, or exhausting retries,
  routes to the terminal `BLOCKED_TESTS_NEED_CLARIFICATION` state (state
  machine transitions on `EVENT_DEV_EXHAUSTED`, or a branch-diff check); the
  orchestrator's recovery mapping allows `→ SM_DONE` to restart from
  story-prep.
- **`test_implementer` slop or unsatisfiable red:** sets
  `slop_detected: true`; the chain routes the plan back to `test_designer`.
- **`reviewer` rejection:** `verdict: request_changes` blocks approval;
  `medium`/`high` findings (only `correctness|contract|security|tests` may
  block) route back to `dev`, which applies `suggested_edit` blocks
  verbatim where offered. Capped at 3 cycles; non-convergent stories
  terminate at `blocked_review_nonconvergent`. `test_quality_score < 0.7`
  forces `request_changes` regardless of code findings.
- **`architect`/`sm`/`tech_writer`/`dev`/`onboarder` forbidden paths:**
  `factory/context/enforcer.py` rejects the entire output, not a partial
  acceptance.
- **`release_manager` invalid plan:** `deploy_plan: []` + refusal
  `rationale`; the deploy orchestrator does not proceed.
- **Scheduled personas** (`bug_hunter`, `ralph`, `security`, `ux_auditor`,
  `factory_improver`) never modify code or open issues directly.
  `run_scheduled_persona` (the first four) or the dedicated
  `factory_improver.py` handler converts findings into filed directions (the
  normal `pm`→... chain) or a pinned, idempotently-updated `factory-
  improvements` GitHub issue.
- **FMS stack:** `manager_watcher` (L1, every 60s) summarizes and may set
  `escalate_to_l2` — one override: `stalled_stories.alarms` non-empty
  ALWAYS forces escalation. `manager_summarizer` (L2, every 3 min or on L1
  escalation) emits a concern with `urgency: continue|warn|halt` and may set
  `escalate_to_l3`. `manager_diagnostician` (L3, escalation-only) emits a
  root-cause proposal with a unified-diff patch and a `target_class` safety
  gate (`prompt_edit` may auto-merge; `persona_settings`/`dispatch_code`/
  `detector_tool` are always a human-review PR), or sets
  `escalate_to_human: true` on low confidence. **Only L3 may request a
  factory-wide halt** (`request_halt: true` + non-empty `halt_reason`) — L1
  and L2 have no halt authority.
- **Operator intervention:** `factory resume` is the only way to clear a
  halt — an operator action automation must never trigger. Otherwise, human
  intervention arrives via a blocked/terminal story state, a
  `request_changes` PR, a pinned `factory-improvements` issue, or a
  `manager_diagnostician` proposal that classified as risky and became a PR.

### Persona inventory: consumes → produces, model, breakpoint

Azure model shown first (active: `default_provider: azure`), direct-provider
fallback in parentheses. No entry in either `routes.yaml` block → resolves
via `defaults.azure_fallback` / `defaults.fallback`.

- **`pm`** — Direction+context → type/priority/backpressure/`child_stories[]`;
  `azure/gpt-5.4` (`deepseek/deepseek-chat`); breaks on oversized/horizontal
  child stories or fabricated ACs.
- **`analyst`** — Direction+PM JSON → phases/metrics/risks; `azure/gpt-5.4`
  (`deepseek/deepseek-chat`); breaks by inventing requirements or replacing
  PM's stories silently.
- **`architect`** — PM result+context → full-file `context_updates[]`;
  `azure/gpt-5.4` both blocks; breaks on forbidden paths or speculative
  future-state diagrams.
- **`sm`** — direction+PM JSON+context → one story's JSON (`target_path`
  issue placeholder `0`); `azure/gpt-5.4` both blocks; 20k-token ceiling
  (self-truncates past 16k); breaks on invented ACs or budget overflow.
- **`ux_designer`** — story+flow.md+context → `flow_additions`/`ui_notes`;
  `azure/gpt-5.4` both blocks; breaks by inventing gaps or proposing backend
  work.
- **`acceptance_author`** — spec ONLY (no dev code/tests) →
  `{"test_file_content": "..."}` (Hypothesis property tests under EARS);
  `azure/gpt-5.4` both blocks — deliberately a different model family than
  `dev`/`test_implementer` (DeepSeek) to reinforce independence; breaks by
  weakening an assertion to match an anticipated implementation.
- **`test_designer`** — story+flow/api spec+gates → `test_plan[]`+
  `e2e_required`; **not routed** → `azure/gpt-5.4`/`deepseek/deepseek-chat`
  fallback; breaks by planning an E2E test when `e2e_harness_ready` is false
  or grounding on an aspirational spec example.
- **`test_implementer`** — test plan+story+gates → test files on disk +
  `slop_detected`/`exit_code` report; `azure/deepseek-v4-pro`
  (`deepseek/deepseek-coder`); `reasoning_effort: "none"`; breaks on green
  pre-impl tests or harness-failure mistaken for red.
- **`dev`** — story+repo+context → code+tests on disk + `SELF_SUMMARY:`;
  standard `azure/deepseek-v4-pro` (`deepseek/deepseek-coder`) /
  hard `azure/gpt-5.3-codex` both blocks (deliberately a different model
  family — escapes Azure content-filter blocks, adds a capability jump);
  `reasoning_effort: "none"` standard / `high` hard; breaks on touching
  frozen tests or exhausting retries without landing code.
- **`reviewer`** — PR diff+story+tests+dev self-summary+context →
  `verdict`/`findings[]`+`test_quality_score`; `azure/gpt-5.3-codex` both
  blocks; `reasoning_effort: high` (sandbox reviews only); carries a
  provenance mandate — story-silent literals/formats/data sources must cite a
  repo precedent (`file:line`) in the dev's self-summary, and same-diff test
  fixtures are never evidence; breaks by moving the goalposts on re-review
  (chain clamps this past cycle 3) or approving below the 0.7 test-quality
  threshold.
- **`tech_writer`** — final PR diff+context+story → full-file
  `context_updates[]`; `azure/gpt-5.4` (`deepseek/deepseek-chat`); breaks on
  non-canonical paths or preserving reversed decisions.
- **`onboarder`** — existing repo only, once per app → full canonical
  `context/` set on disk (≤30 reads, ≤50 tool calls); `azure/gpt-5.4` both
  blocks; breaks on exhausting budget with nothing written.
- **`release_manager`** — merged-PR metadata+`DeployConfig` → ordered
  `deploy_plan[]`+`rollback_command`; `azure/gpt-5.4`
  (`deepseek/deepseek-chat`); breaks by accepting a plan missing a mandatory
  command or missing a destructive-pattern match.
- **`bug_hunter`** — app config+root → runs scanner subprocesses →
  `findings[]`+`runs_completed[]`; `azure/gpt-5.4` (`deepseek/deepseek-chat`);
  breaks by silently skipping a missing tool instead of recording
  `<tool>:errored`, or spamming duplicate directions.
- **`ralph`** — app config+prd+context+source → `drifts[]` (spec|context);
  `azure/gpt-5.4` (`deepseek/deepseek-chat`); output <1024 tokens; breaks by
  inventing drift without a cited file/test.
- **`security`** — app config+docs+source(+direction on tagged runs) →
  `threat_model_summary`+`findings[]`; `azure/gpt-5.3-codex` both blocks;
  ~3000 output tokens; breaks on uncited findings.
- **`ux_auditor`** — app config+extracted flow.md files (v1: `text_run`,
  static prelude — live-browser path reserved, not shipped) → `findings[]`
  (friction|accessibility|broken-affordance|slow); `azure/gpt-5.4`
  (`deepseek/deepseek-chat`); breaks by inventing a finding or side-effecting
  the working tree.
- **`factory_improver`** — redesign events+blocked stories+persona index+
  state-machine summary → `improvements[]` with a REQUIRED unified-diff
  `suggested_patch`; `azure/gpt-5.4` (`deepseek/deepseek-chat`); breaks on a
  free-text recipe (auto-dropped as invalid).
- **`manager_watcher`** (L1) — signals+detector results+prior notes →
  `summary`+`escalate_to_l2`+`observations[]`; `azure/deepseek-v4-pro` both
  blocks (cheapest deployed model; L1 fires every 60s and historically drove
  ~88% of persona-call spend); breaks by escalating on one ambiguous event or
  missing a `stalled_stories` alarm.
- **`manager_summarizer`** (L2) — flagged notes+signals+detector docstrings+
  up to 5 prior concerns → concern doc+`urgency`+`escalate_to_l3`;
  `azure/gpt-5.4` both blocks; breaks by fabricating evidence or escalating
  `review_churn` alone.
- **`manager_diagnostician`** (L3) — one concern+pre-loaded source+detector
  hints → `diagnosis`+`proposal` (unified diff+`target_class`)+optional
  `request_halt`; `azure/gpt-5.3-codex` both blocks — the only persona with
  halt authority; breaks by shipping a low-confidence speculative patch
  instead of escalating, or repeating a listed failed attempt.
- **`factory_self_context`** — module name/topic+source bundle → ≤2000-word
  Markdown context module; **not routed** → `azure/gpt-5.4`/`deepseek/
  deepseek-chat` fallback; breaks by inventing unconfirmed behavior instead
  of writing "not confirmed in provided source."
