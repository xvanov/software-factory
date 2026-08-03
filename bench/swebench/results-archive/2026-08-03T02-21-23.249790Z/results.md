# SWE-rebench — externally graded

Generated 2026-08-03T02:21:23.249790+00:00.

`factory says` is the chain's OWN verdict — it reached `reviewer_done`, i.e. dev got its tests green and the reviewer approved. `oracle` is the hidden held-out suite.

NOTE ON NAMING: the rates below are **chain-verdict** precision/recall, NOT merge-gate precision. This harness drives dev+review only; no merge gate runs. Of the six gates, only `tests-green` and `tests-meaningful` could even apply to a SWE-bench repo — `docs-current`, `acceptance-verified`, `smoke-green` and `canonical-paths-only` all require app capabilities these repos do not have. Calling this "gate precision" would overclaim.

`task_broken` is reported SEPARATELY from `wrong_patch`. This dataset execution-validates every instance upstream, so a non-trivial `task_broken` rate means THIS harness's plumbing broke, not the tasks.

| instance | arm | factory says | oracle | audit | outcome | tokens in | tokens out | wall s |
|---|---|---|---|---|---|---:|---:|---:|
| alibaba__opensandbox-816 | bare | not green | FAIL | ok | wrong_place | 2,835 | 953 | 16.8 |
| alibaba__opensandbox-816 | factory | green | FAIL | ok | wrong_place | 1,933,271 | 15,629 | 641.9 |
| conan-io__conan-19735_interface | bare | not green | FAIL | ok | right_place_wrong_fix | 9,212 | 1,015 | 16.1 |
| conan-io__conan-19735_interface | factory | green | FAIL | FAIL | right_place_wrong_fix | 524,588 | 5,482 | 139.2 |
| conan-io__conan-19750 | bare | not green | FAIL | ok | empty_patch | 80,599 | 10,938 | 116.5 |
| conan-io__conan-19750 | factory | green | FAIL | ok | right_place_wrong_fix | 2,223,120 | 19,814 | 1133.8 |
| getmoto__moto-9841 | bare | not green | FAIL | ok | right_place_wrong_fix | 77,776 | 16,006 | 150.5 |
| getmoto__moto-9841 | factory | green | PASS | ok | resolved | 1,478,679 | 14,823 | 266.8 |
| harumiweb__exstruct-113 | bare | not green | FAIL | ok | wrong_place | 36,891 | 4,088 | 47.9 |
| harumiweb__exstruct-113 | factory | not green | FAIL | ok | empty_patch | 2,781,766 | 26,497 | 1101.9 |
| hiero-ledger__hiero-sdk-python-1914_interface | bare | not green | FAIL | ok | right_place_wrong_fix | 93,763 | 9,168 | 91.2 |
| hiero-ledger__hiero-sdk-python-1914_interface | factory | green | FAIL | ok | right_place_wrong_fix | 4,581,075 | 49,016 | 1279.4 |
| hkuds__openharness-217 | bare | not green | FAIL | ok | empty_patch | 12,952 | 1,440 | 23.0 |
| hkuds__openharness-217 | factory | green | PASS | ok | resolved | 568,686 | 7,250 | 159.4 |
| idaholab__montepy-933_interface | bare | not green | FAIL | ok | right_place_wrong_fix | 53,160 | 4,412 | 52.2 |
| idaholab__montepy-933_interface | factory | green | PASS | ok | resolved | 4,193,280 | 45,129 | 1417.7 |
| jsonpickle__jsonpickle-588 | bare | not green | FAIL | ok | right_place_wrong_fix | 26,160 | 493 | 22.8 |
| jsonpickle__jsonpickle-588 | factory | green | PASS | ok | resolved | 7,114,363 | 87,747 | 2078.4 |
| keras-team__keras-22316 | bare | not green | FAIL | ok | wrong_place | 38,888 | 6,806 | 68.3 |
| keras-team__keras-22316 | factory | not green | FAIL | ok | empty_patch | 163,402 | 5,772 | 160.1 |
| keras-team__keras-22642 | bare | not green | FAIL | ok | right_place_wrong_fix | 9,212 | 487 | 14.4 |
| keras-team__keras-22642 | factory | green | PASS | ok | resolved | 1,458,781 | 11,189 | 530.0 |
| line__line-bot-sdk-python-981_interface | bare | not green | FAIL | ok | right_place_wrong_fix | 10,737 | 5,843 | 56.9 |
| line__line-bot-sdk-python-981_interface | factory | green | PASS | FAIL | resolved | 5,420,319 | 49,014 | 960.0 |
| pandas-dev__pandas-63945 | bare | not green | FAIL | ok | right_place_wrong_fix | 60,910 | 10,981 | 104.4 |
| pandas-dev__pandas-63945 | factory | not green | FAIL | FAIL | right_place_wrong_fix | 2,652,887 | 32,551 | 1537.2 |
| pyinfra-dev__pyinfra-1665 | bare | not green | FAIL | ok | wrong_place | 26,265 | 1,067 | 19.0 |
| pyinfra-dev__pyinfra-1665 | factory | green | PASS | ok | resolved | 1,220,242 | 8,844 | 296.1 |
| raullenchai__rapid-mlx-289 | bare | not green | FAIL | ok | right_place_wrong_fix | 94,416 | 10,006 | 91.8 |
| raullenchai__rapid-mlx-289 | factory | green | PASS | ok | resolved | 4,389,311 | 48,780 | 1467.4 |
| tox-dev__tox-3931 | bare | not green | FAIL | ok | right_place_wrong_fix | 34,042 | 3,334 | 65.6 |
| tox-dev__tox-3931 | factory | green | PASS | FAIL | resolved | 4,303,677 | 38,143 | 1373.4 |
| ucfopen__canvasapi-716 | bare | not green | FAIL | ok | empty_patch | 1,221 | 376 | 6.7 |
| ucfopen__canvasapi-716 | factory | green | FAIL | ok | right_place_wrong_fix | 996,540 | 9,031 | 273.7 |
| vyperlang__vyper-4801 | bare | not green | FAIL | ok | empty_patch | 23,685 | 8,489 | 94.3 |
| vyperlang__vyper-4801 | factory | green | PASS | ok | resolved | 4,735,865 | 39,474 | 1246.8 |
| zauberzeug__nicegui-5858 | bare | not green | FAIL | ok | right_place_wrong_fix | 7,547 | 1,586 | 19.9 |
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

## factory

- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **15 audited-valid** of 19 gradable (audit failed: 4, not audited: 0, run failed: 0)
- resolve rate: **9/15 = 60% audited-valid**; **2 oracle-pass EXCLUDED** (line__line-bot-sdk-python-981_interface: audit failed, tox-dev__tox-3931: audit failed)
- chain-verdict precision (oracle passes | chain said green): **9/13 = 69%**
- chain-verdict recall (chain said green | oracle passes): **9/9 = 100%**

> **n=19 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on.

> A factory number without the matched **bare-model** number beside it measures the MODEL, not the harness. See `PLAN.md` 1.4.
