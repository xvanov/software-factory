# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/xvanov/software-factory/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                   |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------- | -------: | -------: | ------: | --------: |
| factory/\_\_init\_\_.py                                |        2 |        0 |    100% |           |
| factory/app\_config.py                                 |       96 |        5 |     95% |277, 281, 296, 314, 330 |
| factory/artifacts/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/backpressure/\_\_init\_\_.py                   |        0 |        0 |    100% |           |
| factory/backpressure/parser.py                         |       67 |        5 |     93% |103-104, 128, 132-133 |
| factory/backpressure/vacuity.py                        |      109 |        5 |     95% |511, 520, 534-541 |
| factory/backpressure/validator.py                      |      101 |        7 |     93% |60-61, 80, 147-153, 156 |
| factory/chain/\_\_init\_\_.py                          |        2 |        0 |    100% |           |
| factory/chain/acceptance.py                            |      398 |       57 |     86% |197-198, 292, 300, 302, 307-308, 332-333, 339-342, 442, 444, 475-505, 547, 595-596, 643, 651, 656, 695-696, 719, 730-731, 738, 812-819, 977-978, 1017, 1024-1025, 1029-1030, 1042-1043, 1058, 1075-1076, 1095-1096 |
| factory/chain/auto\_merge.py                           |      763 |      116 |     85% |543-544, 591-593, 595, 597, 601-602, 769-770, 772, 809, 826, 916-917, 932-933, 1018-1019, 1220, 1325-1326, 1535-1536, 1563, 1578-1579, 1704-1705, 1715, 1733-1734, 1736, 1739-1740, 1748, 1779-1780, 1782, 1807, 1809, 1818-1819, 1830-1831, 1854, 1896, 1899-1900, 1902, 1910, 1939-1940, 1944-1945, 1965-1966, 1969, 2041, 2055-2056, 2099-2100, 2108-2109, 2118-2119, 2128-2129, 2201-2202, 2272, 2426, 2445-2446, 2521-2522, 2576, 2601-2653, 2830-2831, 2854-2855, 2874-2878, 2899-2907, 2925-2929, 2980-2981, 3017-3020, 3044-3045, 3067-3068, 3079-3080, 3119-3120 |
| factory/chain/boot.py                                  |      217 |       45 |     79% |59-65, 121-122, 124, 155-156, 187-188, 200, 222-225, 227-235, 256, 265-269, 352-354, 361-364, 370-371, 397, 400 |
| factory/chain/branch.py                                |       56 |        4 |     93% |   163-166 |
| factory/chain/ci\_health.py                            |      197 |       28 |     86% |113-114, 131, 134, 178, 181, 201, 210, 217, 251, 264, 326, 330, 339, 343-344, 421-422, 430-431, 449-450, 468-469, 494-495, 505-506 |
| factory/chain/context\_refresh.py                      |      179 |       40 |     78% |123-130, 211, 222-248, 277-290, 360-369, 411, 442, 477, 524-526, 541-543, 545-548, 553-556, 564-565, 567, 571-572 |
| factory/chain/detector\_watch.py                       |      374 |       73 |     80% |254, 257, 266-267, 269, 321, 356, 372-373, 408-415, 425-430, 446-453, 480-485, 488-490, 542, 570, 574-576, 595-610, 717-718, 799, 802, 819-820, 835-836, 838, 845, 1020, 1073-1075 |
| factory/chain/dual\_draft.py                           |      150 |       15 |     90% |64-65, 197, 228, 230, 234, 384, 402-403, 445-446, 477-478, 480-481 |
| factory/chain/event\_log.py                            |       55 |        3 |     95% |122, 132-133 |
| factory/chain/factory\_status.py                       |      144 |        8 |     94% |88-89, 121-122, 124, 267, 289-291 |
| factory/chain/gates/\_\_init\_\_.py                    |        3 |        0 |    100% |           |
| factory/chain/gates/acceptance\_verified.py            |      350 |       36 |     90% |257, 267-268, 273, 297-298, 369, 563, 572, 580, 614, 644, 670, 680, 716, 763, 770, 783, 798, 824, 835, 860, 920, 934, 979, 1033-1035, 1041-1046, 1057, 1060-1061, 1068-1069 |
| factory/chain/gates/canonical\_paths\_only.py          |       12 |        0 |    100% |           |
| factory/chain/gates/docs\_current.py                   |       23 |        3 |     87% | 19, 24-25 |
| factory/chain/gates/evaluator.py                       |       55 |        4 |     93% |   172-177 |
| factory/chain/gates/production\_tree\_changed.py       |       56 |        9 |     84% |116-117, 135-136, 138, 160-161, 167, 219 |
| factory/chain/gates/smoke\_green.py                    |       12 |        0 |    100% |           |
| factory/chain/gates/tests\_green.py                    |       38 |       10 |     74% |47-63, 122, 143 |
| factory/chain/gates/tests\_meaningful.py               |       13 |        0 |    100% |           |
| factory/chain/handlers.py                              |     1483 |      238 |     84% |153-154, 188-189, 377-378, 456-470, 477-478, 504-505, 517-528, 550-551, 558-570, 662-663, 667-668, 805-808, 810-813, 817-818, 860, 1013, 1147, 1169-1171, 1185-1186, 1395, 1505-1511, 1547-1548, 1579-1580, 1584-1586, 1750, 1772, 1779, 1787-1788, 1790-1793, 1853-1854, 1864-1871, 1873-1881, 2073-2075, 2147-2149, 2174-2175, 2202, 2232, 2248-2251, 2295-2296, 2304, 2310, 2362-2363, 2497, 2501-2502, 2550, 2563-2564, 2566-2577, 2611, 2668-2669, 2686-2687, 2689, 2710-2711, 2718, 2817-2818, 2829-2830, 2852-2853, 2855, 2864, 2894-2895, 2902, 2915-2916, 2918, 3095, 3099-3100, 3190-3194, 3307-3313, 3353-3354, 3365, 3435-3436, 3498-3502, 3520-3523, 3650-3651, 3934-3938, 4032-4033, 4079-4083, 4101-4103, 4132-4165, 4215-4216, 4249-4250, 4255, 4288-4289, 4326-4327, 4444-4445, 4451, 4471, 4474-4475, 4480, 4536-4537, 4577-4585, 4637-4638, 4706-4707, 4709-4710, 4723-4724, 4728-4747, 4845-4846, 4972-4980 |
| factory/chain/idle\_ping.py                            |       98 |        8 |     92% |153-154, 162-163, 185-186, 214-215 |
| factory/chain/issue\_intake.py                         |       46 |        5 |     89% |55, 89-90, 92-93 |
| factory/chain/mutation.py                              |      570 |      100 |     82% |263-264, 305, 327, 334, 350, 359, 387, 407, 409, 420, 422-428, 448, 464, 467-469, 530-531, 541, 556, 559-560, 609, 617-621, 641-642, 671-672, 710-716, 735-747, 792, 796, 798, 813, 853-854, 894, 903, 959-964, 969-972, 999-1000, 1034, 1078, 1087, 1095, 1208-1209, 1213, 1270-1271, 1275-1276, 1280-1281, 1287-1288, 1348-1349, 1356-1357, 1366-1367, 1373-1374, 1377-1380 |
| factory/chain/oracle\_probe.py                         |       74 |       74 |      0% |    39-152 |
| factory/chain/oracle\_run.py                           |      141 |       23 |     84% |115-116, 125, 128-129, 163-164, 195-196, 213-214, 218, 227, 261, 289-298, 323 |
| factory/chain/orchestrator.py                          |     1000 |      193 |     81% |378, 544, 639, 651, 763, 770, 775, 778-779, 797, 894, 899-900, 903, 907-908, 1115-1116, 1291-1320, 1331-1356, 1430, 1441, 1485-1513, 1548-1549, 1565-1566, 1584, 1600, 1614, 1623-1624, 1671, 1679-1680, 1692-1693, 1702, 1708-1709, 1754-1756, 1761, 1844-1845, 1887, 1936-1946, 2037, 2059, 2110-2111, 2117-2118, 2153-2154, 2159-2160, 2218-2219, 2228-2229, 2280-2283, 2296, 2303-2324, 2342-2343, 2362-2363, 2385-2387, 2399-2401, 2413-2415, 2440-2447, 2452-2454, 2462-2464, 2474-2475, 2493-2498, 2513-2514, 2536-2540, 2550-2551, 2590-2597, 2617-2618, 2797, 2921-2931, 2976-2977, 3140-3144, 3159-3162, 3178-3181, 3208-3209, 3229-3239, 3242-3244, 3265-3266 |
| factory/chain/pm\_sync.py                              |      261 |       42 |     84% |173-174, 176-177, 179-181, 199, 208, 239, 437, 469, 510-514, 518, 574, 590-612, 628-647, 663, 670, 680-682, 705-706, 717, 729-731, 809-810, 812, 822-823, 843 |
| factory/chain/red\_green.py                            |      342 |       42 |     88% |335-336, 375, 414, 423, 439, 446, 474-476, 518-520, 526-532, 629-633, 636, 638-640, 645-646, 666-667, 717, 755, 758-759, 779, 785, 792-793, 831, 846-847 |
| factory/chain/scheduled\_tasks.py                      |      305 |       38 |     88% |178, 187-190, 291, 321-322, 354, 555-557, 572, 577, 586-588, 655-656, 679, 683, 686, 691-692, 720-721, 723-724, 796, 806, 809-810, 874-880 |
| factory/chain/security.py                              |        7 |        7 |      0% |     11-46 |
| factory/chain/slop\_detector.py                        |      301 |       33 |     89% |113, 137-140, 166, 168, 185, 193, 208, 214, 233, 288-289, 319, 330, 361-376, 391, 400, 551, 609, 617-618, 621 |
| factory/chain/state\_machine.py                        |      123 |        0 |    100% |           |
| factory/chain/step\_events.py                          |       59 |        7 |     88% |127-128, 157, 160-161, 168-169 |
| factory/chain/stub\_server.py                          |      106 |       16 |     85% |93-94, 101-111, 129-130, 186 |
| factory/chain/ux\_auditor.py                           |        7 |        7 |      0% |     14-49 |
| factory/chain/worktree.py                              |      123 |       25 |     80% |115-116, 162-163, 168, 197, 200-202, 260, 263-269, 290, 307-308, 331, 335, 344-345, 353, 355-356 |
| factory/cli.py                                         |     1635 |      804 |     51% |48-49, 64, 92-144, 164-175, 200-205, 213-219, 228-249, 266-299, 314, 333-334, 398-399, 408-410, 438-442, 445-449, 510-511, 528-529, 545-546, 549-553, 602, 646, 686-722, 731-777, 802-841, 850-862, 891-892, 916-922, 939-940, 945, 972-995, 1012-1024, 1033-1035, 1044-1051, 1076-1098, 1134, 1136, 1138-1143, 1152-1164, 1166, 1174-1175, 1183, 1213-1228, 1252, 1378-1379, 1421-1422, 1424-1435, 1444, 1474-1475, 1477, 1492-1493, 1495-1496, 1498, 1523-1531, 1533, 1547-1548, 1580-1581, 1583, 1595-1636, 1665-1687, 1704-1713, 1744-1768, 1785-1803, 1814-1829, 1856-1857, 1978-1979, 2031, 2039, 2088-2092, 2132-2172, 2178-2183, 2207-2224, 2244-2320, 2324-2359, 2378-2388, 2410-2421, 2454, 2479, 2511, 2577-2609, 2720, 2724-2732, 2850-2906, 2919-2946, 2964-2967, 2984, 2987, 3016, 3050-3051, 3082-3088, 3103-3126, 3149, 3152-3156, 3177-3184, 3188-3190, 3199-3200, 3206-3207, 3211, 3214-3215, 3220-3222, 3228-3229, 3271-3291, 3313-3331, 3344-3370, 3410-3468, 3497-3498, 3571-3611, 3640-3708, 3739-3826 |
| factory/context/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/context/canonical\_paths.py                    |       36 |        2 |     94% |     90-91 |
| factory/context/enforcer.py                            |       49 |        0 |    100% |           |
| factory/context/loader.py                              |       87 |        5 |     94% |97, 101-102, 106, 179 |
| factory/context/navigator.py                           |       39 |        2 |     95% |     65-66 |
| factory/context/updater.py                             |       29 |        1 |     97% |        77 |
| factory/deploy/\_\_init\_\_.py                         |        4 |        0 |    100% |           |
| factory/deploy/models.py                               |       28 |        0 |    100% |           |
| factory/deploy/orchestrator.py                         |      284 |       34 |     88% |259, 261-264, 267-269, 318, 404-407, 433-443, 488-492, 534-538, 557-558, 563, 580, 591, 598, 706-707 |
| factory/deploy/runner.py                               |       56 |        0 |    100% |           |
| factory/diff\_paths.py                                 |       43 |        0 |    100% |           |
| factory/directions/\_\_init\_\_.py                     |        0 |        0 |    100% |           |
| factory/directions/approval.py                         |       73 |        4 |     95% |101, 133, 173, 185 |
| factory/directions/backfill.py                         |      172 |        9 |     95% |104, 108, 118-119, 121, 137, 168, 175, 373 |
| factory/directions/creator.py                          |      154 |       69 |     55% |126, 156, 163, 198, 227-235, 245-356 |
| factory/directions/gc.py                               |       74 |        9 |     88% |66, 70, 86-87, 89, 158-159, 204-205 |
| factory/directions/ingester.py                         |       77 |        2 |     97% |   55, 131 |
| factory/directions/parser.py                           |      252 |       22 |     91% |58, 122, 170, 180-181, 195, 223-225, 280, 286-287, 291, 313, 319, 329, 355, 368, 380, 405, 418-420 |
| factory/directions/schema.py                           |       56 |        1 |     98% |       159 |
| factory/directions/tracker\_backfill.py                |       74 |        5 |     93% |110-111, 113, 135-136 |
| factory/directions/tracker\_issue.py                   |      360 |       42 |     88% |79-81, 127, 133, 137, 186-187, 218, 222-223, 271, 288-292, 386-387, 451, 474, 482-484, 491-492, 495, 499-501, 630, 637, 652, 659-660, 752-754, 769, 783-784, 872 |
| factory/directions/watcher.py                          |      130 |       28 |     78% |105, 116-117, 208, 257-258, 270, 272-273, 293-295, 305-315, 320-325 |
| factory/events/\_\_init\_\_.py                         |        1 |        0 |    100% |           |
| factory/events/rotation.py                             |       78 |       16 |     79% |62-63, 67-69, 96-98, 113, 116-117, 123-124, 144, 163-164 |
| factory/git\_state.py                                  |       41 |        2 |     95% |    47, 60 |
| factory/manager/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/manager/circuit\_breaker.py                    |      187 |       36 |     81% |132-133, 155, 160-163, 184-186, 201-203, 262-265, 273-278, 354-357, 378-382, 436-439, 443, 446, 473-474, 568-573 |
| factory/manager/detectors/\_\_init\_\_.py              |       17 |        0 |    100% |           |
| factory/manager/detectors/conformance\_breach.py       |       24 |        6 |     75% |60-61, 65-66, 79-80 |
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
| factory/providers/azure\_foundry.py                    |       40 |        0 |    100% |           |
| factory/providers/github.py                            |       23 |        2 |     91% |     79-81 |
| factory/runner.py                                      |      907 |      136 |     85% |164-165, 245-246, 315-316, 369-370, 380-381, 385-386, 412-415, 467-468, 511, 518-519, 758-759, 785-786, 850, 862, 888, 926, 960-961, 963-968, 987-988, 991-997, 1018, 1083-1084, 1131-1132, 1148, 1151, 1153, 1158-1159, 1167-1182, 1193-1199, 1215-1216, 1222, 1227-1238, 1247-1257, 1262, 1265, 1304, 1319, 1356-1357, 1362-1374, 1456, 1458-1462, 1766, 1768, 1883-1888, 1909, 1968, 2351, 2379-2380, 2388-2392, 2470, 2493-2494, 2497-2498 |
| factory/runtime\_state.py                              |       51 |        0 |    100% |           |
| factory/scheduler/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/scheduler/cron.py                              |      132 |       11 |     92% |112, 117, 119, 166-170, 206, 348-349 |
| factory/settings/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/settings/audit.py                              |      124 |        5 |     96% |129-130, 132, 161-162 |
| factory/settings/enforcer.py                           |       54 |        0 |    100% |           |
| factory/settings/loader.py                             |       89 |        0 |    100% |           |
| factory/settings/modes.py                              |       40 |        1 |     98% |        67 |
| factory/settings/spend.py                              |       96 |       25 |     74% |56-57, 87, 108-109, 123, 150-163, 182-188 |
| factory/testing/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/testing/flake.py                               |      124 |       24 |     81% |91, 121-149, 236-237, 239, 255, 282-283, 335-336, 339 |
| factory/tui/\_\_init\_\_.py                            |        2 |        0 |    100% |           |
| factory/tui/app.py                                     |      183 |      151 |     17% |48-57, 61, 66-74, 78, 87-121, 130-161, 166-232, 241-250, 254-274, 278-312, 316-339, 372-377, 380-388, 391-406, 409-415, 418-442, 454-461 |
| factory/webhook/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/webhook/github.py                              |      186 |       40 |     78% |56, 60, 63-64, 96, 126, 162-167, 191-207, 252, 298-302, 345-346, 369-381, 385 |
| factory/webhook/openhands\_events.py                   |       36 |        7 |     81% |69, 84-123 |
| **TOTAL**                                              | **18130** | **3258** | **82%** |           |


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