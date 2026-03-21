#!/usr/bin/env python3
"""
Download seasonal forecast data from the CDS using a pre-built plan.

Takes a plan JSON (from query_seasonal_plan.py) and downloads each task.
Resumable — skips existing files. Optional parallelism.

Requires:
    pip install "cdsapi>=0.7.7"
    ~/.cdsapirc configured

See references/seasonal.md for usage examples.
"""
import argparse
import json
import os
import cdsapi


def download_one(client, dataset, task, variables, product_type, leadtime_months,
                 data_format, output_dir, area=None):
    """Download one (centre, system, year, month) task. Returns status string."""
    centre = task["centre"]
    system = task["system"]
    year = task["year"]
    month = task["month"]

    target = os.path.join(
        output_dir, f"{centre}_sys{system}_{year}_{month}.{data_format}"
    )
    if os.path.exists(target):
        return f"Skipped (exists): {target}"

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
    if area:
        request["area"] = area

    try:
        client.retrieve(dataset, request, target)
        return f"Downloaded: {target}"
    except Exception as e:
        return f"ERROR ({target}): {e}"


def main():
    p = argparse.ArgumentParser(
        description="Download seasonal forecast data using a plan JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--plan", required=True, help="Path to download_plan.json")
    p.add_argument("--variables", required=True, nargs="+", help="Variable names")
    p.add_argument("--leadtime-months", required=True, nargs="+",
                   help="Forecast lead time months (e.g., 1 2 3 4 5 6)")
    p.add_argument("--product-type", default=None,
                   help="Product type (default: from plan)")
    p.add_argument("--format", choices=["grib", "netcdf"], default="grib",
                   dest="data_format", help="Data format (default: grib)")
    p.add_argument("--area", nargs=4, type=float, metavar=("N", "W", "S", "E"),
                   help="Geographic subset [North West South East]")
    p.add_argument("-o", "--output-dir", default="./seasonal_data",
                   help="Output directory (default: ./seasonal_data)")
    p.add_argument("--workers", type=int, default=1,
                   help="Parallel download workers (default: 1, max recommended: 4)")

    args = p.parse_args()

    with open(args.plan) as f:
        plan = json.load(f)

    dataset = plan["dataset"]
    product_type = args.product_type or plan.get("product_type", "monthly_mean")
    tasks = plan["tasks"]

    print(f"Dataset: {dataset}")
    print(f"Product type: {product_type}")
    print(f"Tasks: {len(tasks)}")
    print(f"Variables: {args.variables}")
    print(f"Leadtime months: {args.leadtime_months}")

    os.makedirs(args.output_dir, exist_ok=True)
    client = cdsapi.Client()

    if args.workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(args.workers, 4)) as pool:
            futures = {
                pool.submit(
                    download_one, client, dataset, task, args.variables,
                    product_type, args.leadtime_months, args.data_format,
                    args.output_dir, args.area,
                ): task
                for task in tasks
            }
            for future in as_completed(futures):
                print(future.result())
    else:
        for task in tasks:
            print(f"Requesting {task['centre']} sys{task['system']} "
                  f"{task['year']}-{task['month']}...")
            print(f"  {download_one(client, dataset, task, args.variables, product_type, args.leadtime_months, args.data_format, args.output_dir, args.area)}")

    print("Done.")


if __name__ == "__main__":
    main()
