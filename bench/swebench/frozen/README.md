# Frozen records — do not edit anything in this directory

Every file here is a **point-in-time record**. It was written either before the
data existed (a pre-registration) or from the data as it stood on a stated date.
Editing one destroys the only thing it is for.

## The rule

> **If a file in here is wrong, superseded, or embarrassing, it stays as written.
> Record the correction somewhere else and link back.**

A pre-registration whose predictions failed is doing its job. A results table that
a later campaign overturned is evidence of what was believed and when. Both become
worthless the moment they can be quietly revised, because then no reader can tell
whether they were edited after the fact.

## What is in here

| file | what it fixed, and when |
|---|---|
| `PRE-REGISTRATION-1.6.md` | the five arms, five tables and decision rules, fixed before the data existed |
| `PRE-REGISTRATION-2026-08-10.md` | the 2026-08-10 sweep design |
| `PRE-REGISTRATION-2026-08-11-REPLAY.md` | the factory-replay design |
| `PRE-REGISTRATION-B1.md` | the B.1 design |
| `RESULTS-B1-PHASE1A.md` | B.1 Phase 1a results, 2026-08-05. Its own header states nothing was edited after the data existed |

## Deliberately NOT in here

**`../results.md` is machine-written**, not hand-authored — `swebench_adapter.py`
rewrites it at a fixed path and `report --check` asserts it is still byte-for-byte
re-derivable from the store. It is immutable in the same spirit but must stay where
the code writes it. Do not hand-edit it either; regenerate with `report`.

`../../reviewer-replay/PRE-REGISTRATION-A4.md` and `RESULTS-A4.md` follow the same
rule in place, because `reviewer-replay/replay.py` reads its pinned constants from
that directory.

## Where the current picture lives

* **Our measured results, all campaigns** — `sssf/ai_docs/research/EXPERIMENTS.md`
  (the single owner of our own numbers)
* **What we believe now** — `sssf/ai_docs/research/CURRENT-UNDERSTANDING.md`
* **The store's schema and how to query it** — `../BENCHMARK-RECORDS.md`
* **How to run a sweep** — `../README.md`
