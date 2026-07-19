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
| factory/chain/auto\_merge.py                           |      216 |       48 |     78% |253, 518, 543-581, 604, 685-686, 705-709, 730-738, 756-760, 789-836, 850-851, 870-871 |
| factory/chain/branch.py                                |       56 |        4 |     93% |   163-166 |
| factory/chain/bug\_hunter.py                           |        8 |        8 |      0% |     13-62 |
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
| factory/chain/handlers.py                              |     1029 |      212 |     79% |161, 186-188, 294-308, 315-316, 343-354, 376-377, 386-398, 479-480, 484-485, 624-627, 629-632, 636-637, 679, 852, 873-875, 889-890, 989-995, 1129, 1151, 1158, 1166-1167, 1169-1172, 1231-1232, 1242-1249, 1251-1259, 1442-1444, 1481-1483, 1510, 1540, 1556-1559, 1592-1593, 1601, 1607, 1617, 1657-1658, 1764, 1768-1769, 1821, 1834-1835, 1837-1848, 1888-1889, 1891, 1901-1902, 1913-1914, 1916, 1924, 1926, 1989-1990, 2100-2101, 2107-2113, 2153-2154, 2168, 2219, 2253-2257, 2279-2282, 2383-2384, 2667-2671, 2744-2745, 2777-2781, 2801-2805, 2834-2869, 2892-3051, 3149-3150, 3272-3278 |
| factory/chain/idle.py                                  |      128 |       28 |     78% |61-63, 84-85, 96-110, 130-131, 153, 178, 181, 205-217, 235 |
| factory/chain/issue\_intake.py                         |       46 |        5 |     89% |55, 89-90, 92-93 |
| factory/chain/orchestrator.py                          |      383 |       56 |     85% |170, 185-189, 328, 506-507, 747-750, 763, 770-775, 795-796, 811-813, 821-823, 841-846, 861-862, 883-888, 898-899, 934-941, 961-962, 993, 1032-1042, 1087-1088, 1153-1154, 1186-1190, 1193-1195, 1215-1216 |
| factory/chain/pm\_sync.py                              |      254 |       42 |     83% |152-153, 155-156, 158-160, 178, 187, 416, 448, 489-493, 497, 520, 553-566, 592, 597-598, 622, 629, 639-641, 664-665, 676, 688-690, 762-767, 777-778, 788 |
| factory/chain/review\_events.py                        |       11 |        0 |    100% |           |
| factory/chain/rollback.py                              |      106 |        3 |     97% |102-103, 105 |
| factory/chain/scheduled\_tasks.py                      |      196 |       45 |     77% |231, 240-243, 344, 374-375, 407, 565-569, 584, 589, 598-600, 655-668, 689-720 |
| factory/chain/security.py                              |        7 |        7 |      0% |     11-46 |
| factory/chain/slop\_detector.py                        |      257 |       38 |     85% |109-112, 135, 137, 156, 160, 164, 179, 185, 195, 202, 236-237, 258-259, 289, 296, 300, 331-346, 361, 368, 370, 433, 491, 499-500, 503 |
| factory/chain/state\_machine.py                        |      109 |        0 |    100% |           |
| factory/chain/ux\_auditor.py                           |        7 |        7 |      0% |     14-49 |
| factory/chain/worktree.py                              |      112 |       29 |     74% |134-135, 140, 153-156, 169, 172-174, 190-191, 232, 235-241, 262, 279-280, 303, 307, 316-317, 325, 327-328 |
| factory/cli.py                                         |     1261 |      707 |     44% |45-46, 61, 88-140, 160-171, 185-201, 209-215, 224-245, 262-295, 304-339, 348-360, 387-390, 414-419, 441-489, 493-494, 499, 515-536, 553, 562-564, 576-594, 619-641, 658-697, 705-720, 744, 816, 829-830, 839, 845, 875-876, 878, 893-894, 896-897, 899, 924-932, 934, 952-953, 956-958, 960, 978-979, 981, 993-1031, 1060-1084, 1120-1121, 1219-1220, 1276-1280, 1320-1360, 1366-1371, 1395-1412, 1432-1506, 1510-1545, 1564-1574, 1596-1607, 1620-1652, 1664-1701, 1734, 1738-1746, 1864-1920, 1933-1960, 1978-1981, 1998, 2001, 2068-2123, 2163, 2197-2198, 2228-2234, 2290-2292, 2307-2330, 2353, 2356-2360, 2381-2388, 2392-2394, 2403-2404, 2410-2411, 2415, 2418-2419, 2424-2426, 2432-2433, 2543-2556, 2596-2610, 2654-2672, 2727-2752, 2771-2787, 2801-2819, 2841-2857, 2870-2894, 2934-2995 |
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
| factory/directions/parser.py                           |      242 |       26 |     89% |58, 127, 148, 158-159, 168-171, 173, 201-203, 258, 264-265, 269, 291, 297, 307, 333, 346, 358, 383, 396-398 |
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
| factory/providers/azure\_foundry.py                    |       33 |        0 |    100% |           |
| factory/providers/github.py                            |       23 |        5 |     78% |     76-81 |
| factory/runner.py                                      |      639 |      111 |     83% |132-133, 281-282, 308-309, 320, 362, 396-397, 399-404, 423-424, 427-433, 494-495, 534-535, 551, 554, 556, 561-562, 570-585, 593, 596-602, 611-621, 626, 629, 668, 683, 720-721, 726-738, 806, 808-812, 1093, 1095, 1137-1158, 1202-1207, 1228, 1322-1373, 1497, 1522-1523, 1531-1535, 1603, 1616-1617, 1620-1621 |
| factory/scheduler/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/scheduler/cron.py                              |      132 |       11 |     92% |117, 122, 124, 171-175, 211, 353-354 |
| factory/settings/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/settings/enforcer.py                           |       54 |        0 |    100% |           |
| factory/settings/loader.py                             |       83 |        0 |    100% |           |
| factory/settings/modes.py                              |       40 |        1 |     98% |        67 |
| factory/settings/spend.py                              |       83 |       25 |     70% |56-57, 78-79, 81, 93, 120-133, 152-158 |
| factory/tui/\_\_init\_\_.py                            |        2 |        0 |    100% |           |
| factory/tui/app.py                                     |      183 |      151 |     17% |48-57, 61, 66-74, 78, 87-121, 130-161, 166-232, 241-250, 254-274, 278-312, 316-339, 372-377, 380-388, 391-406, 409-415, 418-442, 454-461 |
| factory/webhook/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/webhook/github.py                              |      190 |       40 |     79% |56, 60, 63-64, 96, 126, 162-167, 191-207, 253, 308-312, 355-356, 379-391, 395 |
| factory/webhook/openhands\_events.py                   |       36 |        7 |     81% |69, 84-123 |
| **TOTAL**                                              | **12343** | **2762** | **78%** |           |


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