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
| factory/chain/\_\_init\_\_.py                          |        2 |        0 |    100% |           |
| factory/chain/acceptance.py                            |      166 |       35 |     79% |88-89, 95-98, 148, 189, 191, 200-228, 236-237, 320, 350, 357-358, 371-372, 381-382, 384-385, 388-389 |
| factory/chain/auto\_merge.py                           |      686 |      108 |     84% |523-524, 571-573, 575, 577, 581-582, 749-750, 752, 789, 806, 902-903, 1025, 1130-1131, 1423-1424, 1434, 1452-1453, 1455, 1458-1459, 1467, 1498-1499, 1501, 1526, 1528, 1537-1538, 1549-1550, 1573, 1615, 1618-1619, 1621, 1629, 1658-1659, 1663-1664, 1684-1685, 1688, 1760, 1774-1775, 1818-1819, 1827-1828, 1837-1838, 1847-1848, 1920-1921, 1991, 2145, 2164-2165, 2240-2241, 2295, 2320-2372, 2395, 2526-2527, 2550-2551, 2570-2574, 2595-2603, 2621-2625, 2676-2677, 2713-2716, 2740-2741, 2763-2764, 2775-2776, 2815-2816 |
| factory/chain/branch.py                                |       56 |        4 |     93% |   163-166 |
| factory/chain/bug\_hunter.py                           |        8 |        8 |      0% |     13-62 |
| factory/chain/ci\_health.py                            |      197 |       28 |     86% |113-114, 131, 134, 178, 181, 201, 210, 217, 251, 264, 326, 330, 339, 343-344, 421-422, 430-431, 449-450, 468-469, 494-495, 505-506 |
| factory/chain/context\_refresh.py                      |      179 |       40 |     78% |123-130, 211, 222-248, 277-290, 360-369, 411, 442, 477, 524-526, 541-543, 545-548, 553-556, 564-565, 567, 571-572 |
| factory/chain/dual\_draft.py                           |      150 |       15 |     90% |64-65, 197, 228, 230, 234, 383, 401-402, 444-445, 476-477, 479-480 |
| factory/chain/ears.py                                  |       71 |        0 |    100% |           |
| factory/chain/event\_log.py                            |       55 |        3 |     95% |122, 132-133 |
| factory/chain/factory\_improver.py                     |      274 |       92 |     66% |142, 159-160, 162, 167-168, 184-226, 259-260, 267-268, 335, 378-400, 414-415, 440-441, 518-519, 540, 566, 634-672, 689-691, 705-717, 744-787 |
| factory/chain/factory\_improver\_apply.py              |      355 |       39 |     89% |120, 204, 240, 253, 321, 386-387, 458-459, 469, 498-499, 546, 553-554, 577-578, 600, 637, 693-694, 722, 782, 815-824, 921-922, 925, 935-944, 958, 1031-1035 |
| factory/chain/factory\_status.py                       |      144 |        8 |     94% |88-89, 121-122, 124, 267, 289-291 |
| factory/chain/gates/\_\_init\_\_.py                    |        3 |        0 |    100% |           |
| factory/chain/gates/acceptance\_verified.py            |       40 |        2 |     95% |   161-162 |
| factory/chain/gates/canonical\_paths\_only.py          |       10 |        0 |    100% |           |
| factory/chain/gates/docs\_current.py                   |       23 |        3 |     87% | 19, 24-25 |
| factory/chain/gates/evaluator.py                       |       55 |        4 |     93% |   172-177 |
| factory/chain/gates/production\_tree\_changed.py       |       56 |        9 |     84% |116-117, 135-136, 138, 160-161, 167, 219 |
| factory/chain/gates/smoke\_green.py                    |       12 |        0 |    100% |           |
| factory/chain/gates/tests\_green.py                    |       38 |       10 |     74% |47-63, 122, 143 |
| factory/chain/gates/tests\_meaningful.py               |      100 |       17 |     83% |88, 103, 157, 160-161, 196, 216-217, 221, 240-249, 253 |
| factory/chain/handlers.py                              |     1483 |      243 |     84% |153-154, 188-189, 366-378, 456-470, 477-478, 504-505, 517-528, 550-551, 558-570, 589-590, 662-663, 667-668, 805-808, 810-813, 817-818, 860, 1013, 1147, 1169-1171, 1185-1186, 1395, 1505-1511, 1547-1548, 1579-1580, 1584-1586, 1750, 1772, 1779, 1787-1788, 1790-1793, 1853-1854, 1864-1871, 1873-1881, 2073-2075, 2147-2149, 2174-2175, 2202, 2232, 2248-2251, 2295-2296, 2304, 2310, 2362-2363, 2495, 2499-2500, 2548, 2561-2562, 2564-2575, 2609, 2666-2667, 2684-2685, 2687, 2708-2709, 2716, 2815-2816, 2827-2828, 2850-2851, 2853, 2862, 2892-2893, 2900, 2913-2914, 2916, 3093, 3097-3098, 3188-3192, 3305-3311, 3351-3352, 3363, 3433-3434, 3496-3500, 3518-3521, 3648-3649, 3932-3936, 4030-4031, 4077-4081, 4099-4101, 4130-4163, 4213-4214, 4247-4248, 4253, 4286-4287, 4324-4325, 4442-4443, 4449, 4469, 4472-4473, 4478, 4534-4535, 4575-4583, 4635-4636, 4704-4705, 4707-4708, 4721-4722, 4726-4745, 4843-4844, 4970-4978 |
| factory/chain/idle.py                                  |      209 |       33 |     84% |91-92, 148-150, 158, 169, 172-173, 184-185, 248-250, 271-272, 295-296, 317-318, 340, 365, 368, 392-404, 422 |
| factory/chain/issue\_intake.py                         |       46 |        5 |     89% |55, 89-90, 92-93 |
| factory/chain/orchestrator.py                          |      978 |      189 |     81% |370, 536, 631, 643, 755, 762, 767, 770-771, 789, 886, 891-892, 895, 899-900, 1107-1108, 1283-1312, 1323-1348, 1422, 1433, 1477-1505, 1540-1541, 1557-1558, 1576, 1592, 1606, 1615-1616, 1663, 1671-1672, 1684-1685, 1694, 1700-1701, 1746-1748, 1753, 1836-1837, 1879, 1928-1938, 2029, 2051, 2102-2103, 2109-2110, 2145-2146, 2151-2152, 2210-2211, 2220-2221, 2272-2275, 2288, 2295-2316, 2334-2335, 2354-2355, 2377-2379, 2391-2393, 2405-2407, 2432-2439, 2444-2446, 2454-2456, 2466-2467, 2485-2490, 2505-2506, 2528-2532, 2542-2543, 2582-2589, 2609-2610, 2789, 2913-2923, 2968-2969, 3132-3136, 3151-3154, 3174-3184, 3187-3189, 3210-3211 |
| factory/chain/pm\_sync.py                              |      260 |       40 |     85% |173-174, 176-177, 179-181, 199, 208, 437, 469, 510-514, 518, 574, 590-602, 618-628, 644, 651, 661-663, 686-687, 698, 710-712, 790-791, 793, 803-804, 824 |
| factory/chain/review\_events.py                        |       11 |        0 |    100% |           |
| factory/chain/rollback.py                              |      106 |        3 |     97% |102-103, 105 |
| factory/chain/scheduled\_tasks.py                      |      309 |       38 |     88% |231, 240-243, 344, 374-375, 407, 608-610, 625, 630, 639-641, 708-709, 732, 736, 739, 744-745, 773-774, 776-777, 849, 859, 862-863, 927-933 |
| factory/chain/security.py                              |        7 |        7 |      0% |     11-46 |
| factory/chain/slop\_detector.py                        |      301 |       33 |     89% |113, 137-140, 166, 168, 185, 193, 208, 214, 233, 288-289, 319, 330, 361-376, 391, 400, 551, 609, 617-618, 621 |
| factory/chain/state\_machine.py                        |      123 |        0 |    100% |           |
| factory/chain/step\_events.py                          |       59 |        7 |     88% |127-128, 157, 160-161, 168-169 |
| factory/chain/ux\_auditor.py                           |        7 |        7 |      0% |     14-49 |
| factory/chain/worktree.py                              |      112 |       23 |     79% |134-135, 140, 169, 172-174, 232, 235-241, 262, 279-280, 303, 307, 316-317, 325, 327-328 |
| factory/cli.py                                         |     1725 |      936 |     46% |48-49, 64, 92-144, 164-175, 189-205, 213-219, 228-249, 266-299, 314, 333-334, 398-399, 408-410, 438-442, 445-449, 496, 540, 580-616, 625-671, 696-735, 744-756, 783-786, 810-816, 838-886, 890-891, 896, 920-955, 962-985, 1002-1014, 1023-1025, 1034-1041, 1066-1088, 1116, 1118, 1120-1125, 1134-1146, 1148, 1156, 1186-1201, 1225, 1337-1338, 1373, 1403-1404, 1406, 1421-1422, 1424-1425, 1427, 1452-1460, 1462, 1480-1481, 1506-1507, 1509, 1521-1562, 1591-1613, 1630-1639, 1670-1694, 1711-1729, 1740-1755, 1782-1783, 1881-1882, 1934, 1942, 1991-1995, 2035-2075, 2081-2086, 2110-2127, 2147-2223, 2227-2262, 2281-2291, 2313-2324, 2357, 2382, 2414, 2480-2512, 2524-2561, 2594, 2598-2606, 2724-2780, 2793-2820, 2838-2841, 2858, 2861, 2928-2983, 3023, 3057-3058, 3088-3094, 3150-3152, 3167-3190, 3213, 3216-3220, 3241-3248, 3252-3254, 3263-3264, 3270-3271, 3275, 3278-3279, 3284-3286, 3292-3293, 3417-3431, 3471-3486, 3532-3551, 3606-3631, 3650-3666, 3680-3700, 3722-3740, 3753-3779, 3819-3877, 3906-3907, 3980-4020, 4049-4117, 4148-4235 |
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
| factory/diff\_paths.py                                 |       24 |        0 |    100% |           |
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
| factory/manager/apply.py                               |      472 |      168 |     64% |192-194, 208-211, 262-265, 304, 372, 377, 381, 399, 402, 444-483, 495, 506-536, 545-602, 625, 638, 647, 697-704, 772-773, 796-803, 857-861, 930-931, 935-936, 941-943, 1001, 1004-1008, 1012-1016, 1034-1037, 1049-1051, 1092-1094, 1099, 1103-1108, 1183-1186, 1209, 1219, 1224-1225 |
| factory/manager/circuit\_breaker.py                    |      187 |       36 |     81% |126-127, 149, 154-157, 178-180, 195-197, 256-259, 267-272, 348-351, 372-376, 430-433, 437, 440, 467-468, 562-567 |
| factory/manager/detectors/\_\_init\_\_.py              |       17 |        0 |    100% |           |
| factory/manager/detectors/conformance\_breach.py       |       24 |        8 |     67% |60-61, 65-66, 69-72, 79-80 |
| factory/manager/detectors/cost\_spike.py               |       50 |        4 |     92% |29, 32-33, 112 |
| factory/manager/detectors/fms\_yield.py                |       63 |        6 |     90% |84, 87-88, 90, 94-95 |
| factory/manager/detectors/placeholder\_prompts.py      |       32 |        1 |     97% |        66 |
| factory/manager/detectors/retry\_storm.py              |       44 |        3 |     93% | 67, 70-71 |
| factory/manager/detectors/review\_churn.py             |       52 |        5 |     90% |110, 113-114, 120, 123 |
| factory/manager/detectors/runs\_failed\_since.py       |       25 |        3 |     88% | 49, 52-53 |
| factory/manager/detectors/stalled\_stories.py          |      165 |       25 |     85% |71, 74-75, 77, 97, 100-101, 103, 107-108, 128, 131-132, 134, 138-139, 159, 162-163, 166-167, 187-188, 191, 294 |
| factory/manager/detectors/state\_distribution\_skew.py |       41 |        5 |     88% |77, 80-81, 83, 89 |
| factory/manager/detectors/tick\_duration\_outliers.py  |       70 |        8 |     89% |23, 25-26, 87, 90-91, 95, 117 |
| factory/manager/detectors/worktree\_orphans.py         |       38 |        4 |     89% |64-65, 86-87 |
| factory/manager/diagnostician.py                       |      466 |      100 |     79% |235-236, 248-249, 348-349, 356, 363, 402-403, 548-550, 559, 570-571, 576, 581-583, 586, 594, 653-657, 738-739, 753, 794-797, 826-831, 880-881, 907-908, 953-955, 974-975, 1037-1042, 1044-1049, 1156-1157, 1169-1170, 1191-1192, 1224-1312 |
| factory/manager/escalation.py                          |      180 |       21 |     88% |126-128, 138-139, 152-153, 167, 312-313, 315, 319, 369, 432-433, 478-479, 516-517, 554-555 |
| factory/manager/halt.py                                |      126 |       24 |     81% |101-102, 180-185, 247, 293-296, 314-315, 317, 322-324, 332-337 |
| factory/manager/poison\_escalation.py                  |      109 |       16 |     85% |93-94, 99, 102-103, 127, 173, 181, 183, 315-324, 345-346, 360-361 |
| factory/manager/recovery.py                            |      467 |       63 |     87% |182, 185-186, 188, 228-232, 245, 248, 250, 295-296, 353, 364-365, 411, 416-417, 471, 484-485, 499, 553-554, 565-566, 614, 631-632, 670, 673-674, 677, 811, 821-822, 829, 838-839, 851, 960-961, 980, 983-984, 987-988, 1004, 1025, 1027, 1057-1058, 1128-1129, 1346-1365 |
| factory/manager/self\_context.py                       |      141 |       29 |     79% |43-45, 55-57, 170-171, 189, 200, 203, 206-207, 212-213, 257-258, 292-298, 323, 338-339, 388, 393-400 |
| factory/manager/signals.py                             |      100 |        5 |     95% |159-160, 180-181, 343 |
| factory/manager/staging.py                             |      152 |       11 |     93% |206, 307-308, 394, 437, 452, 470, 562-583 |
| factory/manager/summarizer.py                          |      414 |      104 |     75% |42-44, 55-57, 118, 123, 147, 150-151, 155-156, 180, 183-184, 204, 207-208, 212-213, 215, 219, 221-222, 293, 305, 308-309, 311, 332-333, 573-576, 578, 584-606, 647-649, 670-671, 674-675, 776-778, 783-785, 883-963 |
| factory/manager/watcher.py                             |      407 |      124 |     70% |41-43, 54-56, 130, 133-134, 138-139, 172, 189, 204, 207-208, 210-211, 222, 226, 228-229, 293-304, 437-440, 442, 450-472, 540-541, 548-549, 559-560, 565-566, 573-574, 581-582, 587-588, 597-598, 610-611, 676-677, 680-683, 799-826, 835-841, 858-865, 886-889, 908-921, 942, 947, 975-976, 978, 999, 1041-1054, 1065-1098 |
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
| factory/power.py                                       |      140 |        3 |     98% |83, 94, 168 |
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
| **TOTAL**                                              | **18299** | **3612** | **80%** |           |


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