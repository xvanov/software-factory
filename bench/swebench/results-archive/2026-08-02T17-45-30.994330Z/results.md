# SWE-bench Pro — externally graded

Generated 2026-08-02T17:45:30.994330+00:00.

`factory says` is the chain's OWN verdict — it reached `reviewer_done`, i.e. dev got its tests green and the reviewer approved. `oracle` is the hidden held-out suite.

NOTE ON NAMING: the rates below are **chain-verdict** precision/recall, NOT merge-gate precision. This harness drives dev+review only; no merge gate runs. Of the six gates, only `tests-green` and `tests-meaningful` could even apply to a SWE-bench repo — `docs-current`, `acceptance-verified`, `smoke-green` and `canonical-paths-only` all require app capabilities these repos do not have. Calling this "gate precision" would overclaim.

`task_broken` is reported SEPARATELY from `wrong_patch`. OpenAI's 2026-07-08 audit found ~30% of this suite's public tasks broken, so summing the two would read a broken harness as factory failure.

| instance | arm | factory says | oracle | audit | outcome | tokens in | tokens out | wall s |
|---|---|---|---|---|---|---:|---:|---:|
| instance_ansible__ansible-34db57a47f875d11c406 | bare | not green | FAIL | ok | right_place_wrong_fix | 15,559 | 2,026 | 31.3 |
| instance_ansible__ansible-34db57a47f875d11c406 | factory | green | FAIL | ok | right_place_wrong_fix | 2,523,593 | 23,594 | 525.9 |
| instance_ansible__ansible-9a21e247786ebd294daf | bare | not green | FAIL | ok | right_place_wrong_fix | 45,500 | 10,378 | 85.7 |
| instance_ansible__ansible-9a21e247786ebd294daf | factory | green | FAIL | ok | right_place_wrong_fix | 1,346,869 | 11,681 | 288.0 |
| instance_ansible__ansible-e22e103cdf8edc56ff7d | bare | not green | FAIL | ok | right_place_wrong_fix | 107,720 | 17,976 | 146.6 |
| instance_ansible__ansible-e22e103cdf8edc56ff7d | factory | green | FAIL | ok | right_place_wrong_fix | 841,910 | 6,570 | 182.2 |
| instance_internetarchive__openlibrary-3aeec6af | bare | not green | FAIL | ok | empty_patch | 15,406 | 3,468 | 48.6 |
| instance_internetarchive__openlibrary-3aeec6af | factory | not green | FAIL | ok | empty_patch | 1,675,288 | 19,073 | 644.2 |
| instance_internetarchive__openlibrary-798055d1 | bare | not green | FAIL | ok | right_place_wrong_fix | 26,034 | 3,852 | 42.9 |
| instance_internetarchive__openlibrary-798055d1 | factory | green | FAIL | ok | right_place_wrong_fix | 1,198,619 | 15,564 | 329.9 |
| instance_qutebrowser__qutebrowser-0833b5f6f140 | bare | not green | PASS | ok | resolved | 2,764 | 113 | 6.8 |
| instance_qutebrowser__qutebrowser-0833b5f6f140 | factory | green | PASS | ok | resolved | 848,805 | 6,629 | 288.3 |

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
- chain-verdict precision (oracle passes | chain said green): **1/5 = 20%**
- chain-verdict recall (chain said green | oracle passes): **1/1 = 100%**

> **n=6 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on.

> A factory number without the matched **bare-model** number beside it measures the MODEL, not the harness. See `PLAN.md` 1.4.
