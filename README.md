# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/xvanov/software-factory/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                   |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------- | -------: | -------: | ------: | --------: |
| factory/\_\_init\_\_.py                                |        2 |        0 |    100% |           |
| factory/app\_config.py                                 |       82 |        5 |     94% |224, 228, 243, 261, 277 |
| factory/artifacts/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/backpressure/\_\_init\_\_.py                   |        0 |        0 |    100% |           |
| factory/backpressure/parser.py                         |       67 |        5 |     93% |103-104, 128, 132-133 |
| factory/backpressure/validator.py                      |       78 |        3 |     96% | 52-53, 72 |
| factory/chain/\_\_init\_\_.py                          |        2 |        0 |    100% |           |
| factory/chain/acceptance.py                            |      399 |       56 |     86% |197-198, 292, 300, 302, 307-308, 332-333, 339-342, 392, 445, 447, 480-510, 545, 586-587, 634, 642, 647, 686-687, 710, 721-722, 729, 803-810, 967-968, 1007, 1014-1015, 1019-1020, 1032-1033, 1050, 1064-1065 |
| factory/chain/auto\_merge.py                           |      686 |      108 |     84% |531-532, 579-581, 583, 585, 589-590, 757-758, 760, 797, 814, 910-911, 1045, 1150-1151, 1443-1444, 1454, 1472-1473, 1475, 1478-1479, 1487, 1518-1519, 1521, 1546, 1548, 1557-1558, 1569-1570, 1593, 1635, 1638-1639, 1641, 1649, 1678-1679, 1683-1684, 1704-1705, 1708, 1780, 1794-1795, 1838-1839, 1847-1848, 1857-1858, 1867-1868, 1940-1941, 2011, 2165, 2184-2185, 2260-2261, 2315, 2340-2392, 2415, 2546-2547, 2570-2571, 2590-2594, 2615-2623, 2641-2645, 2696-2697, 2733-2736, 2760-2761, 2783-2784, 2795-2796, 2835-2836 |
| factory/chain/branch.py                                |       56 |        4 |     93% |   163-166 |
| factory/chain/bug\_hunter.py                           |        8 |        8 |      0% |     13-62 |
| factory/chain/ci\_health.py                            |      197 |       28 |     86% |113-114, 131, 134, 178, 181, 201, 210, 217, 251, 264, 326, 330, 339, 343-344, 421-422, 430-431, 449-450, 468-469, 494-495, 505-506 |
| factory/chain/context\_refresh.py                      |      179 |       40 |     78% |123-130, 211, 222-248, 277-290, 360-369, 411, 442, 477, 524-526, 541-543, 545-548, 553-556, 564-565, 567, 571-572 |
| factory/chain/dual\_draft.py                           |      150 |       15 |     90% |64-65, 197, 228, 230, 234, 384, 402-403, 445-446, 477-478, 480-481 |
| factory/chain/ears.py                                  |       71 |        0 |    100% |           |
| factory/chain/event\_log.py                            |       55 |        3 |     95% |122, 132-133 |
| factory/chain/factory\_status.py                       |      144 |        8 |     94% |88-89, 121-122, 124, 267, 289-291 |
| factory/chain/gates/\_\_init\_\_.py                    |        3 |        0 |    100% |           |
| factory/chain/gates/acceptance\_verified.py            |      308 |       25 |     92% |408, 479-480, 485, 518-519, 767, 776, 787, 837, 1033, 1120-1122, 1128-1133, 1152, 1158-1159, 1166-1167, 1244, 1256-1257 |
| factory/chain/gates/canonical\_paths\_only.py          |       10 |        0 |    100% |           |
| factory/chain/gates/docs\_current.py                   |       23 |        3 |     87% | 19, 24-25 |
| factory/chain/gates/evaluator.py                       |       55 |        4 |     93% |   172-177 |
| factory/chain/gates/production\_tree\_changed.py       |       56 |        9 |     84% |116-117, 135-136, 138, 160-161, 167, 219 |
| factory/chain/gates/smoke\_green.py                    |       12 |        0 |    100% |           |
| factory/chain/gates/tests\_green.py                    |       38 |       10 |     74% |47-63, 122, 143 |
| factory/chain/gates/tests\_meaningful.py               |       11 |        0 |    100% |           |
| factory/chain/handlers.py                              |     1483 |      238 |     84% |153-154, 188-189, 377-378, 456-470, 477-478, 504-505, 517-528, 550-551, 558-570, 662-663, 667-668, 805-808, 810-813, 817-818, 860, 1013, 1147, 1169-1171, 1185-1186, 1395, 1505-1511, 1547-1548, 1579-1580, 1584-1586, 1750, 1772, 1779, 1787-1788, 1790-1793, 1853-1854, 1864-1871, 1873-1881, 2073-2075, 2147-2149, 2174-2175, 2202, 2232, 2248-2251, 2295-2296, 2304, 2310, 2362-2363, 2497, 2501-2502, 2550, 2563-2564, 2566-2577, 2611, 2668-2669, 2686-2687, 2689, 2710-2711, 2718, 2817-2818, 2829-2830, 2852-2853, 2855, 2864, 2894-2895, 2902, 2915-2916, 2918, 3095, 3099-3100, 3190-3194, 3307-3313, 3353-3354, 3365, 3435-3436, 3498-3502, 3520-3523, 3650-3651, 3934-3938, 4032-4033, 4079-4083, 4101-4103, 4132-4165, 4215-4216, 4249-4250, 4255, 4288-4289, 4326-4327, 4444-4445, 4451, 4471, 4474-4475, 4480, 4536-4537, 4577-4585, 4637-4638, 4706-4707, 4709-4710, 4723-4724, 4728-4747, 4845-4846, 4972-4980 |
| factory/chain/idle.py                                  |      209 |       33 |     84% |91-92, 148-150, 158, 169, 172-173, 184-185, 248-250, 271-272, 295-296, 317-318, 340, 365, 368, 392-404, 422 |
| factory/chain/issue\_intake.py                         |       46 |        5 |     89% |55, 89-90, 92-93 |
| factory/chain/mutation.py                              |      570 |      101 |     82% |263-264, 305, 327, 334, 350, 359, 387, 407, 409, 420, 422-428, 448, 464, 467-469, 530-531, 541, 556, 559-560, 609, 617-621, 641-642, 671-672, 710-716, 735-747, 792, 796, 798, 813, 853-854, 894, 903, 959-964, 969-972, 999-1000, 1034, 1078, 1087, 1095, 1208-1209, 1213, 1270-1271, 1275-1276, 1280-1281, 1287-1288, 1348-1349, 1356-1357, 1366-1367, 1373-1374, 1377-1380, 1398 |
| factory/chain/orchestrator.py                          |      978 |      189 |     81% |370, 536, 631, 643, 755, 762, 767, 770-771, 789, 886, 891-892, 895, 899-900, 1107-1108, 1283-1312, 1323-1348, 1422, 1433, 1477-1505, 1540-1541, 1557-1558, 1576, 1592, 1606, 1615-1616, 1663, 1671-1672, 1684-1685, 1694, 1700-1701, 1746-1748, 1753, 1836-1837, 1879, 1928-1938, 2029, 2051, 2102-2103, 2109-2110, 2145-2146, 2151-2152, 2210-2211, 2220-2221, 2272-2275, 2288, 2295-2316, 2334-2335, 2354-2355, 2377-2379, 2391-2393, 2405-2407, 2432-2439, 2444-2446, 2454-2456, 2466-2467, 2485-2490, 2505-2506, 2528-2532, 2542-2543, 2582-2589, 2609-2610, 2789, 2913-2923, 2968-2969, 3132-3136, 3151-3154, 3174-3184, 3187-3189, 3210-3211 |
| factory/chain/pm\_sync.py                              |      260 |       40 |     85% |173-174, 176-177, 179-181, 199, 208, 437, 469, 510-514, 518, 574, 590-602, 618-628, 644, 651, 661-663, 686-687, 698, 710-712, 790-791, 793, 803-804, 824 |
| factory/chain/red\_green.py                            |      330 |       31 |     91% |335-336, 361, 375, 414, 423, 439, 446, 474-476, 526-532, 636, 645-646, 666-667, 717, 755, 758-759, 785, 792-793, 831, 846-847 |
| factory/chain/review\_events.py                        |       11 |        0 |    100% |           |
| factory/chain/rollback.py                              |      106 |        3 |     97% |102-103, 105 |
| factory/chain/scheduled\_tasks.py                      |      309 |       38 |     88% |231, 240-243, 344, 374-375, 407, 608-610, 625, 630, 639-641, 708-709, 732, 736, 739, 744-745, 773-774, 776-777, 849, 859, 862-863, 927-933 |
| factory/chain/security.py                              |        7 |        7 |      0% |     11-46 |
| factory/chain/slop\_detector.py                        |      301 |       33 |     89% |113, 137-140, 166, 168, 185, 193, 208, 214, 233, 288-289, 319, 330, 361-376, 391, 400, 551, 609, 617-618, 621 |
| factory/chain/state\_machine.py                        |      123 |        0 |    100% |           |
| factory/chain/step\_events.py                          |       59 |        7 |     88% |127-128, 157, 160-161, 168-169 |
| factory/chain/ux\_auditor.py                           |        7 |        7 |      0% |     14-49 |
| factory/chain/worktree.py                              |      123 |       25 |     80% |115-116, 162-163, 168, 197, 200-202, 260, 263-269, 290, 307-308, 331, 335, 344-345, 353, 355-356 |
| factory/cli.py                                         |     1684 |      835 |     50% |48-49, 64, 92-144, 164-175, 200-205, 213-219, 228-249, 266-299, 314, 333-334, 398-399, 408-410, 438-442, 445-449, 510-511, 528-529, 545-546, 549-553, 602, 646, 686-722, 731-777, 802-841, 850-862, 891-892, 916-922, 939-940, 945, 969-1004, 1011-1034, 1051-1063, 1072-1074, 1083-1090, 1115-1137, 1165, 1167, 1169-1174, 1183-1195, 1197, 1205, 1235-1250, 1274, 1386-1387, 1429-1430, 1432-1443, 1452, 1482-1483, 1485, 1500-1501, 1503-1504, 1506, 1531-1539, 1541, 1559-1560, 1585-1586, 1588, 1600-1641, 1670-1692, 1709-1718, 1749-1773, 1790-1808, 1819-1834, 1861-1862, 1960-1961, 2013, 2021, 2070-2074, 2114-2154, 2160-2165, 2189-2206, 2226-2302, 2306-2341, 2360-2370, 2392-2403, 2436, 2461, 2493, 2559-2591, 2681-2718, 2751, 2755-2763, 2881-2937, 2950-2977, 2995-2998, 3015, 3018, 3067, 3101-3102, 3132-3138, 3194-3196, 3211-3234, 3257, 3260-3264, 3285-3292, 3296-3298, 3307-3308, 3314-3315, 3319, 3322-3323, 3328-3330, 3336-3337, 3379-3399, 3421-3439, 3452-3478, 3518-3576, 3605-3606, 3679-3719, 3748-3816, 3847-3934 |
| factory/context/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/context/canonical\_paths.py                    |       36 |        2 |     94% |     90-91 |
| factory/context/enforcer.py                            |       49 |        0 |    100% |           |
| factory/context/loader.py                              |       87 |        5 |     94% |97, 101-102, 106, 179 |
| factory/context/navigator.py                           |       39 |        2 |     95% |     65-66 |
| factory/context/updater.py                             |       29 |        1 |     97% |        77 |
| factory/deploy/\_\_init\_\_.py                         |        4 |        0 |    100% |           |
| factory/deploy/models.py                               |       28 |        0 |    100% |           |
| factory/deploy/orchestrator.py                         |      284 |       34 |     88% |257, 259-262, 265-267, 316, 402-405, 431-441, 486-490, 532-536, 555-556, 561, 578, 589, 596, 704-705 |
| factory/deploy/runner.py                               |       56 |        0 |    100% |           |
| factory/diff\_paths.py                                 |       43 |        0 |    100% |           |
| factory/directions/\_\_init\_\_.py                     |        0 |        0 |    100% |           |
| factory/directions/approval.py                         |       73 |        4 |     95% |101, 133, 173, 185 |
| factory/directions/backfill.py                         |      172 |        9 |     95% |104, 108, 118-119, 121, 137, 168, 175, 373 |
| factory/directions/creator.py                          |      150 |       69 |     54% |126, 156, 163, 197, 214-222, 232-343 |
| factory/directions/gc.py                               |       74 |        9 |     88% |66, 70, 86-87, 89, 158-159, 204-205 |
| factory/directions/ingester.py                         |       77 |        2 |     97% |   55, 131 |
| factory/directions/parser.py                           |      242 |       21 |     91% |58, 148, 158-159, 173, 201-203, 258, 264-265, 269, 291, 297, 307, 333, 346, 358, 383, 396-398 |
| factory/directions/schema.py                           |       56 |        1 |     98% |       159 |
| factory/directions/tracker\_backfill.py                |       74 |        5 |     93% |110-111, 113, 135-136 |
| factory/directions/tracker\_issue.py                   |      358 |       41 |     89% |79-81, 126, 132, 136, 184-185, 216, 220-221, 277-281, 375-376, 440, 463, 471-473, 480-481, 484, 488-490, 619, 626, 641, 648-649, 741-743, 758, 772-773, 861 |
| factory/directions/watcher.py                          |      130 |       28 |     78% |105, 116-117, 208, 257-258, 270, 272-273, 293-295, 305-315, 320-325 |
| factory/events/\_\_init\_\_.py                         |        1 |        0 |    100% |           |
| factory/events/rotation.py                             |       78 |       16 |     79% |62-63, 67-69, 96-98, 113, 116-117, 123-124, 144, 163-164 |
| factory/git\_state.py                                  |       41 |        2 |     95% |    47, 60 |
| factory/manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/manager/circuit\_breaker.py                    |      187 |       36 |     81% |132-133, 155, 160-163, 184-186, 201-203, 262-265, 273-278, 354-357, 378-382, 436-439, 443, 446, 473-474, 568-573 |
| factory/manager/detectors/\_\_init\_\_.py              |       17 |        0 |    100% |           |
| factory/manager/detectors/conformance\_breach.py       |       24 |        8 |     67% |60-61, 65-66, 69-72, 79-80 |
| factory/manager/detectors/cost\_spike.py               |       50 |        5 |     90% |29, 32-33, 112, 117 |
| factory/manager/detectors/fms\_yield.py                |       63 |        6 |     90% |84, 87-88, 90, 94-95 |
| factory/manager/detectors/placeholder\_prompts.py      |       32 |        1 |     97% |        66 |
| factory/manager/detectors/retry\_storm.py              |       44 |        3 |     93% | 67, 70-71 |
| factory/manager/detectors/review\_churn.py             |       52 |        5 |     90% |110, 113-114, 120, 123 |
| factory/manager/detectors/runs\_failed\_since.py       |       25 |        3 |     88% | 49, 52-53 |
| factory/manager/detectors/stalled\_stories.py          |      165 |       27 |     84% |71, 74-75, 77, 97, 100-101, 103, 107-108, 128, 131-132, 134, 138-139, 159, 162-163, 166-167, 187-188, 191, 275-276, 294 |
| factory/manager/detectors/state\_distribution\_skew.py |       41 |        5 |     88% |77, 80-81, 83, 89 |
| factory/manager/detectors/tick\_duration\_outliers.py  |       70 |        8 |     89% |23, 25-26, 87, 90-91, 95, 117 |
| factory/manager/detectors/worktree\_orphans.py         |       38 |        4 |     89% |64-65, 86-87 |
| factory/manager/escalation.py                          |      180 |       22 |     88% |100, 126-128, 138-139, 152-153, 167, 312-313, 315, 319, 369, 432-433, 478-479, 516-517, 554-555 |
| factory/manager/forbidden\_paths.py                    |       21 |        4 |     81% |    97-100 |
| factory/manager/halt.py                                |      126 |       24 |     81% |101-102, 180-185, 247, 293-296, 314-315, 317, 322-324, 332-337 |
| factory/manager/poison\_escalation.py                  |      109 |       16 |     85% |93-94, 99, 102-103, 127, 173, 181, 183, 315-324, 345-346, 360-361 |
| factory/manager/recovery.py                            |      467 |       63 |     87% |188, 191-192, 194, 234-238, 251, 254, 256, 301-302, 359, 370-371, 417, 422-423, 477, 490-491, 505, 559-560, 571-572, 620, 637-638, 676, 679-680, 683, 817, 827-828, 835, 844-845, 857, 966-967, 986, 989-990, 993-994, 1010, 1031, 1033, 1063-1064, 1134-1135, 1352-1371 |
| factory/manager/self\_context.py                       |      141 |       29 |     79% |43-45, 55-57, 174-175, 193, 204, 207, 210-211, 216-217, 261-262, 296-302, 327, 342-343, 392, 397-404 |
| factory/manager/signals.py                             |      100 |        5 |     95% |159-160, 180-181, 343 |
| factory/manager/staging.py                             |      156 |       11 |     93% |217, 318-319, 405, 448, 463, 481, 573-594 |
| factory/model\_router.py                               |      162 |        8 |     95% |53, 55, 67, 185, 292-295 |
| factory/observability/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| factory/observability/audit\_chain.py                  |      216 |       26 |     88% |170-187, 248, 327, 331, 358-359, 373, 382-383, 455-460, 549-550 |
| factory/observability/conformance.py                   |      148 |       11 |     93% |120, 181, 209, 215, 225, 306, 351-356 |
| factory/observability/estimator.py                     |      185 |       31 |     83% |170-185, 219, 242-244, 331, 333, 337, 384, 417, 450, 470, 489, 491, 493, 498 |
| factory/observability/heartbeat.py                     |       60 |        7 |     88% |69, 74-77, 129-130 |
| factory/observability/queries.py                       |      321 |       62 |     81% |150-151, 153, 205-208, 261-266, 273, 325-326, 340, 368-369, 463, 465-489, 537-540, 546, 594-597, 643-652, 655-661 |
| factory/observability/schema.py                        |       61 |        2 |     97% |   130-131 |
| factory/observability/state\_trace.py                  |       99 |       20 |     80% |111-112, 125-127, 189, 195-196, 200-201, 218-219, 248, 251-252, 254, 256, 258, 260-261 |
| factory/personas/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/personas/loader.py                             |       86 |        5 |     94% |124-125, 151-152, 187 |
| factory/personas/validator.py                          |      107 |       10 |     91% |89, 115, 154, 176, 211, 221, 278-279, 298-299 |
| factory/power.py                                       |      140 |        3 |     98% |90, 101, 175 |
| factory/providers/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/providers/azure\_foundry.py                    |       34 |        0 |    100% |           |
| factory/providers/github.py                            |       23 |        2 |     91% |     79-81 |
| factory/runner.py                                      |      903 |      136 |     85% |161-162, 242-243, 312-313, 366-367, 377-378, 382-383, 409-412, 464-465, 508, 515-516, 728-729, 755-756, 820, 832, 858, 896, 930-931, 933-938, 957-958, 961-967, 988, 1053-1054, 1101-1102, 1118, 1121, 1123, 1128-1129, 1137-1152, 1163-1169, 1185-1186, 1192, 1197-1208, 1217-1227, 1232, 1235, 1274, 1289, 1326-1327, 1332-1344, 1426, 1428-1432, 1736, 1738, 1853-1858, 1879, 1938, 2321, 2349-2350, 2358-2362, 2440, 2463-2464, 2467-2468 |
| factory/runtime\_state.py                              |       51 |        0 |    100% |           |
| factory/scheduler/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/scheduler/cron.py                              |      132 |       11 |     92% |117, 122, 124, 171-175, 211, 353-354 |
| factory/settings/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/settings/audit.py                              |      124 |        5 |     96% |129-130, 132, 161-162 |
| factory/settings/enforcer.py                           |       54 |        0 |    100% |           |
| factory/settings/loader.py                             |       88 |        0 |    100% |           |
| factory/settings/modes.py                              |       40 |        1 |     98% |        67 |
| factory/settings/spend.py                              |       83 |       24 |     71% |56-57, 78-79, 93, 120-133, 152-158 |
| factory/testing/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/testing/flake.py                               |      124 |       24 |     81% |91, 121-149, 236-237, 239, 255, 282-283, 335-336, 339 |
| factory/tui/\_\_init\_\_.py                            |        2 |        0 |    100% |           |
| factory/tui/app.py                                     |      183 |      151 |     17% |48-57, 61, 66-74, 78, 87-121, 130-161, 166-232, 241-250, 254-274, 278-312, 316-339, 372-377, 380-388, 391-406, 409-415, 418-442, 454-461 |
| factory/webhook/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/webhook/github.py                              |      190 |       40 |     79% |56, 60, 63-64, 96, 126, 162-167, 191-207, 253, 308-312, 355-356, 379-391, 395 |
| factory/webhook/openhands\_events.py                   |       36 |        7 |     81% |69, 84-123 |
| **TOTAL**                                              | **17239** | **3048** | **82%** |           |


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