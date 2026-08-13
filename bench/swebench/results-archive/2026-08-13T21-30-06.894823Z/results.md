# evidence snapshot — NOT a report

Archived at 2026-08-13T21:30:06.894823+00:00 by `archive` (not by `report`), so no table was rendered and `bench/swebench/results.md` was left untouched.

* rows: 1
* arms: full-sdlc
* manifest_sha256: 923aef05add32124
* source: /home/k/software-factory/bench/swebench/runs

Reason this is not a report: `runs/` is gitignored scratch that the next sweep deletes, and the benchmark store holds artifact digests pointing into it, so the evidence had to be captured NOW. The arms in it are not all measured to the same coverage, and rendering one table over rows with 8-row and 18-row denominators would mix accounting bases. Run `report` when the coverage supports a published table; `report --from-archive results-archive/<stamp>` re-derives a table from this snapshot at any time without publishing it.

Operator note: full SDLC end-to-end verification on DeepSeek-V4-Flash: all 13 phases, resolved
