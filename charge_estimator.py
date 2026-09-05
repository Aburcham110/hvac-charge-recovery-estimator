#!/usr/bin/env python3
"""Educational HVAC/R refrigerant charge add/recover estimator (stdlib only).

Approximate additional charge from line-set factors vs factory/nameplate.
NOT an OEM charge procedure — use manufacturer charts / weighed charge / digital manifold.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

DISCLAIMER = (
    "EDUCATIONAL ONLY — NOT an OEM charge procedure. "
    "Use manufacturer charts, weighed-in charge, and a refrigerant-rated "
    "digital manifold for real service work."
)

REFRIGERANTS = ("R-410A", "R-22", "R-134a", "R-404A", "R-407C", "R-32", "R-454B")
SYSTEMS = ("split-ac", "package", "walk-in", "custom")

# Educational oz/ft liquid-line factors by refrigerant and copper OD (approx).
# Grounded in common field rule-of-thumb tables; labeled approximate.
LIQUID_OZ_PER_FT: Dict[str, Dict[str, float]] = {
    "R-410A": {"1/4": 0.19, "3/8": 0.40, "1/2": 0.80, "5/8": 1.30, "3/4": 1.90},
    "R-22": {"1/4": 0.22, "3/8": 0.48, "1/2": 0.95, "5/8": 1.50, "3/4": 2.20},
    "R-134a": {"1/4": 0.18, "3/8": 0.38, "1/2": 0.75, "5/8": 1.20, "3/4": 1.75},
    "R-404A": {"1/4": 0.20, "3/8": 0.42, "1/2": 0.85, "5/8": 1.35, "3/4": 1.95},
    "R-407C": {"1/4": 0.20, "3/8": 0.42, "1/2": 0.82, "5/8": 1.32, "3/4": 1.92},
    "R-32": {"1/4": 0.15, "3/8": 0.32, "1/2": 0.64, "5/8": 1.05, "3/4": 1.55},
    "R-454B": {"1/4": 0.17, "3/8": 0.36, "1/2": 0.72, "5/8": 1.18, "3/4": 1.72},
}

# Suction vapor contribution as fraction of same-OD liquid factor (approx).
SUCTION_FRACTION = 0.05

# Factory-included liquid line (ft) by system type (educational presets).
INCLUDED_LIQUID_FT = {
    "split-ac": 25.0,
    "package": 0.0,
    "walk-in": 0.0,
    "custom": 0.0,
}

OD_CHOICES = ("1/4", "3/8", "1/2", "5/8", "3/4")


def norm_ref(s: str) -> str:
    key = s.strip().upper().replace(" ", "").replace("_", "-")
    aliases = {
        "R410A": "R-410A",
        "410A": "R-410A",
        "R22": "R-22",
        "22": "R-22",
        "R134A": "R-134a",
        "134A": "R-134a",
        "R404A": "R-404A",
        "404A": "R-404A",
        "R407C": "R-407C",
        "407C": "R-407C",
        "R32": "R-32",
        "32": "R-32",
        "R454B": "R-454B",
        "454B": "R-454B",
    }
    if key in aliases:
        return aliases[key]
    for r in REFRIGERANTS:
        if r.upper() == key:
            return r
    raise ValueError(f"Unknown refrigerant: {s!r}. Choose from {', '.join(REFRIGERANTS)}")


def norm_od(s: str) -> str:
    t = s.strip().replace('"', "").replace("in", "").replace(" ", "")
    aliases = {
        "0.25": "1/4",
        ".25": "1/4",
        "0.375": "3/8",
        ".375": "3/8",
        "0.5": "1/2",
        ".5": "1/2",
        "0.625": "5/8",
        ".625": "5/8",
        "0.75": "3/4",
        ".75": "3/4",
    }
    if t in aliases:
        return aliases[t]
    if t in OD_CHOICES:
        return t
    raise ValueError(f"Unknown OD: {s!r}. Choose from {', '.join(OD_CHOICES)}")


@dataclass
class Estimate:
    refrigerant: str
    system: str
    factory_lbs: float
    included_liquid_ft: float
    liquid_ft: float
    liquid_od: str
    suction_ft: float
    suction_od: str
    receiver_lbs: float
    extra_lbs: float
    current_lbs: Optional[float]
    billable_liquid_ft: float
    liquid_oz: float
    suction_oz: float
    add_lbs: float
    estimated_total_lbs: float
    delta_lbs: Optional[float]  # positive = add, negative = recover


def estimate(
    *,
    refrigerant: str,
    system: str,
    factory_lbs: float,
    liquid_ft: float,
    liquid_od: str,
    suction_ft: float = 0.0,
    suction_od: str = "5/8",
    included_liquid_ft: Optional[float] = None,
    receiver_lbs: float = 0.0,
    extra_lbs: float = 0.0,
    current_lbs: Optional[float] = None,
) -> Estimate:
    ref = norm_ref(refrigerant)
    sys_t = system.strip().lower()
    if sys_t not in SYSTEMS:
        raise ValueError(f"Unknown system: {system!r}")
    lod = norm_od(liquid_od)
    sod = norm_od(suction_od)
    if factory_lbs < 0:
        raise ValueError("factory_lbs must be >= 0")
    if liquid_ft < 0 or suction_ft < 0:
        raise ValueError("lengths must be >= 0")

    incl = INCLUDED_LIQUID_FT[sys_t] if included_liquid_ft is None else float(included_liquid_ft)
    billable = max(0.0, liquid_ft - incl)
    lfac = LIQUID_OZ_PER_FT[ref][lod]
    sfac = LIQUID_OZ_PER_FT[ref].get(sod, lfac) * SUCTION_FRACTION
    liquid_oz = billable * lfac
    suction_oz = suction_ft * sfac
    add_lbs = (liquid_oz + suction_oz) / 16.0 + receiver_lbs + extra_lbs
    total = factory_lbs + add_lbs
    delta = None if current_lbs is None else total - current_lbs
    return Estimate(
        refrigerant=ref,
        system=sys_t,
        factory_lbs=factory_lbs,
        included_liquid_ft=incl,
        liquid_ft=liquid_ft,
        liquid_od=lod,
        suction_ft=suction_ft,
        suction_od=sod,
        receiver_lbs=receiver_lbs,
        extra_lbs=extra_lbs,
        current_lbs=current_lbs,
        billable_liquid_ft=billable,
        liquid_oz=liquid_oz,
        suction_oz=suction_oz,
        add_lbs=add_lbs,
        estimated_total_lbs=total,
        delta_lbs=delta,
    )


def format_report(e: Estimate) -> str:
    lines = [
        DISCLAIMER,
        "",
        f"System: {e.system}  |  Refrigerant: {e.refrigerant}",
        f"Factory/nameplate: {e.factory_lbs:.2f} lb",
        f"Liquid line: {e.liquid_ft:.1f} ft @ {e.liquid_od}\" OD "
        f"(factory-included {e.included_liquid_ft:.1f} ft → billable {e.billable_liquid_ft:.1f} ft)",
        f"Suction line: {e.suction_ft:.1f} ft @ {e.suction_od}\" OD "
        f"(vapor factor ~{SUCTION_FRACTION*100:.0f}% of liquid oz/ft)",
        f"Liquid add: {e.liquid_oz:.1f} oz  |  Suction add: {e.suction_oz:.1f} oz",
        f"Receiver: {e.receiver_lbs:.2f} lb  |  Extra volume: {e.extra_lbs:.2f} lb",
        f"Approx additional charge: {e.add_lbs:.2f} lb",
        f"Estimated total charge: {e.estimated_total_lbs:.2f} lb",
    ]
    if e.delta_lbs is not None:
        cur = e.current_lbs if e.current_lbs is not None else 0.0
        if abs(e.delta_lbs) < 0.05:
            lines.append(f"Current {cur:.2f} lb ≈ target — no material add/recover")
        elif e.delta_lbs > 0:
            lines.append(f"vs current {cur:.2f} lb → approximate ADD {e.delta_lbs:.2f} lb")
        else:
            lines.append(f"vs current {cur:.2f} lb → approximate RECOVER {abs(e.delta_lbs):.2f} lb")
    lines += [
        "",
        "Assumptions (approximate):",
        "  • oz/ft factors are educational composites, not OEM charts",
        "  • suction treated as sparse vapor (small fraction of liquid density)",
        "  • no oil, filter-drier, or coil-volume model",
        "  • blend glide / density variation ignored",
        "",
        "Checklist:",
        "  [ ] Confirm nameplate / factory charge and included line length",
        "  [ ] Verify line OD and actual installed length (not just plan ft)",
        "  [ ] Use OEM additional-charge chart when available",
        "  [ ] Weigh cylinder / use recovery machine for add or recover",
        "  [ ] Verify with SH/SC and manifold pressures after service",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Educational HVAC/R charge add/recover estimator (approximate).",
        epilog=DISCLAIMER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-i", "--interactive", action="store_true", help="Prompt for inputs")
    p.add_argument("--system", choices=SYSTEMS, help="System type")
    p.add_argument("--refrigerant", help=f"One of: {', '.join(REFRIGERANTS)}")
    p.add_argument("--factory-lbs", type=float, help="Factory/nameplate charge (lb)")
    p.add_argument("--liquid-ft", type=float, help="Liquid line length (ft)")
    p.add_argument("--liquid-od", help=f"Liquid OD: {', '.join(OD_CHOICES)}")
    p.add_argument("--suction-ft", type=float, default=None, help="Suction line length (ft)")
    p.add_argument("--suction-od", default=None, help=f"Suction OD: {', '.join(OD_CHOICES)}")
    p.add_argument(
        "--included-ft",
        type=float,
        default=None,
        help="Override factory-included liquid ft",
    )
    p.add_argument("--receiver-lbs", type=float, default=0.0, help="Receiver / extra vessel (lb)")
    p.add_argument("--extra-lbs", type=float, default=0.0, help="Other extra volume (lb)")
    p.add_argument("--current-lbs", type=float, default=None, help="Current charge if known (lb)")
    return p


def pf(prompt: str, default: Optional[float] = None) -> float:
    while True:
        suf = f" [{default}]" if default is not None else ""
        s = input(f"{prompt}{suf}: ").strip()
        if not s and default is not None:
            return float(default)
        try:
            return float(s)
        except ValueError:
            print("Enter a number.")


def pc(label: str, choices: List[str], default: str) -> str:
    while True:
        s = (input(f"{label} ({'/'.join(choices)}) [{default}]: ").strip() or default)
        for c in choices:
            if s.lower() == c.lower():
                return c
        print("Invalid choice.")


def interactive() -> Estimate:
    print(DISCLAIMER)
    print()
    system = pc("System type", list(SYSTEMS), "split-ac")
    refrigerant = pc("Refrigerant", list(REFRIGERANTS), "R-410A")
    factory = pf("Factory/nameplate charge (lb)")
    liquid_ft = pf("Liquid line length (ft)", 25.0 if system == "split-ac" else 0.0)
    liquid_od = pc("Liquid OD", list(OD_CHOICES), "3/8")
    suction_ft = pf("Suction line length (ft)", liquid_ft)
    suction_od = pc("Suction OD", list(OD_CHOICES), "5/8")
    incl = INCLUDED_LIQUID_FT[system]
    if system == "custom":
        incl = pf("Factory-included liquid ft", 0.0)
    else:
        print(f"Factory-included liquid (preset): {incl} ft")
    receiver = pf("Receiver / vessel extra (lb)", 0.0)
    extra = pf("Other extra volume (lb)", 0.0)
    cur_s = input("Current charge lbs (blank to skip): ").strip()
    current = float(cur_s) if cur_s else None
    return estimate(
        refrigerant=refrigerant,
        system=system,
        factory_lbs=factory,
        liquid_ft=liquid_ft,
        liquid_od=liquid_od,
        suction_ft=suction_ft,
        suction_od=suction_od,
        included_liquid_ft=incl,
        receiver_lbs=receiver,
        extra_lbs=extra,
        current_lbs=current,
    )


def from_args(ns: argparse.Namespace) -> Estimate:
    missing = [
        n
        for n, v in [
            ("--system", ns.system),
            ("--refrigerant", ns.refrigerant),
            ("--factory-lbs", ns.factory_lbs),
            ("--liquid-ft", ns.liquid_ft),
            ("--liquid-od", ns.liquid_od),
        ]
        if v is None
    ]
    if missing:
        raise SystemExit(f"Missing required args: {', '.join(missing)} (or use -i)")
    suction_ft = ns.suction_ft if ns.suction_ft is not None else ns.liquid_ft
    suction_od = ns.suction_od if ns.suction_od is not None else "5/8"
    return estimate(
        refrigerant=ns.refrigerant,
        system=ns.system,
        factory_lbs=ns.factory_lbs,
        liquid_ft=ns.liquid_ft,
        liquid_od=ns.liquid_od,
        suction_ft=suction_ft,
        suction_od=suction_od,
        included_liquid_ft=ns.included_ft,
        receiver_lbs=ns.receiver_lbs,
        extra_lbs=ns.extra_lbs,
        current_lbs=ns.current_lbs,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    try:
        e = interactive() if ns.interactive else from_args(ns)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2
    print(format_report(e))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
