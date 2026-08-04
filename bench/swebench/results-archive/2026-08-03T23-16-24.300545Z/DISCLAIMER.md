> ## SUPERSEDED — do not quote these numbers
>
> This is an **intermediate report of the five-arm sweep**, generated before the
> sweep's audits were re-run under the fixed retrieval detector. The rows are kept
> as evidence of the sweep's raw output. They are **not** the result.
>
> **The result of record is
> `results-archive/2026-08-04T04-18-05.349995Z/`**, published as
> `bench/swebench/results.md` and verifiable with
> `report --from-archive … --check`.
>
> Why this snapshot is not it:
>
> 1. **The audits are pre-#227.** The retrieval detector matched hostnames the
>    arms merely *read* (`ObservationEvent` text) as well as hostnames they
>    *fetched*. It flagged 218 lines across 46 rows, every one a false positive.
>    That is why this table shows arms at absurd denominators — `claude` 16/18,
>    `claude-4.8` **8/9** with 10 invalid rows — instead of the true 19/19
>    audited-valid. The 04-18 report re-audited all 95 rows under the fixed
>    detector, uniformly and with no arm re-run, and found **one** genuine
>    violation (`bare` on `hiero…-1914_interface`, a real `curl` of upstream
>    source).
> 2. **It carries a sixth pseudo-arm.** `claude` (the back-compatible run key on
>    the CLI's default model) is here beside `claude-5`, which superseded it. The
>    04-18 report excludes it explicitly as a superseded run key rather than
>    double-counting one (harness, model) pair.
>
> Correct headline, from the 04-18 archive: `claude-opus-5` **15/19 = 79%**
> [54%, 94%] · `claude-opus-4-8` **14/19 = 74%** [49%, 91%] · openhands
> **7/16 = 44%** [20%, 70%] · factory **7/19 = 37%** [16%, 62%] · bare
> **1/18 = 6%** [0%, 27%]. The chain shows no measurable lift over one OpenHands
> agent (p=0.625).
>
> This archive is committed because it holds all five `sweep-<arm>.json` files,
> which the 04-18 archive does not (`PLAN.md` 1.6 G).
