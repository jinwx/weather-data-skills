"""
Download common ERA5 / ERA5-Land datasets from the CDS, split by month.

Supported datasets:
    - reanalysis-era5-single-levels
    - reanalysis-era5-pressure-levels
    - reanalysis-era5-land
    - reanalysis-era5-single-levels-monthly-means
    - reanalysis-era5-pressure-levels-monthly-means
    - reanalysis-era5-land-monthly-means

This script intentionally does not support daily statistics, ERA5-complete,
time-series datasets, or custom product types.
"""

import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import cdsapi


@dataclass(frozen=True)
class DatasetConfig:
    product_type: str | None
    needs_pressure_levels: bool
    is_monthly: bool


DATASETS = {
    "reanalysis-era5-single-levels": DatasetConfig("reanalysis", needs_pressure_levels=False, is_monthly=False),
    "reanalysis-era5-pressure-levels": DatasetConfig("reanalysis", needs_pressure_levels=True, is_monthly=False),
    "reanalysis-era5-land": DatasetConfig(None, needs_pressure_levels=False, is_monthly=False),
    "reanalysis-era5-single-levels-monthly-means": DatasetConfig(
        "monthly_averaged_reanalysis", needs_pressure_levels=False, is_monthly=True
    ),
    "reanalysis-era5-pressure-levels-monthly-means": DatasetConfig(
        "monthly_averaged_reanalysis", needs_pressure_levels=True, is_monthly=True
    ),
    "reanalysis-era5-land-monthly-means": DatasetConfig(
        "monthly_averaged_reanalysis", needs_pressure_levels=False, is_monthly=True
    ),
}

MAX_WORKERS = 4


def parse_args():
    parser = argparse.ArgumentParser(description="Download common ERA5 datasets from CDS, split by month.")
    parser.add_argument("--dataset", required=True, choices=sorted(DATASETS), help="Supported CDS dataset identifier")
    parser.add_argument("--variables", required=True, nargs="+", help="Variable names")
    parser.add_argument(
        "--years", required=True, nargs=2, type=int, metavar=("START", "END"), help="Year range (inclusive)"
    )
    parser.add_argument(
        "--months", nargs="+", type=int, default=list(range(1, 13)), help="Months to download (default: all months)"
    )
    parser.add_argument("--pressure-levels", nargs="+", help="Pressure levels in hPa for pressure-level datasets")
    parser.add_argument(
        "--format", choices=["grib", "netcdf"], default="grib", dest="data_format", help="Output data format"
    )
    parser.add_argument(
        "--area", nargs=4, type=float, metavar=("N", "W", "S", "E"), help="Geographic subset [North West South East]"
    )
    parser.add_argument("-o", "--output-dir", default="./era5_data", help="Output directory")
    parser.add_argument(
        "--workers", type=int, default=1, help=f"Parallel download workers (default: 1, max: {MAX_WORKERS})"
    )
    return parser.parse_args()


def validate_args(args):
    config = DATASETS[args.dataset]
    start_year, end_year = args.years

    if start_year > end_year:
        raise SystemExit("--years must be in ascending order: START END")

    if not args.months:
        raise SystemExit("--months must not be empty")

    invalid_months = sorted({month for month in args.months if month < 1 or month > 12})
    if invalid_months:
        invalid = ", ".join(str(month) for month in invalid_months)
        raise SystemExit(f"Invalid month values: {invalid}. Expected 1-12.")

    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")

    if config.needs_pressure_levels and not args.pressure_levels:
        raise SystemExit(f"--pressure-levels is required for {args.dataset}")
    if not config.needs_pressure_levels and args.pressure_levels:
        raise SystemExit("--pressure-levels is only valid for pressure-level datasets")

    if args.area:
        north, west, south, east = args.area
        if north < south:
            raise SystemExit("--area must satisfy North >= South")
        if not (-90 <= south <= 90 and -90 <= north <= 90):
            raise SystemExit("--area latitude values must be within [-90, 90]")
        if not (-180 <= west <= 180 and -180 <= east <= 180):
            raise SystemExit("--area longitude values must be within [-180, 180]")


def build_request(dataset, variables, pressure_levels, data_format, area, year, month):
    config = DATASETS[dataset]
    request = {"variable": variables, "year": [str(year)], "month": [f"{month:02d}"], "data_format": data_format}

    if config.product_type:
        request["product_type"] = config.product_type
    if config.is_monthly:
        request["time"] = ["00:00"]
    else:
        request["day"] = [f"{day:02d}" for day in range(1, 32)]
        request["time"] = [f"{hour:02d}:00" for hour in range(24)]
    if config.needs_pressure_levels:
        request["pressure_level"] = pressure_levels
    if area:
        request["area"] = area
    return request


def target_path(output_dir, dataset, data_format, year, month):
    extension = "nc" if data_format == "netcdf" else "grib"
    prefix = dataset.replace("reanalysis-", "")
    return os.path.join(output_dir, f"{prefix}_{year}_{month:02d}.{extension}")


def download_one(client, dataset, request, target):
    if os.path.exists(target):
        return True, f"Skipped (exists): {target}"
    try:
        client.retrieve(dataset, request, target)
    except Exception as exc:
        return False, f"ERROR ({target}): {exc}"
    return True, f"Downloaded: {target}"


def iter_tasks(years, months):
    start_year, end_year = years
    for year in range(start_year, end_year + 1):
        for month in months:
            yield year, month


def main():
    args = parse_args()
    validate_args(args)

    os.makedirs(args.output_dir, exist_ok=True)
    client = cdsapi.Client()
    tasks = list(iter_tasks(args.years, args.months))
    had_errors = False

    if args.workers == 1:
        for year, month in tasks:
            request = build_request(
                args.dataset, args.variables, args.pressure_levels, args.data_format, args.area, year, month
            )
            target = target_path(args.output_dir, args.dataset, args.data_format, year, month)
            print(f"Requesting {year}-{month:02d}...")
            ok, message = download_one(client, args.dataset, request, target)
            had_errors = had_errors or not ok
            print(f"  {message}")
    else:
        worker_count = min(args.workers, MAX_WORKERS)
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = {
                pool.submit(
                    download_one,
                    client,
                    args.dataset,
                    build_request(
                        args.dataset, args.variables, args.pressure_levels, args.data_format, args.area, year, month
                    ),
                    target_path(args.output_dir, args.dataset, args.data_format, year, month),
                ): (year, month)
                for year, month in tasks
            }
            for future in as_completed(futures):
                ok, message = future.result()
                had_errors = had_errors or not ok
                print(message)

    if had_errors:
        raise SystemExit(1)

    print("Done.")


if __name__ == "__main__":
    main()
