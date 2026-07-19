# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/xvanov/software-factory/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                   |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------- | -------: | -------: | ------: | --------: |
| factory/\_\_init\_\_.py                                |        2 |        0 |    100% |           |
| factory/app\_config.py                                 |       61 |        4 |     93% |107, 111, 126, 144 |
| factory/artifacts/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/backpressure/\_\_init\_\_.py                   |        0 |        0 |    100% |           |
| factory/backpressure/parser.py                         |       67 |        5 |     93% |103-104, 128, 132-133 |
| factory/backpressure/validator.py                      |       78 |        3 |     96% | 52-53, 72 |
| factory/chain/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| factory/chain/auto\_merge.py                           |      329 |       67 |     80% |262, 478, 512, 515-516, 518, 526, 545-546, 550-551, 569-570, 573, 641-642, 650-651, 712-713, 785, 810-848, 871, 986-987, 1006-1010, 1031-1039, 1057-1061, 1090-1137, 1151-1152, 1171-1172 |
| factory/chain/branch.py                                |       56 |        4 |     93% |   163-166 |
| factory/chain/bug\_hunter.py                           |        8 |        8 |      0% |     13-62 |
| factory/chain/ci\_health.py                            |      197 |       28 |     86% |113-114, 131, 134, 178, 181, 201, 210, 217, 251, 264, 326, 330, 339, 343-344, 421-422, 430-431, 449-450, 468-469, 494-495, 505-506 |
| factory/chain/context\_refresh.py                      |      179 |       40 |     78% |123-130, 211, 222-248, 277-290, 360-369, 411, 442, 477, 524-526, 541-543, 545-548, 553-556, 564-565, 567, 571-572 |
| factory/chain/dual\_draft.py                           |      123 |       10 |     92% |63-64, 196, 227, 229, 233, 334, 364, 384-385 |
| factory/chain/event\_log.py                            |       55 |        3 |     95% |122, 132-133 |
| factory/chain/factory\_improver.py                     |      274 |       92 |     66% |142, 159-160, 162, 167-168, 184-221, 254-255, 262-263, 330, 373-395, 409-410, 435-436, 513-514, 535, 561, 629-667, 684-686, 700-712, 739-782 |
| factory/chain/factory\_improver\_apply.py              |      327 |       41 |     87% |120, 124, 153-154, 233, 246, 314, 379-380, 428-429, 439, 468-469, 516, 523-524, 547-548, 570, 607, 663-664, 692, 752, 785-794, 832-833, 836, 846-855, 869, 907-911 |
| factory/chain/factory\_status.py                       |      144 |        8 |     94% |81-82, 114-115, 117, 260, 282-284 |
| factory/chain/gates/\_\_init\_\_.py                    |        3 |        0 |    100% |           |
| factory/chain/gates/canonical\_paths\_only.py          |       10 |        0 |    100% |           |
| factory/chain/gates/coverage\_verified.py              |       19 |        4 |     79% |     51-55 |
| factory/chain/gates/docs\_current.py                   |       23 |        3 |     87% | 19, 24-25 |
| factory/chain/gates/evaluator.py                       |       52 |        5 |     90% |103, 133-138 |
| factory/chain/gates/flow\_verified.py                  |       57 |        6 |     89% |56, 63-64, 94, 101, 113 |
| factory/chain/gates/format\_clean.py                   |       19 |        5 |     74% | 28, 40-43 |
| factory/chain/gates/lint\_clean.py                     |       19 |        3 |     84% | 30, 44-45 |
| factory/chain/gates/smoke\_green.py                    |       15 |        0 |    100% |           |
| factory/chain/gates/tests\_green.py                    |       20 |        3 |     85% | 30, 38-39 |
| factory/chain/gates/tests\_meaningful.py               |       13 |        0 |    100% |           |
| factory/chain/gates/tests\_red\_first\_confirmed.py    |       20 |        2 |     90% |     34-35 |
| factory/chain/gates/types\_clean.py                    |       19 |        5 |     74% | 28, 40-43 |
| factory/chain/handlers.py                              |     1110 |      206 |     81% |141-142, 171-172, 222, 247-249, 355-369, 376-377, 404-415, 437-438, 447-459, 540-541, 545-546, 685-688, 690-693, 697-698, 740, 913, 934-936, 950-951, 1050-1056, 1190, 1212, 1219, 1227-1228, 1230-1233, 1292-1293, 1303-1310, 1312-1320, 1503-1505, 1542-1544, 1571, 1601, 1617-1620, 1653-1654, 1662, 1668, 1678, 1718-1719, 1825, 1829-1830, 1882, 1895-1896, 1898-1909, 1964-1965, 1978-1979, 1981, 1995-1996, 2041-2042, 2044, 2054-2055, 2066-2067, 2079, 2142-2143, 2233-2237, 2323-2324, 2330-2336, 2376-2377, 2391, 2442, 2476-2480, 2502-2505, 2606-2607, 2890-2894, 2967-2968, 3000-3004, 3024-3028, 3057-3092, 3121-3122, 3162-3170, 3212-3213, 3266-3267, 3269-3270, 3283-3284, 3288-3307, 3405-3406, 3528-3534 |
| factory/chain/idle.py                                  |      128 |       28 |     78% |61-63, 84-85, 96-110, 130-131, 153, 178, 181, 205-217, 235 |
| factory/chain/issue\_intake.py                         |       46 |        5 |     89% |55, 89-90, 92-93 |
| factory/chain/orchestrator.py                          |      395 |       58 |     85% |174, 189-193, 332, 547-548, 767-770, 783, 790-795, 815-816, 831-833, 841-843, 861-866, 881-882, 903-908, 918-919, 954-961, 981-982, 1013, 1052-1062, 1107-1108, 1173-1174, 1206-1210, 1225-1228, 1231-1233, 1253-1254 |
| factory/chain/pm\_sync.py                              |      254 |       42 |     83% |152-153, 155-156, 158-160, 178, 187, 416, 448, 489-493, 497, 520, 553-566, 592, 597-598, 622, 629, 639-641, 664-665, 676, 688-690, 762-767, 777-778, 788 |
| factory/chain/review\_events.py                        |       11 |        0 |    100% |           |
| factory/chain/rollback.py                              |      106 |        3 |     97% |102-103, 105 |
| factory/chain/scheduled\_tasks.py                      |      196 |       45 |     77% |231, 240-243, 344, 374-375, 407, 565-569, 584, 589, 598-600, 655-668, 689-726 |
| factory/chain/security.py                              |        7 |        7 |      0% |     11-46 |
| factory/chain/slop\_detector.py                        |      257 |       38 |     85% |109-112, 135, 137, 156, 160, 164, 179, 185, 195, 202, 236-237, 258-259, 289, 296, 300, 331-346, 361, 368, 370, 433, 491, 499-500, 503 |
| factory/chain/state\_machine.py                        |      109 |        0 |    100% |           |
| factory/chain/ux\_auditor.py                           |        7 |        7 |      0% |     14-49 |
| factory/chain/worktree.py                              |      112 |       25 |     78% |134-135, 140, 169, 172-174, 190-191, 232, 235-241, 262, 279-280, 303, 307, 316-317, 325, 327-328 |
| factory/cli.py                                         |     1295 |      709 |     45% |45-46, 61, 88-140, 160-171, 185-201, 209-215, 224-245, 262-295, 304-339, 348-360, 387-390, 414-419, 441-489, 493-494, 499, 515-536, 553, 562-564, 576-594, 619-641, 659-704, 712-727, 751, 823, 836-837, 846, 852, 882-883, 885, 900-901, 903-904, 906, 931-939, 941, 959-960, 963-965, 967, 985-986, 988, 1000-1038, 1067-1091, 1127-1128, 1226-1227, 1283-1287, 1327-1367, 1373-1378, 1402-1419, 1439-1513, 1517-1552, 1571-1581, 1603-1614, 1735-1767, 1779-1816, 1849, 1853-1861, 1979-2035, 2048-2075, 2093-2096, 2113, 2116, 2183-2238, 2278, 2312-2313, 2343-2349, 2405-2407, 2422-2445, 2468, 2471-2475, 2496-2503, 2507-2509, 2518-2519, 2525-2526, 2530, 2533-2534, 2539-2541, 2547-2548, 2658-2671, 2711-2725, 2769-2787, 2842-2867, 2886-2902, 2916-2934, 2956-2972, 2985-3009, 3049-3110 |
| factory/context/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/context/canonical\_paths.py                    |       36 |        2 |     94% |     90-91 |
| factory/context/enforcer.py                            |       49 |        0 |    100% |           |
| factory/context/loader.py                              |       66 |        8 |     88% |96-110, 132 |
| factory/context/navigator.py                           |       39 |        2 |     95% |     65-66 |
| factory/context/updater.py                             |       29 |        1 |     97% |        77 |
| factory/deploy/\_\_init\_\_.py                         |        4 |        0 |    100% |           |
| factory/deploy/models.py                               |       28 |        0 |    100% |           |
| factory/deploy/orchestrator.py                         |      282 |       34 |     88% |255, 257-260, 263-265, 314, 400-403, 429-439, 484-488, 520-524, 543-544, 549, 566, 577, 584, 692-693 |
| factory/deploy/runner.py                               |       56 |        0 |    100% |           |
| factory/directions/\_\_init\_\_.py                     |        0 |        0 |    100% |           |
| factory/directions/creator.py                          |      150 |       69 |     54% |126, 156, 163, 197, 214-222, 232-343 |
| factory/directions/gc.py                               |       72 |       10 |     86% |59, 63, 76, 79-80, 82, 136-137, 162-163 |
| factory/directions/ingester.py                         |       77 |        2 |     97% |   55, 131 |
| factory/directions/parser.py                           |      242 |       25 |     90% |58, 148, 158-159, 168-171, 173, 201-203, 258, 264-265, 269, 291, 297, 307, 333, 346, 358, 383, 396-398 |
| factory/directions/tracker\_issue.py                   |      151 |       17 |     89% |70-72, 110, 116, 120, 195-199, 256, 262, 270, 275, 281-282 |
| factory/directions/watcher.py                          |       76 |       25 |     67% |77-81, 86, 110-114, 122-132, 137-142 |
| factory/manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/manager/apply.py                               |      422 |      117 |     72% |148-150, 164-166, 192-195, 234, 256, 261, 279, 282, 326, 336-337, 344-351, 356, 361, 375, 386-416, 453, 456, 478-480, 505, 518, 523, 527, 561-565, 619-620, 641-645, 655-658, 673-674, 679-681, 705-709, 739, 742-746, 750-754, 772-774, 784-786, 827-829, 834, 838-843, 915-917, 938, 953-954 |
| factory/manager/circuit\_breaker.py                    |      175 |       38 |     78% |126-127, 149, 154-157, 178-180, 195-197, 256-259, 267-272, 348-351, 372-373, 403, 407, 410, 412-413, 430-432, 507-512 |
| factory/manager/detectors/\_\_init\_\_.py              |       15 |        0 |    100% |           |
| factory/manager/detectors/cost\_spike.py               |       50 |        4 |     92% |29, 32-33, 112 |
| factory/manager/detectors/placeholder\_prompts.py      |       32 |        1 |     97% |        66 |
| factory/manager/detectors/retry\_storm.py              |       44 |        3 |     93% | 67, 70-71 |
| factory/manager/detectors/review\_churn.py             |       52 |        5 |     90% |110, 113-114, 120, 123 |
| factory/manager/detectors/runs\_failed\_since.py       |       25 |        3 |     88% | 49, 52-53 |
| factory/manager/detectors/stalled\_stories.py          |      139 |       19 |     86% |50, 53-54, 56, 76, 79-80, 82, 86-87, 107, 110-111, 114-115, 135-136, 139, 237 |
| factory/manager/detectors/state\_distribution\_skew.py |       41 |        5 |     88% |77, 80-81, 83, 89 |
| factory/manager/detectors/tick\_duration\_outliers.py  |       70 |        8 |     89% |23, 25-26, 87, 90-91, 95, 117 |
| factory/manager/detectors/worktree\_orphans.py         |       38 |        4 |     89% |64-65, 86-87 |
| factory/manager/diagnostician.py                       |      448 |       98 |     78% |234-235, 247-248, 347-348, 355, 362, 401-402, 404, 536-538, 547, 558-559, 564, 569-571, 574, 582, 641-645, 726-727, 741, 782-785, 814-819, 848-849, 852, 869-870, 915-917, 934-935, 997-1002, 1004-1009, 1107-1108, 1120-1121, 1142-1143, 1175-1251 |
| factory/manager/halt.py                                |       99 |       16 |     84% |93-94, 135-136, 219-220, 222, 227-229, 237-242 |
| factory/manager/recovery.py                            |      412 |       62 |     85% |177, 180-181, 183, 223-227, 240, 243, 245, 281, 290-291, 348, 359-360, 397, 406, 411-412, 466, 479-480, 492, 494, 548-549, 557-558, 597, 603, 626, 633-634, 666, 672, 675-676, 679, 812, 821-822, 829, 838-839, 858, 861-862, 865-866, 882, 903, 905, 935-936, 1006-1007, 1058-1064 |
| factory/manager/self\_context.py                       |      141 |       29 |     79% |43-45, 55-57, 170-171, 189, 200, 203, 206-207, 212-213, 257-258, 292-298, 323, 338-339, 388, 393-400 |
| factory/manager/signals.py                             |       69 |        1 |     99% |       201 |
| factory/manager/summarizer.py                          |      349 |      113 |     68% |41-43, 54-56, 102, 107, 131, 134-135, 139-140, 156, 159-160, 162-163, 176-200, 214-215, 455-458, 460, 466-488, 529-531, 548-549, 612, 643, 650-652, 657-659, 728-796 |
| factory/manager/watcher.py                             |      346 |       99 |     71% |41-43, 54-56, 107, 110-111, 115-116, 131, 146, 149-150, 152-153, 164, 168, 170-171, 358-361, 363, 371-393, 461-462, 469-470, 480-481, 486-487, 494-495, 502-503, 508-509, 518-519, 531-532, 594-597, 713-727, 736-742, 759-762, 794, 822, 862-875, 886-919 |
| factory/model\_router.py                               |      122 |        9 |     93% |53, 55, 67, 89, 100, 189-192 |
| factory/observability/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| factory/observability/estimator.py                     |      185 |       31 |     83% |170-185, 219, 242-244, 331, 333, 337, 384, 417, 450, 470, 489, 491, 493, 498 |
| factory/observability/heartbeat.py                     |       60 |        7 |     88% |69, 74-77, 129-130 |
| factory/observability/queries.py                       |      321 |       62 |     81% |150-151, 153, 197-200, 253-258, 265, 317-318, 332, 360-361, 455, 457-481, 529-532, 538, 586-589, 635-644, 647-653 |
| factory/observability/schema.py                        |       48 |        0 |    100% |           |
| factory/personas/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/providers/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/providers/azure\_foundry.py                    |       34 |        0 |    100% |           |
| factory/providers/github.py                            |       23 |        5 |     78% |     76-81 |
| factory/runner.py                                      |      660 |      114 |     83% |132-133, 152, 159-160, 331-332, 358-359, 370, 412, 446-447, 449-454, 473-474, 477-483, 544-545, 584-585, 601, 604, 606, 611-612, 620-635, 643, 646-652, 661-671, 676, 679, 718, 733, 770-771, 776-788, 856, 858-862, 1143, 1145, 1189-1212, 1258-1263, 1284, 1383-1438, 1567, 1594-1595, 1603-1607, 1676, 1690-1691, 1694-1695 |
| factory/scheduler/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/scheduler/cron.py                              |      132 |       11 |     92% |117, 122, 124, 171-175, 211, 353-354 |
| factory/settings/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/settings/audit.py                              |      113 |        5 |     96% |108-109, 111, 140-141 |
| factory/settings/enforcer.py                           |       54 |        0 |    100% |           |
| factory/settings/loader.py                             |       86 |        0 |    100% |           |
| factory/settings/modes.py                              |       40 |        1 |     98% |        67 |
| factory/settings/spend.py                              |       83 |       25 |     70% |56-57, 78-79, 81, 93, 120-133, 152-158 |
| factory/tui/\_\_init\_\_.py                            |        2 |        0 |    100% |           |
| factory/tui/app.py                                     |      183 |      151 |     17% |48-57, 61, 66-74, 78, 87-121, 130-161, 166-232, 241-250, 254-274, 278-312, 316-339, 372-377, 380-388, 391-406, 409-415, 418-442, 454-461 |
| factory/webhook/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/webhook/github.py                              |      190 |       40 |     79% |56, 60, 63-64, 96, 126, 162-167, 191-207, 253, 308-312, 355-356, 379-391, 395 |
| factory/webhook/openhands\_events.py                   |       36 |        7 |     81% |69, 84-123 |
| **TOTAL**                                              | **12918** | **2810** | **78%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/xvanov/software-factory/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/xvanov/software-factory/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/xvanov/software-factory/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/xvanov/software-factory/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fxvanov%2Fsoftware-factory%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/xvanov/software-factory/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.