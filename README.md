# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/xvanov/software-factory/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                   |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------- | -------: | -------: | ------: | --------: |
| factory/\_\_init\_\_.py                                |        2 |        0 |    100% |           |
| factory/app\_config.py                                 |       97 |        5 |     95% |290, 294, 309, 327, 343 |
| factory/artifacts/\_\_init\_\_.py                      |        0 |        0 |    100% |           |
| factory/backpressure/\_\_init\_\_.py                   |        0 |        0 |    100% |           |
| factory/backpressure/parser.py                         |       67 |        5 |     93% |103-104, 128, 132-133 |
| factory/backpressure/vacuity.py                        |      109 |        5 |     95% |511, 520, 534-541 |
| factory/backpressure/validator.py                      |      101 |        7 |     93% |60-61, 80, 147-153, 156 |
| factory/chain/\_\_init\_\_.py                          |        2 |        0 |    100% |           |
| factory/chain/acceptance.py                            |      398 |       57 |     86% |197-198, 292, 300, 302, 307-308, 332-333, 339-342, 442, 444, 475-505, 547, 595-596, 643, 651, 656, 695-696, 719, 730-731, 738, 812-819, 977-978, 1017, 1024-1025, 1029-1030, 1042-1043, 1058, 1075-1076, 1095-1096 |
| factory/chain/auto\_merge.py                           |      784 |      117 |     85% |227, 637-638, 685-687, 689, 691, 695-696, 863-864, 866, 903, 920, 1029-1030, 1045-1046, 1134-1135, 1342, 1447-1448, 1663-1664, 1691, 1706-1707, 1832-1833, 1843, 1861-1862, 1864, 1867-1868, 1876, 1907-1908, 1910, 1935, 1937, 1946-1947, 1958-1959, 1982, 2024, 2027-2028, 2030, 2038, 2067-2068, 2072-2073, 2093-2094, 2097, 2169, 2183-2184, 2227-2228, 2236-2237, 2246-2247, 2256-2257, 2329-2330, 2400, 2554, 2573-2574, 2649-2650, 2705, 2730-2782, 2960-2961, 2984-2985, 3004-3008, 3029-3037, 3055-3059, 3110-3111, 3147-3150, 3174-3175, 3197-3198, 3209-3210, 3249-3250 |
| factory/chain/boot.py                                  |      249 |       49 |     80% |69-75, 131-132, 134, 165-166, 197-198, 239, 270-273, 275-283, 304, 313-317, 388, 390, 395-396, 463-465, 472-475, 481-482, 508, 511 |
| factory/chain/branch.py                                |       56 |        4 |     93% |   163-166 |
| factory/chain/ci\_health.py                            |      197 |       28 |     86% |113-114, 131, 134, 178, 181, 201, 210, 217, 251, 264, 326, 330, 339, 343-344, 421-422, 430-431, 449-450, 468-469, 494-495, 505-506 |
| factory/chain/context\_refresh.py                      |      179 |       40 |     78% |123-130, 211, 222-248, 277-290, 360-369, 411, 442, 477, 524-526, 541-543, 545-548, 553-556, 564-565, 567, 571-572 |
| factory/chain/contract.py                              |       88 |        1 |     99% |       302 |
| factory/chain/detector\_watch.py                       |      374 |       73 |     80% |254, 257, 266-267, 269, 321, 356, 372-373, 408-415, 425-430, 446-453, 480-485, 488-490, 542, 570, 574-576, 595-610, 717-718, 799, 802, 819-820, 835-836, 838, 845, 1020, 1073-1075 |
| factory/chain/dual\_draft.py                           |      150 |       15 |     90% |64-65, 197, 228, 230, 234, 384, 402-403, 445-446, 477-478, 480-481 |
| factory/chain/event\_log.py                            |       55 |        3 |     95% |122, 132-133 |
| factory/chain/factory\_status.py                       |      144 |        8 |     94% |88-89, 121-122, 124, 267, 289-291 |
| factory/chain/gates/\_\_init\_\_.py                    |        3 |        0 |    100% |           |
| factory/chain/gates/acceptance\_verified.py            |      390 |       38 |     90% |323, 333-334, 339, 363-364, 435, 452, 467-468, 681, 690, 698, 732, 778, 804, 814, 851, 898, 905, 918, 933, 959, 970, 996, 1077, 1097, 1224-1226, 1232-1237, 1248, 1251-1252, 1259-1260 |
| factory/chain/gates/canonical\_paths\_only.py          |       12 |        0 |    100% |           |
| factory/chain/gates/docs\_current.py                   |       27 |        3 |     89% | 31, 36-37 |
| factory/chain/gates/evaluator.py                       |       55 |        4 |     93% |   172-177 |
| factory/chain/gates/production\_tree\_changed.py       |       56 |        9 |     84% |116-117, 135-136, 138, 160-161, 167, 219 |
| factory/chain/gates/smoke\_green.py                    |       12 |        0 |    100% |           |
| factory/chain/gates/tests\_green.py                    |       38 |       10 |     74% |47-63, 122, 143 |
| factory/chain/gates/tests\_meaningful.py               |       13 |        0 |    100% |           |
| factory/chain/handlers.py                              |     1623 |      252 |     84% |155-156, 190-191, 398-399, 477-491, 498-499, 525-526, 538-549, 666-667, 701-702, 733-734, 741-753, 845-846, 850-851, 1076-1079, 1081-1084, 1088-1089, 1149, 1231-1259, 1338, 1396, 1412-1413, 1421, 1423, 1532, 1554-1556, 1570-1571, 1842, 1952-1958, 1994-1995, 2026-2027, 2031-2033, 2197, 2219, 2226, 2234-2235, 2237-2240, 2300-2301, 2311-2318, 2320-2328, 2520-2522, 2594-2596, 2621-2622, 2649, 2679, 2695-2698, 2742-2743, 2751, 2757, 2809-2810, 2944, 2948-2949, 2997, 3010-3011, 3013-3024, 3058, 3115-3116, 3133-3134, 3136, 3157-3158, 3165, 3264-3265, 3276-3277, 3299-3300, 3302, 3311, 3341-3342, 3349, 3362-3363, 3365, 3542, 3546-3547, 3637-3641, 3754-3760, 3800-3801, 3812, 3882-3883, 3945-3949, 3967-3970, 4428-4432, 4532-4533, 4579-4583, 4676-4709, 4759-4760, 4793-4794, 4799, 4832-4833, 4870-4871, 4988-4989, 4995, 5015, 5018-5019, 5024, 5080-5081, 5121-5129, 5181-5182, 5250-5251, 5253-5254, 5267-5268, 5272-5291, 5389-5390, 5516-5524 |
| factory/chain/idle\_ping.py                            |      101 |        8 |     92% |191-192, 200-201, 223-224, 252-253 |
| factory/chain/issue\_intake.py                         |       46 |        5 |     89% |55, 89-90, 92-93 |
| factory/chain/mutation.py                              |      570 |      100 |     82% |263-264, 305, 327, 334, 350, 359, 387, 407, 409, 420, 422-428, 448, 464, 467-469, 530-531, 541, 556, 559-560, 609, 617-621, 641-642, 671-672, 710-716, 735-747, 792, 796, 798, 813, 853-854, 894, 903, 959-964, 969-972, 999-1000, 1034, 1078, 1087, 1095, 1208-1209, 1213, 1270-1271, 1275-1276, 1280-1281, 1287-1288, 1348-1349, 1356-1357, 1366-1367, 1373-1374, 1377-1380 |
| factory/chain/oracle\_probe.py                         |       74 |       74 |      0% |    39-152 |
| factory/chain/oracle\_run.py                           |      141 |       23 |     84% |115-116, 125, 128-129, 163-164, 195-196, 213-214, 218, 227, 261, 289-298, 323 |
| factory/chain/orchestrator.py                          |     1034 |      184 |     82% |395, 586, 692, 704, 816, 823, 828, 831-832, 850, 947, 952-953, 956, 960-961, 1168-1169, 1344-1373, 1384-1409, 1483, 1494, 1538-1566, 1601-1602, 1618-1619, 1637, 1653, 1667, 1676-1677, 1724, 1732-1733, 1745-1746, 1755, 1761-1762, 1807-1809, 1814, 1897-1898, 1940, 1989-1999, 2090, 2112, 2163-2164, 2170-2171, 2206-2207, 2212-2213, 2271-2272, 2281-2282, 2333-2336, 2349, 2356-2377, 2395-2396, 2430-2431, 2453-2455, 2467-2469, 2481-2483, 2512-2519, 2524-2526, 2534-2536, 2546-2547, 2565-2570, 2585-2586, 2608-2612, 2622-2623, 2668-2669, 2693-2694, 2873, 2997-3007, 3052-3053, 3265-3268, 3318-3322, 3399-3401, 3422-3423 |
| factory/chain/pm\_sync.py                              |      261 |       42 |     84% |173-174, 176-177, 179-181, 199, 208, 239, 437, 469, 510-514, 518, 574, 590-612, 628-647, 663, 670, 680-682, 705-706, 717, 729-731, 809-810, 812, 822-823, 843 |
| factory/chain/red\_green.py                            |      342 |       42 |     88% |335-336, 375, 414, 423, 439, 446, 474-476, 518-520, 526-532, 629-633, 636, 638-640, 645-646, 666-667, 717, 755, 758-759, 779, 785, 792-793, 831, 846-847 |
| factory/chain/resume.py                                |      176 |       31 |     82% |186-199, 209-223, 303, 312-314, 334, 339, 361, 374, 377, 407-408, 463-467 |
| factory/chain/route\_table.py                          |       51 |        9 |     82% |66, 84, 86, 90-91, 93, 112-113, 126 |
| factory/chain/scheduled\_tasks.py                      |      305 |       38 |     88% |178, 187-190, 291, 321-322, 354, 555-557, 572, 577, 586-588, 655-656, 679, 683, 686, 691-692, 720-721, 723-724, 796, 806, 809-810, 874-880 |
| factory/chain/security.py                              |        7 |        7 |      0% |     11-46 |
| factory/chain/slop\_detector.py                        |      301 |       33 |     89% |113, 137-140, 166, 168, 185, 193, 208, 214, 233, 288-289, 319, 330, 361-376, 391, 400, 551, 609, 617-618, 621 |
| factory/chain/state\_machine.py                        |      125 |        0 |    100% |           |
| factory/chain/step\_events.py                          |       59 |        7 |     88% |127-128, 157, 160-161, 168-169 |
| factory/chain/stub\_server.py                          |      106 |       16 |     85% |93-94, 101-111, 129-130, 186 |
| factory/chain/ux\_auditor.py                           |        7 |        7 |      0% |     14-49 |
| factory/chain/worktree.py                              |      123 |       24 |     80% |115-116, 162-163, 168, 197, 200-202, 260, 263-269, 290, 307-308, 335, 344-345, 353, 355-356 |
| factory/cli.py                                         |     1767 |      868 |     51% |48-49, 64, 92-144, 164-175, 200-205, 213-219, 228-249, 266-299, 314, 333-334, 398-399, 408-410, 438-442, 445-449, 510-511, 528-529, 545-546, 549-553, 602, 634-693, 740, 780-816, 825-871, 896-935, 944-956, 985-986, 1010-1016, 1033-1034, 1039, 1066-1089, 1106-1118, 1127-1129, 1138-1145, 1170-1192, 1228, 1230, 1232-1237, 1246-1258, 1260, 1268-1269, 1277, 1282-1283, 1291-1292, 1323-1338, 1362, 1497-1498, 1540-1541, 1543-1554, 1563, 1593-1594, 1596, 1611-1612, 1614-1615, 1617, 1642-1650, 1652, 1666-1667, 1749-1750, 1752, 1764-1805, 1859-1870, 1909-1912, 1935-1944, 1975-1999, 2016-2034, 2045-2060, 2242-2243, 2263-2319, 2363-2364, 2416, 2424, 2473-2477, 2493, 2534-2574, 2580-2585, 2609-2626, 2646-2722, 2726-2761, 2780-2790, 2812-2823, 2856, 2881, 2913, 2979-3011, 3122, 3126-3134, 3252-3308, 3321-3348, 3366-3369, 3386, 3389, 3418, 3452-3453, 3484-3490, 3505-3528, 3551, 3554-3558, 3579-3586, 3590-3592, 3601-3602, 3608-3609, 3613, 3616-3617, 3622-3624, 3630-3631, 3673-3693, 3762-3763, 3777-3803, 3843-3901, 3930-3931, 4004-4044, 4073-4141, 4172-4259 |
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
| factory/runner.py                                      |      960 |      137 |     86% |164-165, 245-246, 315-316, 369-370, 380-381, 385-386, 412-415, 467-468, 511, 518-519, 758-759, 785-786, 850, 862, 888, 926, 960-961, 963-968, 987-988, 991-997, 1018, 1147-1148, 1164, 1167, 1169, 1183-1198, 1221, 1237-1243, 1259-1260, 1266, 1271-1282, 1291-1301, 1306, 1309, 1348, 1363, 1439-1440, 1448-1460, 1545, 1547-1551, 1863, 1865, 1980-1985, 2006, 2065, 2123, 2161, 2164-2165, 2547, 2575-2576, 2584-2588, 2666, 2689-2690, 2693-2694 |
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
| **TOTAL**                                              | **18910** | **3371** | **82%** |           |


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