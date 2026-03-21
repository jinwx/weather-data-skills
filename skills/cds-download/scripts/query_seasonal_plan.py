#!/usr/bin/env python3
"""
Query CDS constraints API and build a seasonal forecast download plan.

Outputs a JSON file listing every (centre, system, year, month) to download,
based on one of several strategies:

  - latest-system (default): Single latest system per centre. Internally
    consistent — same model physics throughout.
  - max-coverage: Latest system's hindcasts + chained real-time from all
    systems. Maximizes temporal coverage.

Supports single-centre or multi-centre mode.

Requires: Python 3.7+ (no extra packages needed — uses urllib only).
See references/seasonal.md for usage examples and strategy guidance.
"""
import argparse
import json
import sys
import os

# Allow importing cds_utils from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cds_utils import query_constraints, find_latest_system


def plan_latest_system(dataset, centre, product_type, year_start=None, year_end=None):
    """Strategy A: download everything from the latest system."""
    print(f"[{centre}] Finding latest system...")
    system = find_latest_system(dataset, centre, product_type)
    if not system:
        print(f"[{centre}] No systems found, skipping.")
        return []

    print(f"[{centre}] Latest system: {system}")
    avail = query_constraints(
        dataset, originating_centre=[centre], system=[system],
        product_type=[product_type],
    )
    years = sorted(avail.get("year", []), key=int)
    months = sorted(avail.get("month", []))

    if year_start:
        years = [y for y in years if int(y) >= year_start]
    if year_end:
        years = [y for y in years if int(y) <= year_end]

    print(f"[{centre}] sys {system}: {years[0]}–{years[-1]} ({len(years)} years), "
          f"{len(months)} months")

    return [
        {"centre": centre, "system": system, "year": y, "month": m}
        for y in years for m in months
    ]


def plan_max_coverage(dataset, centre, product_type, hindcast_cutoff=2017,
                      year_start=None, year_end=None):
    """Strategy B: latest system hindcasts + chained real-time from all systems."""
    print(f"[{centre}] Querying all systems...")
    result = query_constraints(dataset, originating_centre=[centre])
    systems = result.get("system", [])
    if not systems:
        print(f"[{centre}] No systems found, skipping.")
        return []

    print(f"[{centre}] Available systems: {systems}")

    # Get coverage for each system
    system_coverage = {}
    for sys_ver in systems:
        r = query_constraints(
            dataset, originating_centre=[centre], system=[sys_ver],
            product_type=[product_type],
        )
        years = r.get("year", [])
        months = r.get("month", [])
        year_months = {(y, m) for y in years for m in months}
        system_coverage[sys_ver] = year_months
        hc = [y for y in years if int(y) < hindcast_cutoff]
        rt = [y for y in years if int(y) >= hindcast_cutoff]
        print(f"[{centre}]   sys {sys_ver}: {len(hc)} hindcast yrs, "
              f"{len(rt)} real-time yrs")

    # Find the latest system
    latest_sys = max(systems, key=lambda s: max(
        (int(y) * 100 + int(m) for y, m in system_coverage[s]), default=0
    ))
    print(f"[{centre}] Latest system: {latest_sys}")

    plan = []
    covered = set()

    # 1. Use latest system for all hindcast year-months
    hindcast_pairs = sorted(
        (y, m) for y, m in system_coverage[latest_sys] if int(y) < hindcast_cutoff
    )
    for y, m in hindcast_pairs:
        plan.append((latest_sys, y, m))
        covered.add((y, m))

    # 2. For real-time, assign each year-month to the newest system that has it
    all_realtime = set()
    for sys_ver, ym_set in system_coverage.items():
        for y, m in ym_set:
            if int(y) >= hindcast_cutoff:
                all_realtime.add((y, m))

    systems_by_recency = sorted(systems, key=lambda s: max(
        (int(y) * 100 + int(m) for y, m in system_coverage[s]
         if int(y) >= hindcast_cutoff),
        default=0
    ), reverse=True)

    for y, m in sorted(all_realtime):
        if (y, m) in covered:
            continue
        for sys_ver in systems_by_recency:
            if (y, m) in system_coverage[sys_ver]:
                plan.append((sys_ver, y, m))
                covered.add((y, m))
                break

    # Convert and filter by year range
    tasks = [
        {"centre": centre, "system": s, "year": y, "month": m}
        for s, y, m in sorted(plan)
    ]
    if year_start:
        tasks = [t for t in tasks if int(t["year"]) >= year_start]
    if year_end:
        tasks = [t for t in tasks if int(t["year"]) <= year_end]

    # Summarize
    systems_used = sorted(set(t["system"] for t in tasks))
    for sv in systems_used:
        sv_years = sorted(set(t["year"] for t in tasks if t["system"] == sv), key=int)
        print(f"[{centre}]   Plan: sys {sv} → {sv_years[0]}–{sv_years[-1]}")

    return tasks


def main():
    p = argparse.ArgumentParser(
        description="Build a seasonal forecast download plan by querying CDS constraints.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--centre", help="Single centre (e.g., ecmwf)")
    group.add_argument("--centres", nargs="+", help="Multiple centres")

    p.add_argument("--dataset", default="seasonal-monthly-single-levels",
                   help="CDS dataset ID (default: seasonal-monthly-single-levels)")
    p.add_argument("--strategy", choices=["latest-system", "max-coverage"],
                   default="latest-system",
                   help="Planning strategy (default: latest-system)")
    p.add_argument("--product-type", default="monthly_mean",
                   help="Product type (default: monthly_mean)")
    p.add_argument("--hindcast-cutoff", type=int, default=2017,
                   help="Year separating hindcast/real-time for max-coverage (default: 2017)")
    p.add_argument("--year-start", type=int, help="Filter: earliest year")
    p.add_argument("--year-end", type=int, help="Filter: latest year")
    p.add_argument("-o", "--output", default="download_plan.json",
                   help="Output JSON file (default: download_plan.json)")

    args = p.parse_args()
    centres = args.centres or [args.centre]

    all_tasks = []
    for centre in centres:
        if args.strategy == "max-coverage":
            tasks = plan_max_coverage(
                args.dataset, centre, args.product_type,
                args.hindcast_cutoff, args.year_start, args.year_end,
            )
        else:
            tasks = plan_latest_system(
                args.dataset, centre, args.product_type,
                args.year_start, args.year_end,
            )
        all_tasks.extend(tasks)

    result = {
        "dataset": args.dataset,
        "product_type": args.product_type,
        "strategy": args.strategy,
        "total_requests": len(all_tasks),
        "tasks": all_tasks,
    }

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nPlan saved to {args.output} ({len(all_tasks)} requests)")


if __name__ == "__main__":
    main()
