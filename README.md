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
| factory/chain/auto\_merge.py                           |      780 |      117 |     85% |227, 637-638, 685-687, 689, 691, 695-696, 863-864, 866, 903, 920, 1010-1011, 1026-1027, 1115-1116, 1323, 1428-1429, 1644-1645, 1672, 1687-1688, 1813-1814, 1824, 1842-1843, 1845, 1848-1849, 1857, 1888-1889, 1891, 1916, 1918, 1927-1928, 1939-1940, 1963, 2005, 2008-2009, 2011, 2019, 2048-2049, 2053-2054, 2074-2075, 2078, 2150, 2164-2165, 2208-2209, 2217-2218, 2227-2228, 2237-2238, 2310-2311, 2381, 2535, 2554-2555, 2630-2631, 2686, 2711-2763, 2941-2942, 2965-2966, 2985-2989, 3010-3018, 3036-3040, 3091-3092, 3128-3131, 3155-3156, 3178-3179, 3190-3191, 3230-3231 |
| factory/chain/boot.py                                  |      249 |       49 |     80% |69-75, 131-132, 134, 165-166, 197-198, 239, 270-273, 275-283, 304, 313-317, 388, 390, 395-396, 463-465, 472-475, 481-482, 508, 511 |
| factory/chain/branch.py                                |       56 |        4 |     93% |   163-166 |
| factory/chain/ci\_health.py                            |      197 |       28 |     86% |113-114, 131, 134, 178, 181, 201, 210, 217, 251, 264, 326, 330, 339, 343-344, 421-422, 430-431, 449-450, 468-469, 494-495, 505-506 |
| factory/chain/context\_refresh.py                      |      179 |       40 |     78% |123-130, 211, 222-248, 277-290, 360-369, 411, 442, 477, 524-526, 541-543, 545-548, 553-556, 564-565, 567, 571-572 |
| factory/chain/contract.py                              |       87 |        2 |     98% |  143, 302 |
| factory/chain/detector\_watch.py                       |      374 |       73 |     80% |254, 257, 266-267, 269, 321, 356, 372-373, 408-415, 425-430, 446-453, 480-485, 488-490, 542, 570, 574-576, 595-610, 717-718, 799, 802, 819-820, 835-836, 838, 845, 1020, 1073-1075 |
| factory/chain/dual\_draft.py                           |      150 |       15 |     90% |64-65, 197, 228, 230, 234, 384, 402-403, 445-446, 477-478, 480-481 |
| factory/chain/event\_log.py                            |       55 |        3 |     95% |122, 132-133 |
| factory/chain/factory\_status.py                       |      144 |        8 |     94% |88-89, 121-122, 124, 267, 289-291 |
| factory/chain/gates/\_\_init\_\_.py                    |        3 |        0 |    100% |           |
| factory/chain/gates/acceptance\_verified.py            |      368 |       35 |     90% |290, 300-301, 306, 330-331, 402, 596, 605, 613, 647, 693, 719, 729, 765, 812, 819, 832, 847, 873, 884, 910, 990, 1009, 1136-1138, 1144-1149, 1160, 1163-1164, 1171-1172 |
| factory/chain/gates/canonical\_paths\_only.py          |       12 |        0 |    100% |           |
| factory/chain/gates/docs\_current.py                   |       27 |        3 |     89% | 31, 36-37 |
| factory/chain/gates/evaluator.py                       |       55 |        4 |     93% |   172-177 |
| factory/chain/gates/production\_tree\_changed.py       |       56 |        9 |     84% |116-117, 135-136, 138, 160-161, 167, 219 |
| factory/chain/gates/smoke\_green.py                    |       12 |        0 |    100% |           |
| factory/chain/gates/tests\_green.py                    |       38 |       10 |     74% |47-63, 122, 143 |
| factory/chain/gates/tests\_meaningful.py               |       13 |        0 |    100% |           |
| factory/chain/handlers.py                              |     1524 |      233 |     85% |154-155, 189-190, 381-382, 460-474, 481-482, 508-509, 521-532, 554-555, 562-574, 666-667, 671-672, 874-877, 879-882, 886-887, 944, 1100, 1234, 1256-1258, 1272-1273, 1482, 1592-1598, 1634-1635, 1666-1667, 1671-1673, 1837, 1859, 1866, 1874-1875, 1877-1880, 1940-1941, 1951-1958, 1960-1968, 2160-2162, 2234-2236, 2261-2262, 2289, 2319, 2335-2338, 2382-2383, 2391, 2397, 2449-2450, 2584, 2588-2589, 2637, 2650-2651, 2653-2664, 2698, 2755-2756, 2773-2774, 2776, 2797-2798, 2805, 2904-2905, 2916-2917, 2939-2940, 2942, 2951, 2981-2982, 2989, 3002-3003, 3005, 3182, 3186-3187, 3277-3281, 3394-3400, 3440-3441, 3452, 3522-3523, 3585-3589, 3607-3610, 4062-4066, 4166-4167, 4213-4217, 4310-4343, 4393-4394, 4427-4428, 4433, 4466-4467, 4504-4505, 4622-4623, 4629, 4649, 4652-4653, 4658, 4714-4715, 4755-4763, 4815-4816, 4884-4885, 4887-4888, 4901-4902, 4906-4925, 5023-5024, 5150-5158 |
| factory/chain/idle\_ping.py                            |      101 |        8 |     92% |191-192, 200-201, 223-224, 252-253 |
| factory/chain/issue\_intake.py                         |       46 |        5 |     89% |55, 89-90, 92-93 |
| factory/chain/mutation.py                              |      570 |      100 |     82% |263-264, 305, 327, 334, 350, 359, 387, 407, 409, 420, 422-428, 448, 464, 467-469, 530-531, 541, 556, 559-560, 609, 617-621, 641-642, 671-672, 710-716, 735-747, 792, 796, 798, 813, 853-854, 894, 903, 959-964, 969-972, 999-1000, 1034, 1078, 1087, 1095, 1208-1209, 1213, 1270-1271, 1275-1276, 1280-1281, 1287-1288, 1348-1349, 1356-1357, 1366-1367, 1373-1374, 1377-1380 |
| factory/chain/oracle\_probe.py                         |       74 |       74 |      0% |    39-152 |
| factory/chain/oracle\_run.py                           |      141 |       23 |     84% |115-116, 125, 128-129, 163-164, 195-196, 213-214, 218, 227, 261, 289-298, 323 |
| factory/chain/orchestrator.py                          |     1034 |      184 |     82% |395, 561, 656, 668, 780, 787, 792, 795-796, 814, 911, 916-917, 920, 924-925, 1132-1133, 1308-1337, 1348-1373, 1447, 1458, 1502-1530, 1565-1566, 1582-1583, 1601, 1617, 1631, 1640-1641, 1688, 1696-1697, 1709-1710, 1719, 1725-1726, 1771-1773, 1778, 1861-1862, 1904, 1953-1963, 2054, 2076, 2127-2128, 2134-2135, 2170-2171, 2176-2177, 2235-2236, 2245-2246, 2297-2300, 2313, 2320-2341, 2359-2360, 2394-2395, 2417-2419, 2431-2433, 2445-2447, 2476-2483, 2488-2490, 2498-2500, 2510-2511, 2529-2534, 2549-2550, 2572-2576, 2586-2587, 2632-2633, 2657-2658, 2837, 2961-2971, 3016-3017, 3229-3232, 3282-3286, 3363-3365, 3386-3387 |
| factory/chain/pm\_sync.py                              |      261 |       42 |     84% |173-174, 176-177, 179-181, 199, 208, 239, 437, 469, 510-514, 518, 574, 590-612, 628-647, 663, 670, 680-682, 705-706, 717, 729-731, 809-810, 812, 822-823, 843 |
| factory/chain/red\_green.py                            |      342 |       42 |     88% |335-336, 375, 414, 423, 439, 446, 474-476, 518-520, 526-532, 629-633, 636, 638-640, 645-646, 666-667, 717, 755, 758-759, 779, 785, 792-793, 831, 846-847 |
| factory/chain/route\_table.py                          |       51 |        9 |     82% |66, 84, 86, 90-91, 93, 112-113, 126 |
| factory/chain/scheduled\_tasks.py                      |      305 |       38 |     88% |178, 187-190, 291, 321-322, 354, 555-557, 572, 577, 586-588, 655-656, 679, 683, 686, 691-692, 720-721, 723-724, 796, 806, 809-810, 874-880 |
| factory/chain/security.py                              |        7 |        7 |      0% |     11-46 |
| factory/chain/slop\_detector.py                        |      301 |       33 |     89% |113, 137-140, 166, 168, 185, 193, 208, 214, 233, 288-289, 319, 330, 361-376, 391, 400, 551, 609, 617-618, 621 |
| factory/chain/state\_machine.py                        |      125 |        0 |    100% |           |
| factory/chain/step\_events.py                          |       59 |        7 |     88% |127-128, 157, 160-161, 168-169 |
| factory/chain/stub\_server.py                          |      106 |       16 |     85% |93-94, 101-111, 129-130, 186 |
| factory/chain/ux\_auditor.py                           |        7 |        7 |      0% |     14-49 |
| factory/chain/worktree.py                              |      123 |       24 |     80% |115-116, 162-163, 168, 197, 200-202, 260, 263-269, 290, 307-308, 335, 344-345, 353, 355-356 |
| factory/cli.py                                         |     1698 |      831 |     51% |48-49, 64, 92-144, 164-175, 200-205, 213-219, 228-249, 266-299, 314, 333-334, 398-399, 408-410, 438-442, 445-449, 510-511, 528-529, 545-546, 549-553, 602, 634-693, 740, 780-816, 825-871, 896-935, 944-956, 985-986, 1010-1016, 1033-1034, 1039, 1066-1089, 1106-1118, 1127-1129, 1138-1145, 1170-1192, 1228, 1230, 1232-1237, 1246-1258, 1260, 1268-1269, 1277, 1282-1283, 1291-1292, 1323-1338, 1362, 1488-1489, 1531-1532, 1534-1545, 1554, 1584-1585, 1587, 1602-1603, 1605-1606, 1608, 1633-1641, 1643, 1657-1658, 1690-1691, 1693, 1705-1746, 1800-1811, 1850-1853, 1876-1885, 1916-1940, 1957-1975, 1986-2001, 2150-2151, 2203, 2211, 2260-2264, 2304-2344, 2350-2355, 2379-2396, 2416-2492, 2496-2531, 2550-2560, 2582-2593, 2626, 2651, 2683, 2749-2781, 2892, 2896-2904, 3022-3078, 3091-3118, 3136-3139, 3156, 3159, 3188, 3222-3223, 3254-3260, 3275-3298, 3321, 3324-3328, 3349-3356, 3360-3362, 3371-3372, 3378-3379, 3383, 3386-3387, 3392-3394, 3400-3401, 3443-3463, 3532-3533, 3547-3573, 3613-3671, 3700-3701, 3774-3814, 3843-3911, 3942-4029 |
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
| factory/directions/parser.py                           |      252 |       20 |     92% |58, 122, 170, 195, 223-225, 280, 286-287, 291, 313, 319, 329, 355, 368, 380, 405, 418-420 |
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
| factory/manager/poison\_escalation.py                  |      109 |       15 |     86% |93-94, 99, 102-103, 173, 181, 183, 315-324, 345-346, 360-361 |
| factory/manager/recovery.py                            |      467 |       62 |     87% |188, 191-192, 194, 234-238, 251, 254, 256, 301-302, 359, 370-371, 417, 422-423, 477, 490-491, 505, 559-560, 571-572, 620, 637-638, 679-680, 683, 817, 827-828, 835, 844-845, 857, 966-967, 986, 989-990, 993-994, 1010, 1031, 1033, 1063-1064, 1134-1135, 1352-1371 |
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
| factory/runner.py                                      |      956 |      137 |     86% |164-165, 245-246, 315-316, 369-370, 380-381, 385-386, 412-415, 467-468, 511, 518-519, 758-759, 785-786, 850, 862, 888, 926, 960-961, 963-968, 987-988, 991-997, 1018, 1147-1148, 1164, 1167, 1169, 1183-1198, 1221, 1237-1243, 1259-1260, 1266, 1271-1282, 1291-1301, 1306, 1309, 1348, 1363, 1400-1401, 1406-1418, 1500, 1502-1506, 1818, 1820, 1935-1940, 1961, 2020, 2078, 2116, 2119-2120, 2502, 2530-2531, 2539-2543, 2621, 2644-2645, 2648-2649 |
| factory/runtime\_state.py                              |       51 |        0 |    100% |           |
| factory/scheduler/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/scheduler/cron.py                              |      132 |       11 |     92% |112, 117, 119, 166-170, 206, 348-349 |
| factory/settings/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| factory/settings/audit.py                              |      124 |        5 |     96% |129-130, 132, 161-162 |
| factory/settings/enforcer.py                           |       54 |        0 |    100% |           |
| factory/settings/loader.py                             |       92 |        0 |    100% |           |
| factory/settings/modes.py                              |       40 |        1 |     98% |        67 |
| factory/settings/spend.py                              |       96 |       25 |     74% |56-57, 87, 108-109, 123, 150-163, 182-188 |
| factory/testing/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/testing/flake.py                               |      124 |       24 |     81% |91, 121-149, 236-237, 239, 255, 282-283, 335-336, 339 |
| factory/tui/\_\_init\_\_.py                            |        2 |        0 |    100% |           |
| factory/tui/app.py                                     |      183 |      151 |     17% |48-57, 61, 66-74, 78, 87-121, 130-161, 166-232, 241-250, 254-274, 278-312, 316-339, 372-377, 380-388, 391-406, 409-415, 418-442, 454-461 |
| factory/webhook/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| factory/webhook/github.py                              |      186 |       40 |     78% |56, 60, 63-64, 96, 126, 162-167, 191-207, 252, 298-302, 345-346, 369-381, 385 |
| factory/webhook/openhands\_events.py                   |       36 |        7 |     81% |69, 84-123 |
| **TOTAL**                                              | **18534** | **3282** | **82%** |           |


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