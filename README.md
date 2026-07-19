# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/xvanov/software-factory/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                   |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------- | -------: | -------: | ------: | --------: |
| factory/\_\_init\_\_.py                                |        2 |        0 |    100% |           |
| factory/app\_config.py                                 |       63 |        4 |     94% |124, 128, 143, 161 |
| factory/artifacts/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/backpressure/\_\_init\_\_.py                   |        0 |        0 |    100% |           |
| factory/backpressure/parser.py                         |       67 |        5 |     93% |103-104, 128, 132-133 |
| factory/backpressure/validator.py                      |       78 |        3 |     96% | 52-53, 72 |
| factory/chain/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| factory/chain/acceptance.py                            |      142 |       34 |     76% |88-89, 95-98, 128, 130, 136-164, 172-173, 256, 286, 293-294, 307-308, 317-318, 320-321, 324-325 |
| factory/chain/auto\_merge.py                           |      329 |       67 |     80% |264, 480, 514, 517-518, 520, 528, 547-548, 552-553, 571-572, 575, 643-644, 652-653, 714-715, 787, 812-850, 873, 989-990, 1009-1013, 1034-1042, 1060-1064, 1093-1140, 1154-1155, 1174-1175 |
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
| factory/chain/gates/acceptance\_verified.py            |       39 |        2 |     95% |   138-139 |
| factory/chain/gates/canonical\_paths\_only.py          |       10 |        0 |    100% |           |
| factory/chain/gates/docs\_current.py                   |       23 |        3 |     87% | 19, 24-25 |
| factory/chain/gates/evaluator.py                       |       55 |        5 |     91% |128, 158-163 |
| factory/chain/gates/smoke\_green.py                    |       15 |        0 |    100% |           |
| factory/chain/gates/tests\_green.py                    |       22 |        2 |     91% |    56, 77 |
| factory/chain/gates/tests\_meaningful.py               |      100 |       17 |     83% |88, 103, 157, 160-161, 196, 216-217, 221, 240-249, 253 |
| factory/chain/handlers.py                              |     1158 |      204 |     82% |141-142, 171-172, 229, 330-331, 399-413, 420-421, 452-463, 485-486, 495-507, 592-593, 597-598, 737-740, 742-745, 749-750, 792, 946, 1081, 1103-1105, 1119-1120, 1221-1227, 1361, 1383, 1390, 1398-1399, 1401-1404, 1463-1464, 1474-1481, 1483-1491, 1674-1676, 1713-1715, 1742, 1772, 1788-1791, 1824-1825, 1833, 1839, 1849, 1889-1890, 1996, 2000-2001, 2053, 2066-2067, 2069-2080, 2135-2136, 2149-2150, 2152, 2166-2167, 2212-2213, 2215, 2225-2226, 2237-2238, 2250, 2313-2314, 2404-2408, 2498-2504, 2544-2545, 2559, 2610, 2644-2648, 2670-2673, 2774-2775, 3058-3062, 3135-3136, 3168-3172, 3192-3196, 3225-3260, 3289-3290, 3330-3338, 3380-3381, 3434-3435, 3437-3438, 3451-3452, 3456-3475, 3573-3574, 3696-3702 |
| factory/chain/idle.py                                  |      128 |       28 |     78% |61-63, 84-85, 96-110, 130-131, 153, 178, 181, 205-217, 235 |
| factory/chain/issue\_intake.py                         |       46 |        5 |     89% |55, 89-90, 92-93 |
| factory/chain/orchestrator.py                          |      441 |       56 |     87% |257, 272-276, 418, 633-634, 853-856, 869, 876-881, 901-902, 917-919, 927-929, 947-952, 967-968, 993-994, 1004-1005, 1040-1047, 1067-1068, 1099, 1184-1194, 1239-1240, 1329-1330, 1362-1366, 1381-1384, 1387-1389, 1409-1410 |
| factory/chain/pm\_sync.py                              |      254 |       42 |     83% |152-153, 155-156, 158-160, 178, 187, 416, 448, 489-493, 497, 520, 553-566, 592, 597-598, 622, 629, 639-641, 664-665, 676, 688-690, 762-767, 777-778, 788 |
| factory/chain/review\_events.py                        |       11 |        0 |    100% |           |
| factory/chain/rollback.py                              |      106 |        3 |     97% |102-103, 105 |
| factory/chain/scheduled\_tasks.py                      |      196 |       45 |     77% |231, 240-243, 344, 374-375, 407, 565-569, 584, 589, 598-600, 655-668, 689-726 |
| factory/chain/security.py                              |        7 |        7 |      0% |     11-46 |
| factory/chain/slop\_detector.py                        |      257 |       38 |     85% |109-112, 135, 137, 156, 160, 164, 179, 185, 195, 202, 236-237, 258-259, 289, 296, 300, 331-346, 361, 368, 370, 433, 491, 499-500, 503 |
| factory/chain/state\_machine.py                        |      110 |        0 |    100% |           |
| factory/chain/ux\_auditor.py                           |        7 |        7 |      0% |     14-49 |
| factory/chain/worktree.py                              |      112 |       25 |     78% |134-135, 140, 169, 172-174, 190-191, 232, 235-241, 262, 279-280, 303, 307, 316-317, 325, 327-328 |
| factory/cli.py                                         |     1303 |      716 |     45% |45-46, 61, 88-140, 160-171, 185-201, 209-215, 224-245, 262-295, 304-339, 348-360, 387-390, 414-419, 441-489, 493-494, 499, 515-536, 553, 562-564, 573-580, 592-610, 635-657, 675-720, 728-743, 767, 839, 852-853, 862, 868, 898-899, 901, 916-917, 919-920, 922, 947-955, 957, 975-976, 979-981, 983, 1001-1002, 1004, 1016-1054, 1083-1107, 1143-1144, 1242-1243, 1299-1303, 1343-1383, 1389-1394, 1418-1435, 1455-1529, 1533-1568, 1587-1597, 1619-1630, 1751-1783, 1795-1832, 1865, 1869-1877, 1995-2051, 2064-2091, 2109-2112, 2129, 2132, 2199-2254, 2294, 2328-2329, 2359-2365, 2421-2423, 2438-2461, 2484, 2487-2491, 2512-2519, 2523-2525, 2534-2535, 2541-2542, 2546, 2549-2550, 2555-2557, 2563-2564, 2674-2687, 2727-2741, 2785-2803, 2858-2883, 2902-2918, 2932-2950, 2972-2988, 3001-3025, 3065-3126 |
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
| factory/events/\_\_init\_\_.py                         |        1 |        0 |    100% |           |
| factory/events/rotation.py                             |       78 |       16 |     79% |62-63, 67-69, 96-98, 113, 116-117, 123-124, 144, 163-164 |
| factory/manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/manager/apply.py                               |      422 |      117 |     72% |148-150, 164-166, 192-195, 234, 256, 261, 279, 282, 326, 336-337, 344-351, 356, 361, 375, 386-416, 453, 456, 478-480, 505, 518, 523, 527, 561-565, 619-620, 641-645, 655-658, 673-674, 679-681, 705-709, 739, 742-746, 750-754, 772-774, 784-786, 827-829, 834, 838-843, 915-917, 938, 953-954 |
| factory/manager/circuit\_breaker.py                    |      175 |       38 |     78% |126-127, 149, 154-157, 178-180, 195-197, 256-259, 267-272, 348-351, 372-373, 403, 407, 410, 412-413, 430-432, 507-512 |
| factory/manager/detectors/\_\_init\_\_.py              |       15 |        0 |    100% |           |
| factory/manager/detectors/cost\_spike.py               |       50 |        4 |     92% |29, 32-33, 112 |
| factory/manager/detectors/placeholder\_prompts.py      |       32 |        1 |     97% |        66 |
| factory/manager/detectors/retry\_storm.py              |       44 |        3 |     93% | 67, 70-71 |
| factory/manager/detectors/review\_churn.py             |       52 |        5 |     90% |110, 113-114, 120, 123 |
| factory/manager/detectors/runs\_failed\_since.py       |       25 |        3 |     88% | 49, 52-53 |
| factory/manager/detectors/stalled\_stories.py          |      165 |       25 |     85% |50, 53-54, 56, 76, 79-80, 82, 86-87, 107, 110-111, 113, 117-118, 138, 141-142, 145-146, 166-167, 170, 273 |
| factory/manager/detectors/state\_distribution\_skew.py |       41 |        5 |     88% |77, 80-81, 83, 89 |
| factory/manager/detectors/tick\_duration\_outliers.py  |       70 |        8 |     89% |23, 25-26, 87, 90-91, 95, 117 |
| factory/manager/detectors/worktree\_orphans.py         |       38 |        4 |     89% |64-65, 86-87 |
| factory/manager/diagnostician.py                       |      448 |       98 |     78% |234-235, 247-248, 347-348, 355, 362, 401-402, 404, 536-538, 547, 558-559, 564, 569-571, 574, 582, 641-645, 726-727, 741, 782-785, 814-819, 848-849, 852, 869-870, 915-917, 934-935, 997-1002, 1004-1009, 1107-1108, 1120-1121, 1142-1143, 1175-1251 |
| factory/manager/halt.py                                |       99 |       16 |     84% |93-94, 135-136, 219-220, 222, 227-229, 237-242 |
| factory/manager/recovery.py                            |      412 |       62 |     85% |177, 180-181, 183, 223-227, 240, 243, 245, 281, 290-291, 348, 359-360, 397, 406, 411-412, 466, 479-480, 492, 494, 548-549, 557-558, 597, 603, 626, 633-634, 666, 672, 675-676, 679, 812, 821-822, 829, 838-839, 858, 861-862, 865-866, 882, 903, 905, 935-936, 1006-1007, 1058-1064 |
| factory/manager/self\_context.py                       |      141 |       29 |     79% |43-45, 55-57, 170-171, 189, 200, 203, 206-207, 212-213, 257-258, 292-298, 323, 338-339, 388, 393-400 |
| factory/manager/signals.py                             |       74 |        3 |     96% |102-103, 210 |
| factory/manager/summarizer.py                          |      401 |      100 |     75% |42-44, 55-57, 118, 123, 147, 150-151, 155-156, 180, 183-184, 204, 207-208, 212-213, 215, 219, 221-222, 269, 281, 284-285, 287, 308-309, 549-552, 554, 560-582, 623-625, 645-646, 649-650, 751-753, 758-760, 854-922 |
| factory/manager/watcher.py                             |      367 |      109 |     70% |41-43, 54-56, 107, 110-111, 115-116, 131, 146, 149-150, 152-153, 164, 168, 170-171, 235-246, 379-382, 384, 392-414, 482-483, 490-491, 501-502, 507-508, 515-516, 523-524, 529-530, 539-540, 552-553, 618-619, 622-625, 741-755, 764-770, 787-790, 822, 827, 855-856, 858, 879, 919-932, 943-976 |
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
| factory/runner.py                                      |      662 |      114 |     83% |132-133, 152, 159-160, 331-332, 358-359, 370, 412, 446-447, 449-454, 473-474, 477-483, 544-545, 584-585, 601, 604, 606, 611-612, 620-635, 643, 646-652, 661-671, 676, 679, 718, 733, 770-771, 776-788, 856, 858-862, 1145, 1147, 1191-1214, 1260-1265, 1286, 1385-1440, 1569, 1596-1597, 1605-1609, 1678, 1692-1693, 1696-1697 |
| factory/scheduler/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/scheduler/cron.py                              |      132 |       11 |     92% |117, 122, 124, 171-175, 211, 353-354 |
| factory/settings/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/settings/audit.py                              |      113 |        5 |     96% |108-109, 111, 140-141 |
| factory/settings/enforcer.py                           |       54 |        0 |    100% |           |
| factory/settings/loader.py                             |       88 |        0 |    100% |           |
| factory/settings/modes.py                              |       40 |        1 |     98% |        67 |
| factory/settings/spend.py                              |       83 |       24 |     71% |56-57, 78-79, 93, 120-133, 152-158 |
| factory/tui/\_\_init\_\_.py                            |        2 |        0 |    100% |           |
| factory/tui/app.py                                     |      183 |      151 |     17% |48-57, 61, 66-74, 78, 87-121, 130-161, 166-232, 241-250, 254-274, 278-312, 316-339, 372-377, 380-388, 391-406, 409-415, 418-442, 454-461 |
| factory/webhook/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/webhook/github.py                              |      190 |       40 |     79% |56, 60, 63-64, 96, 126, 162-167, 191-207, 253, 308-312, 355-356, 379-391, 395 |
| factory/webhook/openhands\_events.py                   |       36 |        7 |     81% |69, 84-123 |
| **TOTAL**                                              | **13330** | **2860** | **79%** |           |


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