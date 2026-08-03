# SWE-rebench — externally graded

Generated 2026-08-03T05:12:08.813897+00:00.

`factory says` is the chain's OWN verdict — it reached `reviewer_done`, i.e. dev got its tests green and the reviewer approved. `oracle` is the hidden held-out suite.

NOTE ON NAMING: the rates below are **chain-verdict** precision/recall, NOT merge-gate precision. This harness drives dev+review only; no merge gate runs. Of the six gates, only `tests-green` and `tests-meaningful` could even apply to a SWE-bench repo — `docs-current`, `acceptance-verified`, `smoke-green` and `canonical-paths-only` all require app capabilities these repos do not have. Calling this "gate precision" would overclaim.

`task_broken` is reported SEPARATELY from `wrong_patch`. This dataset execution-validates every instance upstream, so a non-trivial `task_broken` rate means THIS harness's plumbing broke, not the tasks.

| instance | arm | factory says | oracle | audit | outcome | tokens in | tokens out | wall s |
|---|---|---|---|---|---|---:|---:|---:|
| alibaba__opensandbox-816 | bare | not green | FAIL | ok | empty_patch | 503,319 | 77,755 | 1039.6 |
| alibaba__opensandbox-816 | claude | not green | FAIL | ok | right_place_wrong_fix | 1,307,672 | 25,880 | 375.9 |
| alibaba__opensandbox-816 | factory | green | FAIL | ok | wrong_place | 1,933,271 | 15,629 | 641.9 |
| conan-io__conan-19735_interface | bare | not green | FAIL | ok | empty_patch | 4,118 | 369 | 15.6 |
| conan-io__conan-19735_interface | claude | not green | PASS | ok | resolved | 240,246 | 4,095 | 74.3 |
| conan-io__conan-19735_interface | factory | green | FAIL | ok | right_place_wrong_fix | 627,686 | 6,044 | 447.3 |
| conan-io__conan-19750 | bare | not green | FAIL | ok | wrong_place | 238,763 | 60,701 | 818.3 |
| conan-io__conan-19750 | claude | not green | FAIL | ok | right_place_wrong_fix | 491,402 | 6,514 | 150.2 |
| conan-io__conan-19750 | factory | green | FAIL | ok | right_place_wrong_fix | 2,223,120 | 19,814 | 1133.8 |
| getmoto__moto-9841 | bare | not green | FAIL | ok | right_place_wrong_fix | 7,937 | 1,114 | 30.2 |
| getmoto__moto-9841 | claude | not green | PASS | ok | resolved | 663,760 | 9,641 | 227.6 |
| getmoto__moto-9841 | factory | green | PASS | ok | resolved | 1,478,679 | 14,823 | 266.8 |
| harumiweb__exstruct-113 | bare | not green | FAIL | ok | wrong_place | 15,388 | 4,011 | 59.4 |
| harumiweb__exstruct-113 | claude | not green | PASS | ok | resolved | 5,503,836 | 43,109 | 633.3 |
| harumiweb__exstruct-113 | factory | not green | FAIL | ok | empty_patch | 2,781,766 | 26,497 | 1101.9 |
| hiero-ledger__hiero-sdk-python-1914_interface | bare | not green | FAIL | ok | right_place_wrong_fix | 3,234 | 1,176 | 21.0 |
| hiero-ledger__hiero-sdk-python-1914_interface | claude | not green | PASS | ok | resolved | 970,895 | 19,097 | 270.5 |
| hiero-ledger__hiero-sdk-python-1914_interface | factory | green | FAIL | ok | right_place_wrong_fix | 4,581,075 | 49,016 | 1279.4 |
| hkuds__openharness-217 | bare | not green | FAIL | ok | right_place_wrong_fix | 32,136 | 3,653 | 114.7 |
| hkuds__openharness-217 | claude | not green | PASS | ok | resolved | 227,602 | 6,409 | 94.4 |
| hkuds__openharness-217 | factory | green | PASS | ok | resolved | 568,686 | 7,250 | 159.4 |
| idaholab__montepy-933_interface | bare | not green | FAIL | ok | right_place_wrong_fix | 17,003 | 2,333 | 41.4 |
| idaholab__montepy-933_interface | claude | not green | PASS | ok | resolved | 2,477,578 | 19,644 | 353.9 |
| idaholab__montepy-933_interface | factory | green | PASS | ok | resolved | 4,193,280 | 45,129 | 1417.7 |
| jsonpickle__jsonpickle-588 | bare | not green | FAIL | ok | empty_patch | 3,745 | 49 | 12.6 |
| jsonpickle__jsonpickle-588 | claude | not green | PASS | ok | resolved | 4,080,731 | 51,944 | 825.3 |
| jsonpickle__jsonpickle-588 | factory | green | PASS | ok | resolved | 7,114,363 | 87,747 | 2078.4 |
| keras-team__keras-22316 | bare | not green | FAIL | ok | wrong_place | 51,997 | 22,269 | 393.8 |
| keras-team__keras-22316 | claude | not green | PASS | ok | resolved | 2,230,504 | 23,081 | 619.8 |
| keras-team__keras-22316 | factory | not green | FAIL | ok | empty_patch | 163,402 | 5,772 | 160.1 |
| keras-team__keras-22642 | bare | not green | FAIL | ok | right_place_wrong_fix | 339,249 | 104,182 | 1413.2 |
| keras-team__keras-22642 | claude | not green | PASS | ok | resolved | 752,453 | 9,543 | 172.5 |
| keras-team__keras-22642 | factory | green | PASS | ok | resolved | 1,458,781 | 11,189 | 530.0 |
| line__line-bot-sdk-python-981_interface | bare | not green | FAIL | ok | right_place_wrong_fix | 10,718 | 2,377 | 107.6 |
| line__line-bot-sdk-python-981_interface | claude | not green | PASS | ok | resolved | 2,977,374 | 33,081 | 477.2 |
| line__line-bot-sdk-python-981_interface | factory | green | PASS | ok | resolved | 3,364,711 | 34,806 | 641.9 |
| pandas-dev__pandas-63945 | bare | not green | FAIL | ok | right_place_wrong_fix | 18,889 | 6,732 | 164.4 |
| pandas-dev__pandas-63945 | claude | not green | PASS | ok | resolved | 800,303 | 11,065 | 284.4 |
| pandas-dev__pandas-63945 | factory | not green | FAIL | ok | right_place_wrong_fix | 1,712,344 | 24,671 | 709.3 |
| pyinfra-dev__pyinfra-1665 | bare | not green | FAIL | ok | right_place_wrong_fix | 33,699 | 9,202 | 133.1 |
| pyinfra-dev__pyinfra-1665 | claude | not green | PASS | ok | resolved | 618,995 | 7,584 | 133.8 |
| pyinfra-dev__pyinfra-1665 | factory | green | PASS | ok | resolved | 1,220,242 | 8,844 | 296.1 |
| raullenchai__rapid-mlx-289 | bare | not green | FAIL | ok | right_place_wrong_fix | 65,346 | 18,142 | 208.4 |
| raullenchai__rapid-mlx-289 | claude | not green | PASS | ok | resolved | 4,461,461 | 62,922 | 812.4 |
| raullenchai__rapid-mlx-289 | factory | green | PASS | ok | resolved | 4,389,311 | 48,780 | 1467.4 |
| tox-dev__tox-3931 | bare | not green | FAIL | ok | right_place_wrong_fix | 32,099 | 15,721 | 171.4 |
| tox-dev__tox-3931 | claude | not green | PASS | ok | resolved | 618,155 | 6,973 | 127.6 |
| tox-dev__tox-3931 | factory | green | PASS | ok | resolved | 2,766,409 | 19,021 | 513.9 |
| ucfopen__canvasapi-716 | bare | not green | FAIL | ok | empty_patch | 161,477 | 11,563 | 169.4 |
| ucfopen__canvasapi-716 | claude | not green | PASS | ok | resolved | 479,693 | 7,496 | 125.4 |
| ucfopen__canvasapi-716 | factory | green | FAIL | ok | right_place_wrong_fix | 996,540 | 9,031 | 273.7 |
| vyperlang__vyper-4801 | bare | not green | FAIL | ok | empty_patch | 38,966 | 27,504 | 322.9 |
| vyperlang__vyper-4801 | claude | not green | PASS | ok | resolved | 1,687,565 | 17,841 | 1909.1 |
| vyperlang__vyper-4801 | factory | green | PASS | ok | resolved | 4,735,865 | 39,474 | 1246.8 |
| zauberzeug__nicegui-5858 | bare | not green | FAIL | ok | empty_patch | 6,120 | 710 | 37.0 |
| zauberzeug__nicegui-5858 | claude | not green | PASS | ok | resolved | 1,243,259 | 13,508 | 276.0 |
| zauberzeug__nicegui-5858 | factory | green | PASS | ok | resolved | 954,719 | 10,367 | 260.2 |

