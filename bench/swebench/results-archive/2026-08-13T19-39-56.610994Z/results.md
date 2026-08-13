# evidence snapshot — NOT a report

Archived at 2026-08-13T19:39:56.610994+00:00 by `archive` (not by `report`), so no table was rendered and `bench/swebench/results.md` was left untouched.

* rows: 17
* arms: chain, v32-solo
* manifest_sha256: 923aef05add32124
* source: /home/k/software-factory/bench/swebench/runs

Reason this is not a report: `runs/` is gitignored scratch that the next sweep deletes, and the benchmark store holds artifact digests pointing into it, so the evidence had to be captured NOW. The arms in it are not all measured to the same coverage, and rendering one table over rows with 8-row and 18-row denominators would mix accounting bases. Run `report` when the coverage supports a published table; `report --from-archive results-archive/<stamp>` re-derives a table from this snapshot at any time without publishing it.

Operator note: Fix 5: bench/swebench/runs/ is gitignored scratch the next sweep deletes, and benchmark_store.py had recorded 1,604 artifact digests pointing into it. Snapshotted before that trail could evaporate. No table published: chain has 8 rows and v32-solo 9 against 18-25 for every published arm.
