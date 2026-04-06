#!/usr/bin/env python3
"""
Download seasonal forecast data from the CDS using a pre-built plan.

Takes a plan JSON from Step 3b and downloads each task.
Resumable — skips existing files. Optional parallelism.

Requires:
    pip install "cdsapi>=0.7.7"
    ~/.cdsapirc configured

See references/seasonal.md for usage examples.
"""

import argparse
import json
import os
from functools import partial

import cdsapi

MONTHLY_ATMOSPHERIC_DATASETS = frozenset(
    {
        "seasonal-monthly-single-levels",
        "seasonal-monthly-pressure-levels",
        "seasonal-postprocessed-single-levels",
        "seasonal-postprocessed-pressure-levels",
    }
)
PRESSURE_LEVEL_DATASETS = frozenset(
    {
        "seasonal-monthly-pressure-levels",
        "seasonal-postprocessed-pressure-levels",
    }
)


def build_tasks(plan):
    tasks = []

    for centre_item in plan["centres"]:
        centre = centre_item["centre"]
        for segment in centre_item["segments"]:
            system = segment["system"]
            start_year_text, start_month_text = segment["start"].split("-")
            end_year_text, end_month_text = segment["end"].split("-")
            start_year = int(start_year_text)
            start_month = int(start_month_text)
            end_year = int(end_year_text)
            end_month = int(end_month_text)
            start_index = start_year * 12 + start_month - 1
            end_index = end_year * 12 + end_month - 1

            for value in range(start_index, end_index + 1):
                year, month = divmod(value, 12)
                tasks.append({"centre": centre, "system": system, "year": f"{year:04d}", "month": f"{month + 1:02d}"})

    return tasks


def download_one(
    task,
    *,
    client,
    dataset,
    variables,
    product_type,
    leadtime_months,
    pressure_levels,
    data_format,
    output_dir,
    area=None,
):
    """Download one (centre, system, year, month) task. Returns status string."""
    centre = task["centre"]
    system = task["system"]
    year = task["year"]
    month = task["month"]

    target = os.path.join(output_dir, f"{centre}_sys{system}_{year}_{month}.{data_format}")
    downloading_target = f"{target}.downloading"
    if os.path.exists(target):
        return f"Skipped (exists): {target}"
    if os.path.exists(downloading_target):
        os.remove(downloading_target)

    request = {
        "originating_centre": centre,
        "system": system,
        "variable": variables,
        "product_type": [product_type],
        "year": [year],
        "month": [month],
        "leadtime_month": leadtime_months,
        "data_format": data_format,
    }
    if pressure_levels:
        request["pressure_level"] = pressure_levels
    if area:
        request["area"] = area

    try:
        client.retrieve(dataset, request, downloading_target)
        os.replace(downloading_target, target)
        return f"Downloaded: {target}"
    except Exception as e:
        return f"ERROR ({downloading_target}): {e}"


def _validate_plan_inputs(dataset: str, pressure_levels: list[str] | None) -> None:
    if dataset not in MONTHLY_ATMOSPHERIC_DATASETS:
        raise SystemExit(
            "download_seasonal.py currently supports only monthly atmospheric datasets: "
            + ", ".join(sorted(MONTHLY_ATMOSPHERIC_DATASETS))
        )
    if dataset in PRESSURE_LEVEL_DATASETS and not pressure_levels:
        raise SystemExit(f"--pressure-levels is required for {dataset}")
    if dataset not in PRESSURE_LEVEL_DATASETS and pressure_levels:
        raise SystemExit("--pressure-levels is only valid for pressure-level datasets")


def main():
    p = argparse.ArgumentParser(description="Download seasonal forecast data using a plan JSON.")
    p.add_argument("--plan", required=True, help="Path to download_plan.json")
    p.add_argument("--variables", required=True, nargs="+", help="Variable names")
    p.add_argument("--leadtime-months", nargs="+", default=["1", "2", "3", "4", "5", "6"],
                   help="Forecast lead time months (default: 1 2 3 4 5 6)")
    p.add_argument("--pressure-levels", nargs="+",
                   help="Pressure levels for pressure-level datasets (for example: 500 850 1000)")
    p.add_argument("--format", choices=["grib", "netcdf"], default="grib", dest="data_format",
                   help="Data format (default: grib)")
    p.add_argument("--area", nargs=4, type=float, metavar=("N", "W", "S", "E"),
                   help="Geographic subset [North West South East]")
    p.add_argument("-o", "--output-dir", default="./seasonal_data", help="Output directory (default: ./seasonal_data)")
    p.add_argument("--workers", type=int, default=4, help="Parallel download workers (default: 4)")

    args = p.parse_args()

    with open(args.plan) as f:
        plan = json.load(f)

    dataset = plan["dataset"]
    product_type = plan["product_type"]
    tasks = build_tasks(plan)
    _validate_plan_inputs(dataset, args.pressure_levels)

    print(f"Dataset: {dataset}")
    print(f"Product type: {product_type}")
    print(f"Centres: {len(plan['centres'])}")
    if args.pressure_levels:
        print(f"Pressure levels: {args.pressure_levels}")
    print(f"Tasks: {len(tasks)}")
    print(f"Variables: {args.variables}")
    print(f"Leadtime months: {args.leadtime_months}")

    os.makedirs(args.output_dir, exist_ok=True)
    client = cdsapi.Client()
    download_task = partial(
        download_one,
        client=client,
        dataset=dataset,
        variables=args.variables,
        product_type=product_type,
        leadtime_months=args.leadtime_months,
        pressure_levels=args.pressure_levels,
        data_format=args.data_format,
        output_dir=args.output_dir,
        area=args.area,
    )

    if args.workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(download_task, task): task for task in tasks}
            for future in as_completed(futures):
                print(future.result())
    else:
        for task in tasks:
            print(f"Requesting {task['centre']} sys{task['system']} "
                  f"{task['year']}-{task['month']}...")
            print("  " + download_task(task))

    print("Done.")


if __name__ == "__main__":
    main()