## Excluded rows (other manifest/profile)

These runs did not run under the pinned manifest `923aef05add32124`,
so they are NOT table rows and count in NO rate above — merging
runs from two manifests (e.g. a previous dataset's leftovers in
`runs/`) would blend incomparable numbers into one headline.

- `instance_ansible__ansible-34db57a47f875d11c4068567b9ec7ace174ec4cf-v1055803c3a812189a1133297f7f5468579283f86/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-34db57a47f875d11c4068567b9ec7ace174ec4cf-v1055803c3a812189a1133297f7f5468579283f86/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-9a21e247786ebd294dafafca1105fcd770ff46c6-v67cdaa49f89b34e42b69d5b7830b3c3ad3d8803f/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-9a21e247786ebd294dafafca1105fcd770ff46c6-v67cdaa49f89b34e42b69d5b7830b3c3ad3d8803f/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-e22e103cdf8edc56ff7d9b848a58f94f1471a263-v1055803c3a812189a1133297f7f5468579283f86/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-e22e103cdf8edc56ff7d9b848a58f94f1471a263-v1055803c3a812189a1133297f7f5468579283f86/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_internetarchive__openlibrary-3aeec6afed9198d734b7ee1293f03ca94ff970e1-v13642507b4fc1f8d234172bf8129942da2c2ca26/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_internetarchive__openlibrary-3aeec6afed9198d734b7ee1293f03ca94ff970e1-v13642507b4fc1f8d234172bf8129942da2c2ca26/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_internetarchive__openlibrary-798055d1a19b8fa0983153b709f460be97e33064-v13642507b4fc1f8d234172bf8129942da2c2ca26/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_internetarchive__openlibrary-798055d1a19b8fa0983153b709f460be97e33064-v13642507b4fc1f8d234172bf8129942da2c2ca26/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_qutebrowser__qutebrowser-0833b5f6f140d04200ec91605f88704dd18e2970-v059c6fdc75567943479b23ebca7c07b5e9a7f34c/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_qutebrowser__qutebrowser-0833b5f6f140d04200ec91605f88704dd18e2970-v059c6fdc75567943479b23ebca7c07b5e9a7f34c/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124

## bare

- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **19 audited-valid** of 19 gradable (audit failed: 0, not audited: 0, run failed: 0)
- resolve rate: **0/19 = 0% audited-valid**
- chain-verdict precision (oracle passes | chain said green): **n/a (0 in denominator)**
- chain-verdict recall (chain said green | oracle passes): **n/a (0 in denominator)**

## claude

- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **18 audited-valid** of 19 gradable (audit failed: 0, not audited: 0, run failed: 1)
- resolve rate: **16/18 = 89% audited-valid**; **1 oracle-pass EXCLUDED** (harumiweb__exstruct-113: run failed)
- chain-verdict precision (oracle passes | chain said green): **n/a (0 in denominator)**
- chain-verdict recall (chain said green | oracle passes): **0/16 = 0%**

## factory

- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **19 audited-valid** of 19 gradable (audit failed: 0, not audited: 0, run failed: 0)
- resolve rate: **11/19 = 58% audited-valid**
- chain-verdict precision (oracle passes | chain said green): **11/16 = 69%**
- chain-verdict recall (chain said green | oracle passes): **11/11 = 100%**

> **n=19 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on.

> A factory number without the matched **bare-model** number beside it measures the MODEL, not the harness. See `PLAN.md` 1.4.
