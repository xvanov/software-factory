# SWE-bench Pro — externally graded

Generated 2026-08-02T14:01:07.668444+00:00.

`factory says` is the chain's OWN verdict — it reached `reviewer_done`, i.e. dev got its tests green and the reviewer approved. `oracle` is the hidden held-out suite.

NOTE ON NAMING: the rates below are **chain-verdict** precision/recall, NOT merge-gate precision. This harness drives dev+review only; no merge gate runs. Of the six gates, only `tests-green` and `tests-meaningful` could even apply to a SWE-bench repo — `docs-current`, `acceptance-verified`, `smoke-green` and `canonical-paths-only` all require app capabilities these repos do not have. Calling this "gate precision" would overclaim.

`task_broken` is reported SEPARATELY from `wrong_patch`. OpenAI's 2026-07-08 audit found ~30% of this suite's public tasks broken, so summing the two would read a broken harness as factory failure.

| instance | arm | factory says | oracle | audit | outcome | tokens in | tokens out | wall s |
|---|---|---|---|---|---|---:|---:|---:|
| instance_ansible__ansible-34db57a47f875d11c406 | factory | green | FAIL | ok | right_place_wrong_fix | 2,299,905 | 23,472 | 419.0 |
| instance_ansible__ansible-9a21e247786ebd294daf | factory | green | FAIL | ok | right_place_wrong_fix | 1,178,263 | 10,247 | 170.4 |
| instance_ansible__ansible-e22e103cdf8edc56ff7d | factory | green | FAIL | ok | right_place_wrong_fix | 771,717 | 7,218 | 153.6 |
| instance_internetarchive__openlibrary-3aeec6af | factory | not green | FAIL | ok | empty_patch | 142,903 | 4,772 | 70.6 |
| instance_internetarchive__openlibrary-798055d1 | factory | green | FAIL | ok | right_place_wrong_fix | 1,471,747 | 13,810 | 201.7 |
| instance_qutebrowser__qutebrowser-0833b5f6f140 | factory | green | PASS | ok | resolved | 560,594 | 5,488 | 123.3 |

## factory

- graded instances: **6** (0 excluded as `task_broken`, leaving 6)
- audit gate: **6 audited-valid** of 6 gradable (audit failed: 0, not audited: 0, run failed: 0)
- resolve rate: **1/6 = 17% audited-valid**
- chain-verdict precision (oracle passes | chain said green): **1/5 = 20%**
- chain-verdict recall (chain said green | oracle passes): **1/1 = 100%**

> **n=6 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on.

> A factory number without the matched **bare-model** number beside it measures the MODEL, not the harness. See `PLAN.md` 1.4.
