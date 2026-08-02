# SWE-bench Pro — externally graded

Generated 2026-08-02T16:40:16.979179+00:00.

**Run of record (PLAN 1.5):** this paired factory+bare table (the 1.4 sweep,
#209) is the run of record. The earlier 2026-08-02T14:01:07Z table (#206)
disagreed with the artifacts then on disk and is superseded. From this commit
on, `report` refuses rows without backing artifacts and snapshots the
evidence for every row into `bench/swebench/results-archive/<generated-at>/`;
regenerate this file with `report --from-archive <dir>` to re-derive a
published table from its snapshot.

`factory says` is the chain's OWN verdict — it reached `reviewer_done`, i.e. dev got its tests green and the reviewer approved. `oracle` is the hidden held-out suite.

NOTE ON NAMING: the rates below are **chain-verdict** precision/recall, NOT merge-gate precision. This harness drives dev+review only; no merge gate runs. Of the six gates, only `tests-green` and `tests-meaningful` could even apply to a SWE-bench repo — `docs-current`, `acceptance-verified`, `smoke-green` and `canonical-paths-only` all require app capabilities these repos do not have. Calling this "gate precision" would overclaim.

`task_broken` is reported SEPARATELY from `wrong_patch`. OpenAI's 2026-07-08 audit found ~30% of this suite's public tasks broken, so summing the two would read a broken harness as factory failure.

| instance | arm | factory says | oracle | audit | outcome | tokens in | tokens out | wall s |
|---|---|---|---|---|---|---:|---:|---:|
| instance_ansible__ansible-34db57a47f875d11c406 | bare | not green | FAIL | ok | right_place_wrong_fix | 15,559 | 2,026 | 31.3 |
| instance_ansible__ansible-34db57a47f875d11c406 | factory | green | FAIL | ok | right_place_wrong_fix | 1,827,811 | 15,913 | 408.8 |
| instance_ansible__ansible-9a21e247786ebd294daf | bare | not green | FAIL | ok | right_place_wrong_fix | 45,500 | 10,378 | 85.7 |
| instance_ansible__ansible-9a21e247786ebd294daf | factory | green | FAIL | ok | right_place_wrong_fix | 568,132 | 7,620 | 125.0 |
| instance_ansible__ansible-e22e103cdf8edc56ff7d | bare | not green | FAIL | ok | right_place_wrong_fix | 107,720 | 17,976 | 146.6 |
| instance_ansible__ansible-e22e103cdf8edc56ff7d | factory | green | FAIL | ok | right_place_wrong_fix | 780,219 | 7,076 | 280.9 |
| instance_internetarchive__openlibrary-3aeec6af | bare | not green | FAIL | ok | empty_patch | 15,406 | 3,468 | 48.6 |
| instance_internetarchive__openlibrary-3aeec6af | factory | green | FAIL | ok | right_place_wrong_fix | 2,985,777 | 50,735 | 847.9 |
| instance_internetarchive__openlibrary-798055d1 | bare | not green | FAIL | ok | right_place_wrong_fix | 26,034 | 3,852 | 42.9 |
| instance_internetarchive__openlibrary-798055d1 | factory | green | FAIL | ok | right_place_wrong_fix | 733,449 | 8,769 | 160.1 |
| instance_qutebrowser__qutebrowser-0833b5f6f140 | bare | not green | PASS | ok | resolved | 2,764 | 113 | 6.8 |
| instance_qutebrowser__qutebrowser-0833b5f6f140 | factory | green | PASS | ok | resolved | 349,514 | 3,807 | 96.1 |

## bare

- graded instances: **6** (0 excluded as `task_broken`, leaving 6)
- audit gate: **6 audited-valid** of 6 gradable (audit failed: 0, not audited: 0, run failed: 0)
- resolve rate: **1/6 = 17% audited-valid**
- chain-verdict precision (oracle passes | chain said green): **n/a (0 in denominator)**
- chain-verdict recall (chain said green | oracle passes): **0/1 = 0%**

## factory

- graded instances: **6** (0 excluded as `task_broken`, leaving 6)
- audit gate: **6 audited-valid** of 6 gradable (audit failed: 0, not audited: 0, run failed: 0)
- resolve rate: **1/6 = 17% audited-valid**
- chain-verdict precision (oracle passes | chain said green): **1/6 = 17%**
- chain-verdict recall (chain said green | oracle passes): **1/1 = 100%**

> **n=6 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on.

> A factory number without the matched **bare-model** number beside it measures the MODEL, not the harness. See `PLAN.md` 1.4.
