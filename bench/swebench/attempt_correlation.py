#!/usr/bin/env python3
"""Attempt-correlation over the archived sweeps — does a second dev attempt fail the same way?

The Phase-C best-of-N bet rests on attempts being decorrelated: if a re-run of a
failed instance fails identically, selection over N attempts buys nothing and the
extra spend is wasted. This measures that from data already on disk, before any
sweep is run.

The natural experiment: `factory` and `solo-noreview` are two runs of the SAME dev
model over the SAME 19 instances in the SAME sweep. Sweep 1's `factory` and
`openhands` add two more samples on the same manifest.

Read-only. Derives everything from results-archive/**/result.json.

    uv run python bench/swebench/attempt_correlation.py
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SWEEP2 = ROOT / "results-archive" / "2026-08-10T21-53-14.959258Z"
SWEEP1 = ROOT / "results-archive" / "2026-08-04T23-19-24.998844Z"

# Every arm below drives the same dev model (azure/deepseek-v4-pro), so each is a
# sample of "what does this model do on this instance". claude-5 is a reference
# point, never part of the union.
SAMPLES = [("fac2", SWEEP2, "factory"), ("solo2", SWEEP2, "solo-noreview"),
           ("fac1", SWEEP1, "factory"), ("oh1", SWEEP1, "openhands")]


def load(archive: pathlib.Path, arm: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not archive.exists():
        return out
    for d in sorted(p for p in archive.iterdir() if p.is_dir()):
        f = d / arm / "result.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text())
        g = r.get("grade") or {}
        out[d.name] = {
            "res": bool(g.get("oracle_resolved")),
            "out": g.get("outcome"),
            "cost": r.get("cost_usd") or 0.0,
        }
    return out


def phi(a: int, b: int, c: int, d: int) -> float:
    """Phi coefficient over the 2x2 agreement table. 1.0 = identical attempts."""
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    return (a * d - b * c) / den if den else float("nan")


def main() -> int:
    arms = {name: load(arch, arm) for name, arch, arm in SAMPLES}
    claude = load(SWEEP2, "claude-5")
    if not arms["fac2"]:
        print(f"no archive at {SWEEP2}", file=sys.stderr)
        return 1
    insts = sorted(arms["fac2"])

    print("=== per-instance: how many deepseek-dev samples solved it ===")
    hard = []
    for i in insts:
        k = sum(1 for s in arms.values() if s.get(i, {}).get("res"))
        n = sum(1 for s in arms.values() if i in s)
        cl = "R" if claude.get(i, {}).get("res") else ("-" if i not in claude else "F")
        if k == 0:
            hard.append(i)
        print(f"  {i:<46} {k}/{n}  claude:{cl}{'   <-- hard core' if k == 0 else ''}")

    # --- pairwise decorrelation, the number the bet rests on -----------------
    f2, s2 = arms["fac2"], arms["solo2"]
    common = [i for i in insts if i in f2 and i in s2]
    both = [i for i in common if f2[i]["res"] and s2[i]["res"]]
    fonly = [i for i in common if f2[i]["res"] and not s2[i]["res"]]
    sonly = [i for i in common if not f2[i]["res"] and s2[i]["res"]]
    neither = [i for i in common if not f2[i]["res"] and not s2[i]["res"]]
    disc = len(fonly) + len(sonly)

    print(f"\n=== factory vs solo-noreview — same dev, same sweep, n={len(common)} ===")
    print(f"  both {len(both)} | factory-only {len(fonly)} | solo-only {len(sonly)} | neither {len(neither)}")
    print(f"  DISCORDANT {disc}/{len(common)} = {100*disc/len(common):.0f}%")
    print(f"  phi = {phi(len(both), len(fonly), len(sonly), len(neither)):.3f}  (1.0 = identical attempts)")
    print(f"  factory-only: {[x.split('__')[-1] for x in fonly]}")
    print(f"  solo-only   : {[x.split('__')[-1] for x in sonly]}")

    # --- union ceilings ------------------------------------------------------
    u2 = [i for i in common if f2[i]["res"] or s2[i]["res"]]
    u4 = [i for i in insts if any(s.get(i, {}).get("res") for s in arms.values())]
    print(f"\n  best-of-2 ceiling (perfect selector): {len(u2)}/{len(common)} = {100*len(u2)/len(common):.0f}%")
    print(f"  best-of-4 ceiling (perfect selector): {len(u4)}/{len(insts)} = {100*len(u4)/len(insts):.0f}%")
    print(f"  hard core, never solved by any arm  : {len(hard)}/{len(insts)}")

    # --- cost model on measured per-instance dev cost ------------------------
    costs = [v["cost"] for v in s2.values() if v["cost"]]
    avg = sum(costs) / len(costs)
    p = len(u2 and [i for i in common if s2[i]["res"]]) / len(common)
    print(f"\n=== adaptive best-of-N cost (measured dev cost ${avg:.2f}/instance, p={p:.2f}) ===")
    for n in (1, 2, 3):
        exp = sum((1 - p) ** k for k in range(n))
        print(f"  N={n}: {exp:.2f} expected attempts -> ${avg*exp:.2f}/instance")
    exp2 = 1 + (1 - p)
    print(f"  at the observed best-of-2 union {len(u2)}/{len(common)}: "
          f"${avg*exp2*len(common)/len(u2):.2f}/resolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
