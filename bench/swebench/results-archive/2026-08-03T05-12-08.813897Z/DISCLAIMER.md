> ## RETRACTED — do not quote these numbers
>
> This run's rows are kept as evidence and as the regression corpus for the
> report code. They are **not** a result, for reasons that are properties of the
> run, not of the table:
>
> 1. **The prompt was not matched.** The factory, openhands and claude arms were
>    told to run a test command over the `FAIL_TO_PASS` files at `base_commit`
>    without being told those tests already pass there and do not cover the task.
>    16 of 19 instances contain zero of the relevant test functions. Only the
>    bare arm had the honest note (#223). Every arm has it as of 2026-08-03, which
>    makes the five-arm re-run a **fresh baseline**, not a before/after.
> 2. **No `openhands` arm ran.** `factory − bare` varies the chain AND the
>    tooling at once, so the headline could not be attributed to either. The
>    product claim is `factory − openhands`, and that number does not exist here.
> 3. **The published table was not this table.** It reported 16/18 for the claude
>    arm because it excluded a row that hit its turn cap and PASSED the oracle,
>    while `sweep-claude.json` said 17 — two classifiers, two denominators. It
>    mixed fresh and cached input tokens into one column (cache share ranged
>    0%-97%). It named excluded passes but not excluded failures. It printed
>    "claude recall 0/16 = 0%" for an arm with no chain verdict. It disclosed no
>    attempt counts and no contamination margins.
>
> What the rows below ARE good for: they are the fixture the honest-column fixes
> are tested against, and the reason each column exists is a defect visible in
> them.
