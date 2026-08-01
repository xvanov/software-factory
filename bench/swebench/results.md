# SWE-bench Pro — externally graded

Generated 2026-08-01T22:52:30.102944+00:00.

`factory says` is the factory's OWN verdict (its gates, its tests). `oracle` is the hidden held-out suite. The pair is the point: the merge gate runs the dev's own tests, so precision against a hidden oracle is the only way to know whether that gate means anything.

`task_broken` is reported SEPARATELY from `wrong_patch`. OpenAI's 2026-07-08 audit found ~30% of this suite's public tasks broken, so summing the two would read a broken harness as factory failure.

| instance | arm | factory says | oracle | outcome | tokens in | tokens out | wall s |
|---|---|---|---|---|---:|---:|---:|
| instance_ansible__ansible-34db57a47f875d11c406 | bare | not green | FAIL | wrong_patch | 53,203 | 3,608 | 191.0 |
| instance_ansible__ansible-9a21e247786ebd294daf | bare | not green | FAIL | empty_patch | 2,567 | 963 | 5.5 |
| instance_ansible__ansible-9a21e247786ebd294daf | factory | not green | ? | — | 869,816 | 12,688 | 302.0 |
| instance_ansible__ansible-e22e103cdf8edc56ff7d | bare | not green | FAIL | wrong_patch | 42,687 | 4,461 | 79.6 |
| instance_internetarchive__openlibrary-3aeec6af | bare | not green | FAIL | wrong_patch | 11,503 | 2,370 | 88.0 |
| instance_internetarchive__openlibrary-798055d1 | bare | not green | FAIL | wrong_patch | 13,528 | 1,923 | 25.4 |
| instance_qutebrowser__qutebrowser-0833b5f6f140 | bare | not green | PASS | resolved | 1,100 | 75 | 4.5 |

## bare

- graded instances: **6** (0 excluded as `task_broken`, leaving 6)
- resolve rate: **1/6 = 17%**
- gate precision (oracle passes | factory said green): **n/a (0 in denominator)**
- gate recall (factory said green | oracle passes): **0/1 = 0%**

## factory

- graded instances: **0** (0 excluded as `task_broken`, leaving 0)
- resolve rate: **n/a (0 in denominator)**
- gate precision (oracle passes | factory said green): **n/a (0 in denominator)**
- gate recall (factory said green | oracle passes): **n/a (0 in denominator)**

> **n=6 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on.

> A factory number without the matched **bare-model** number beside it measures the MODEL, not the harness. See `PLAN.md` 1.4.
