# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/xvanov/software-factory/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                   |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------- | -------: | -------: | ------: | --------: |
| factory/\_\_init\_\_.py                                |        2 |        0 |    100% |           |
| factory/app\_config.py                                 |       79 |        5 |     94% |168, 172, 187, 205, 221 |
| factory/artifacts/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/backpressure/\_\_init\_\_.py                   |        0 |        0 |    100% |           |
| factory/backpressure/parser.py                         |       67 |        5 |     93% |103-104, 128, 132-133 |
| factory/backpressure/validator.py                      |       78 |        3 |     96% | 52-53, 72 |
| factory/chain/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| factory/chain/acceptance.py                            |      166 |       35 |     79% |88-89, 95-98, 148, 189, 191, 200-228, 236-237, 320, 350, 357-358, 371-372, 381-382, 384-385, 388-389 |
| factory/chain/auto\_merge.py                           |      653 |      107 |     84% |294-295, 342, 344, 346, 350-351, 510-511, 513, 550, 567, 663-664, 752, 853-854, 1144-1145, 1155, 1173-1174, 1176, 1179-1180, 1188, 1219-1220, 1222, 1247, 1249, 1258-1259, 1270-1271, 1294, 1336, 1339-1340, 1342, 1350, 1379-1380, 1384-1385, 1405-1406, 1409, 1481, 1495-1496, 1539-1540, 1548-1549, 1558-1559, 1568-1569, 1641-1642, 1712, 1866, 1885-1886, 1961-1962, 2016, 2041-2093, 2116, 2247-2248, 2271-2272, 2291-2295, 2316-2324, 2342-2346, 2397-2398, 2434-2437, 2461-2462, 2484-2485, 2496-2497, 2536-2537 |
| factory/chain/branch.py                                |       56 |        4 |     93% |   163-166 |
| factory/chain/bug\_hunter.py                           |        8 |        8 |      0% |     13-62 |
| factory/chain/ci\_health.py                            |      197 |       28 |     86% |113-114, 131, 134, 178, 181, 201, 210, 217, 251, 264, 326, 330, 339, 343-344, 421-422, 430-431, 449-450, 468-469, 494-495, 505-506 |
| factory/chain/context\_refresh.py                      |      179 |       40 |     78% |123-130, 211, 222-248, 277-290, 360-369, 411, 442, 477, 524-526, 541-543, 545-548, 553-556, 564-565, 567, 571-572 |
| factory/chain/dual\_draft.py                           |      150 |       15 |     90% |64-65, 197, 228, 230, 234, 383, 401-402, 444-445, 476-477, 479-480 |
| factory/chain/ears.py                                  |       71 |        0 |    100% |           |
| factory/chain/event\_log.py                            |       55 |        3 |     95% |122, 132-133 |
| factory/chain/factory\_improver.py                     |      274 |       92 |     66% |142, 159-160, 162, 167-168, 184-223, 256-257, 264-265, 332, 375-397, 411-412, 437-438, 515-516, 537, 563, 631-669, 686-688, 702-714, 741-784 |
| factory/chain/factory\_improver\_apply.py              |      355 |       39 |     89% |120, 204, 240, 253, 321, 386-387, 458-459, 469, 498-499, 546, 553-554, 577-578, 600, 637, 693-694, 722, 782, 815-824, 921-922, 925, 935-944, 958, 1031-1035 |
| factory/chain/factory\_status.py                       |      144 |        8 |     94% |85-86, 118-119, 121, 264, 286-288 |
| factory/chain/gates/\_\_init\_\_.py                    |        3 |        0 |    100% |           |
| factory/chain/gates/acceptance\_verified.py            |       39 |        2 |     95% |   138-139 |
| factory/chain/gates/canonical\_paths\_only.py          |       10 |        0 |    100% |           |
| factory/chain/gates/docs\_current.py                   |       23 |        3 |     87% | 19, 24-25 |
| factory/chain/gates/evaluator.py                       |       55 |        5 |     91% |128, 158-163 |
| factory/chain/gates/smoke\_green.py                    |       15 |        0 |    100% |           |
| factory/chain/gates/tests\_green.py                    |       38 |       10 |     74% |47-63, 122, 143 |
| factory/chain/gates/tests\_meaningful.py               |      100 |       17 |     83% |88, 103, 157, 160-161, 196, 216-217, 221, 240-249, 253 |
| factory/chain/handlers.py                              |     1373 |      246 |     82% |151-152, 186-187, 354-366, 444-458, 465-466, 492-493, 505-516, 538-539, 546-558, 577-578, 650-651, 655-656, 793-796, 798-801, 805-806, 848, 1001, 1135, 1157-1159, 1173-1174, 1253, 1333-1339, 1375-1376, 1407-1408, 1412-1414, 1578, 1600, 1607, 1615-1616, 1618-1621, 1681-1682, 1692-1699, 1701-1709, 1887-1889, 1942-1944, 1969-1970, 1997, 2027, 2043-2046, 2090-2091, 2099, 2105, 2157-2158, 2262, 2266-2267, 2315, 2328-2329, 2331-2342, 2397-2398, 2411-2412, 2414, 2428-2429, 2474-2475, 2477, 2487-2488, 2499-2500, 2512, 2537-2557, 2619-2620, 2710-2714, 2798-2804, 2844-2845, 2856, 2907, 2937-2941, 2959-2962, 3059-3060, 3343-3347, 3441-3442, 3488-3492, 3510-3512, 3541-3574, 3624-3625, 3658-3659, 3664, 3697-3698, 3735-3736, 3853-3854, 3860, 3880, 3883-3884, 3889, 3945-3946, 3986-3994, 4046-4047, 4115-4116, 4118-4119, 4132-4133, 4137-4156, 4254-4255, 4381-4389 |
| factory/chain/idle.py                                  |      209 |       39 |     81% |91-92, 148-150, 158, 169, 172-173, 184-185, 248-250, 271-272, 283-297, 317-318, 340, 365, 368, 392-404, 422 |
| factory/chain/issue\_intake.py                         |       46 |        5 |     89% |55, 89-90, 92-93 |
| factory/chain/orchestrator.py                          |      820 |      170 |     79% |342, 357-361, 524, 798-799, 974-1003, 1014-1039, 1117, 1124, 1168-1196, 1231-1232, 1248-1249, 1296, 1304-1305, 1317-1318, 1327, 1333-1334, 1379-1381, 1386, 1456-1457, 1488, 1537-1547, 1632, 1654, 1705-1706, 1712-1713, 1748-1749, 1754-1755, 1813-1814, 1823-1824, 1875-1878, 1891, 1898-1919, 1939-1940, 1962-1964, 1976-1978, 1990-1992, 2017-2024, 2029-2031, 2039-2041, 2057-2062, 2077-2078, 2100-2104, 2114-2115, 2150-2157, 2177-2178, 2332-2342, 2387-2388, 2518-2519, 2551-2555, 2570-2573, 2593-2603, 2606-2608, 2629-2630 |
| factory/chain/pm\_sync.py                              |      249 |       40 |     84% |161-162, 164-165, 167-169, 187, 196, 425, 457, 498-502, 506, 545, 561-573, 589-599, 615, 622, 632-634, 657-658, 669, 681-683, 757-758, 760, 770-771, 781 |
| factory/chain/review\_events.py                        |       11 |        0 |    100% |           |
| factory/chain/rollback.py                              |      106 |        3 |     97% |102-103, 105 |
| factory/chain/scheduled\_tasks.py                      |      281 |       34 |     88% |231, 240-243, 344, 374-375, 407, 608-610, 625, 630, 639-641, 708-709, 732, 736, 739, 744-745, 797, 807, 810-811, 868-874 |
| factory/chain/security.py                              |        7 |        7 |      0% |     11-46 |
| factory/chain/slop\_detector.py                        |      257 |       38 |     85% |109-112, 135, 137, 156, 160, 164, 179, 185, 195, 202, 236-237, 258-259, 289, 296, 300, 331-346, 361, 368, 370, 433, 491, 499-500, 503 |
| factory/chain/state\_machine.py                        |      117 |        0 |    100% |           |
| factory/chain/step\_events.py                          |       59 |        9 |     85% |111-112, 127-128, 157, 160-161, 168-169 |
| factory/chain/ux\_auditor.py                           |        7 |        7 |      0% |     14-49 |
| factory/chain/worktree.py                              |      112 |       25 |     78% |134-135, 140, 169, 172-174, 190-191, 232, 235-241, 262, 279-280, 303, 307, 316-317, 325, 327-328 |
| factory/cli.py                                         |     1439 |      790 |     45% |45-46, 61, 88-140, 160-171, 185-201, 209-215, 224-245, 262-295, 304-339, 356-395, 404-416, 443-446, 470-476, 498-546, 550-551, 556, 580-615, 622-645, 662, 671-673, 682-689, 714-736, 760, 762, 764-769, 771-783, 785, 793, 822-837, 861, 935, 946, 959-960, 969, 975, 1005-1006, 1008, 1023-1024, 1026-1027, 1029, 1054-1062, 1064, 1082-1083, 1086-1088, 1090, 1108-1109, 1111, 1123-1163, 1192-1214, 1231-1240, 1271-1295, 1310-1328, 1336-1351, 1378-1379, 1477-1478, 1534-1538, 1578-1618, 1624-1629, 1653-1670, 1690-1766, 1770-1805, 1824-1834, 1856-1867, 1988-2020, 2032-2069, 2102, 2106-2114, 2232-2288, 2301-2328, 2346-2349, 2366, 2369, 2436-2491, 2531, 2565-2566, 2596-2602, 2658-2660, 2675-2698, 2721, 2724-2728, 2749-2756, 2760-2762, 2771-2772, 2778-2779, 2783, 2786-2787, 2792-2794, 2800-2801, 2925-2939, 2979-2994, 3040-3059, 3114-3139, 3158-3174, 3188-3208, 3230-3248, 3261-3287, 3327-3385, 3414-3415 |
| factory/context/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/context/canonical\_paths.py                    |       36 |        2 |     94% |     90-91 |
| factory/context/enforcer.py                            |       49 |        0 |    100% |           |
| factory/context/loader.py                              |       66 |        8 |     88% |96-110, 132 |
| factory/context/navigator.py                           |       39 |        2 |     95% |     65-66 |
| factory/context/updater.py                             |       29 |        1 |     97% |        77 |
| factory/deploy/\_\_init\_\_.py                         |        4 |        0 |    100% |           |
| factory/deploy/models.py                               |       28 |        0 |    100% |           |
| factory/deploy/orchestrator.py                         |      284 |       34 |     88% |257, 259-262, 265-267, 316, 402-405, 431-441, 486-490, 532-536, 555-556, 561, 578, 589, 596, 704-705 |
| factory/deploy/runner.py                               |       56 |        0 |    100% |           |
| factory/directions/\_\_init\_\_.py                     |        0 |        0 |    100% |           |
| factory/directions/creator.py                          |      150 |       69 |     54% |126, 156, 163, 197, 214-222, 232-343 |
| factory/directions/gc.py                               |       73 |       10 |     86% |59, 63, 76, 79-80, 82, 136-137, 165-166 |
| factory/directions/ingester.py                         |       77 |        2 |     97% |   55, 131 |
| factory/directions/parser.py                           |      242 |       21 |     91% |58, 148, 158-159, 173, 201-203, 258, 264-265, 269, 291, 297, 307, 333, 346, 358, 383, 396-398 |
| factory/directions/tracker\_issue.py                   |      226 |       23 |     90% |70-72, 110, 116, 120, 195-199, 325, 329, 346, 353-354, 420-422, 446-447, 450, 487 |
| factory/directions/watcher.py                          |       76 |       25 |     67% |77-81, 86, 110-114, 122-132, 137-142 |
| factory/events/\_\_init\_\_.py                         |        1 |        0 |    100% |           |
| factory/events/rotation.py                             |       78 |       16 |     79% |62-63, 67-69, 96-98, 113, 116-117, 123-124, 144, 163-164 |
| factory/git\_state.py                                  |       41 |        2 |     95% |    47, 60 |
| factory/manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/manager/apply.py                               |      464 |      167 |     64% |177-179, 193-195, 246-249, 288, 337, 342, 360, 363, 405-444, 456, 467-497, 506-563, 586, 599, 608, 658-665, 733-734, 755-761, 815-819, 883-884, 888-889, 894-896, 954, 957-961, 965-969, 987-989, 999-1001, 1042-1044, 1049, 1053-1058, 1133-1135, 1158, 1168, 1173-1174 |
| factory/manager/circuit\_breaker.py                    |      187 |       36 |     81% |126-127, 149, 154-157, 178-180, 195-197, 256-259, 267-272, 348-351, 372-376, 430-433, 437, 440, 467-468, 562-567 |
| factory/manager/detectors/\_\_init\_\_.py              |       16 |        0 |    100% |           |
| factory/manager/detectors/cost\_spike.py               |       50 |        4 |     92% |29, 32-33, 112 |
| factory/manager/detectors/fms\_yield.py                |       63 |        6 |     90% |84, 87-88, 90, 94-95 |
| factory/manager/detectors/placeholder\_prompts.py      |       32 |        1 |     97% |        66 |
| factory/manager/detectors/retry\_storm.py              |       44 |        3 |     93% | 67, 70-71 |
| factory/manager/detectors/review\_churn.py             |       52 |        5 |     90% |110, 113-114, 120, 123 |
| factory/manager/detectors/runs\_failed\_since.py       |       25 |        3 |     88% | 49, 52-53 |
| factory/manager/detectors/stalled\_stories.py          |      165 |       25 |     85% |58, 61-62, 64, 84, 87-88, 90, 94-95, 115, 118-119, 121, 125-126, 146, 149-150, 153-154, 174-175, 178, 281 |
| factory/manager/detectors/state\_distribution\_skew.py |       41 |        5 |     88% |77, 80-81, 83, 89 |
| factory/manager/detectors/tick\_duration\_outliers.py  |       70 |        8 |     89% |23, 25-26, 87, 90-91, 95, 117 |
| factory/manager/detectors/worktree\_orphans.py         |       38 |        4 |     89% |64-65, 86-87 |
| factory/manager/diagnostician.py                       |      466 |      101 |     78% |235-236, 248-249, 348-349, 356, 363, 402-403, 405, 548-550, 559, 570-571, 576, 581-583, 586, 594, 653-657, 738-739, 753, 794-797, 826-831, 880-881, 907-908, 953-955, 974-975, 1037-1042, 1044-1049, 1156-1157, 1169-1170, 1191-1192, 1224-1312 |
| factory/manager/escalation.py                          |      177 |       21 |     88% |126-128, 138-139, 152-153, 167, 289-290, 292, 296, 346, 409-410, 455-456, 493-494, 531-532 |
| factory/manager/halt.py                                |      126 |       24 |     81% |101-102, 180-185, 247, 293-296, 314-315, 317, 322-324, 332-337 |
| factory/manager/poison\_escalation.py                  |      109 |       16 |     85% |93-94, 99, 102-103, 127, 173, 181, 183, 315-324, 345-346, 360-361 |
| factory/manager/recovery.py                            |      467 |       63 |     87% |182, 185-186, 188, 228-232, 245, 248, 250, 295-296, 353, 364-365, 411, 416-417, 471, 484-485, 499, 553-554, 565-566, 614, 631-632, 670, 673-674, 677, 811, 821-822, 829, 838-839, 851, 960-961, 980, 983-984, 987-988, 1004, 1025, 1027, 1057-1058, 1128-1129, 1346-1365 |
| factory/manager/self\_context.py                       |      141 |       29 |     79% |43-45, 55-57, 170-171, 189, 200, 203, 206-207, 212-213, 257-258, 292-298, 323, 338-339, 388, 393-400 |
| factory/manager/signals.py                             |       86 |        3 |     97% |125-126, 301 |
| factory/manager/staging.py                             |      152 |       11 |     93% |206, 307-308, 394, 437, 452, 470, 562-583 |
| factory/manager/summarizer.py                          |      414 |      104 |     75% |42-44, 55-57, 118, 123, 147, 150-151, 155-156, 180, 183-184, 204, 207-208, 212-213, 215, 219, 221-222, 293, 305, 308-309, 311, 332-333, 573-576, 578, 584-606, 647-649, 670-671, 674-675, 776-778, 783-785, 883-963 |
| factory/manager/watcher.py                             |      407 |      123 |     70% |41-43, 54-56, 130, 133-134, 138-139, 189, 204, 207-208, 210-211, 222, 226, 228-229, 293-304, 437-440, 442, 450-472, 540-541, 548-549, 559-560, 565-566, 573-574, 581-582, 587-588, 597-598, 610-611, 676-677, 680-683, 799-826, 835-841, 858-865, 886-889, 908-921, 942, 947, 975-976, 978, 999, 1041-1054, 1065-1098 |
| factory/model\_router.py                               |      122 |        9 |     93% |53, 55, 67, 89, 100, 189-192 |
| factory/observability/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| factory/observability/estimator.py                     |      185 |       31 |     83% |170-185, 219, 242-244, 331, 333, 337, 384, 417, 450, 470, 489, 491, 493, 498 |
| factory/observability/heartbeat.py                     |       60 |        7 |     88% |69, 74-77, 129-130 |
| factory/observability/queries.py                       |      321 |       62 |     81% |150-151, 153, 205-208, 261-266, 273, 325-326, 340, 368-369, 463, 465-489, 537-540, 546, 594-597, 643-652, 655-661 |
| factory/observability/schema.py                        |       48 |        0 |    100% |           |
| factory/personas/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/power.py                                       |      140 |        3 |     98% |83, 94, 168 |
| factory/providers/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/providers/azure\_foundry.py                    |       34 |        0 |    100% |           |
| factory/providers/github.py                            |       23 |        2 |     91% |     79-81 |
| factory/runner.py                                      |      707 |      108 |     85% |132-133, 152, 159-160, 343-344, 370-371, 435, 447, 458, 500, 534-535, 537-542, 561-562, 565-571, 632-633, 672-673, 689, 692, 694, 699-700, 708-723, 731, 734-740, 749-759, 764, 767, 806, 821, 858-859, 864-876, 958, 960-964, 1245, 1247, 1291-1314, 1360-1365, 1386, 1713, 1740-1741, 1749-1753, 1822, 1836-1837, 1840-1841 |
| factory/runtime\_state.py                              |       51 |        0 |    100% |           |
| factory/scheduler/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/scheduler/cron.py                              |      132 |       11 |     92% |117, 122, 124, 171-175, 211, 353-354 |
| factory/settings/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/settings/audit.py                              |      113 |        5 |     96% |108-109, 111, 140-141 |
| factory/settings/enforcer.py                           |       54 |        0 |    100% |           |
| factory/settings/loader.py                             |       89 |        0 |    100% |           |
| factory/settings/modes.py                              |       40 |        1 |     98% |        67 |
| factory/settings/spend.py                              |       83 |       24 |     71% |56-57, 78-79, 93, 120-133, 152-158 |
| factory/testing/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/testing/flake.py                               |      124 |       24 |     81% |91, 121-149, 236-237, 239, 255, 282-283, 335-336, 339 |
| factory/tui/\_\_init\_\_.py                            |        2 |        0 |    100% |           |
| factory/tui/app.py                                     |      183 |      151 |     17% |48-57, 61, 66-74, 78, 87-121, 130-161, 166-232, 241-250, 254-274, 278-312, 316-339, 372-377, 380-388, 391-406, 409-415, 418-442, 454-461 |
| factory/webhook/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/webhook/github.py                              |      190 |       40 |     79% |56, 60, 63-64, 96, 126, 162-167, 191-207, 253, 308-312, 355-356, 379-391, 395 |
| factory/webhook/openhands\_events.py                   |       36 |        7 |     81% |69, 84-123 |
| **TOTAL**                                              | **15994** | **3304** | **79%** |           |


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