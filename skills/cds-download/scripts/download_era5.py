#!/usr/bin/env python3
"""
Download ERA5 / ERA5-Land data from the CDS, split by month for efficiency.

Supports hourly, daily statistics, and monthly-means time scales.
Resumable (skips existing files). Optionally parallel.

Requires:
    pip install "cdsapi>=0.7.7"
    ~/.cdsapirc configured (see references/api-setup.md)

See references/era5.md for usage examples and dataset-specific guidance.
"""
import argparse
import os
import cdsapi


# --- Dataset classification ---

DAILY_STATS_DATASETS = {
    "derived-era5-single-levels-daily-statistics",
    "derived-era5-land-daily-statistics",
}

MONTHLY_MEANS_DATASETS = {
    "reanalysis-era5-single-levels-monthly-means",
    "reanalysis-era5-pressure-levels-monthly-means",
    "reanalysis-era5-land-monthly-means",
}

PRESSURE_LEVEL_DATASETS = {
    "reanalysis-era5-pressure-levels",
    "reanalysis-era5-pressure-levels-monthly-means",
}


def parse_args():
    p = argparse.ArgumentParser(
        description="Download ERA5 data from CDS, split by month.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dataset", required=True, help="CDS dataset identifier")
    p.add_argument("--variables", required=True, nargs="+", help="Variable names")
    p.add_argument("--years", required=True, nargs=2, type=int,
                    metavar=("START", "END"), help="Year range (inclusive)")
    p.add_argument("--months", nargs="+", type=int, default=list(range(1, 13)),
                    help="Months to download (default: all)")
    p.add_argument("-o", "--output-dir", default="./era5_data", help="Output directory")
    p.add_argument("--format", choices=["netcdf", "grib"], default="netcdf",
                    dest="data_format", help="Data format (ignored for daily stats)")
    p.add_argument("--area", nargs=4, type=float, metavar=("N", "W", "S", "E"),
                    help="Geographic subset [North West South East]")
    p.add_argument("--grid", nargs=2, type=float, metavar=("LAT", "LON"),
                    help="Output grid resolution [lat lon]")
    p.add_argument("--workers", type=int, default=1,
                    help="Parallel download workers (default: 1, max recommended: 4)")

    # Pressure-level options
    p.add_argument("--pressure-levels", nargs="+",
                    help="Pressure levels in hPa (required for pressure-level datasets)")

    # Daily statistics options
    p.add_argument("--daily-statistic",
                    choices=["daily_mean", "daily_minimum", "daily_maximum", "daily_sum"],
                    help="Statistic type (required for daily-stats datasets)")
    p.add_argument("--frequency", choices=["1_hourly", "3_hourly", "6_hourly"],
                    default="1_hourly",
                    help="Sub-daily sampling for daily stats (default: 1_hourly)")
    p.add_argument("--time-zone", default="utc+00:00",
                    help="Time zone defining a 'day' for daily stats (default: utc+00:00)")

    # Monthly means options
    p.add_argument("--product-type", nargs="+", default=["reanalysis"],
                    help="Product type(s) (default: reanalysis)")

    return p.parse_args()


def build_request(args, year, month):
    """Build a CDS API request dict for one year-month."""
    is_daily = args.dataset in DAILY_STATS_DATASETS
    is_monthly = args.dataset in MONTHLY_MEANS_DATASETS
    is_pressure = args.dataset in PRESSURE_LEVEL_DATASETS

    request = {
        "product_type": args.product_type,
        "variable": args.variables,
        "year": [str(year)],
        "month": [f"{month:02d}"],
    }

    if is_daily:
        # Daily stats: day list, no time, extra params, always NetCDF+zip
        request["day"] = [f"{d:02d}" for d in range(1, 32)]
        request["daily_statistic"] = args.daily_statistic
        request["frequency"] = args.frequency
        request["time_zone"] = args.time_zone
    elif is_monthly:
        # Monthly means: no day/time needed
        request["data_format"] = args.data_format
    else:
        # Hourly: full day + time lists
        request["day"] = [f"{d:02d}" for d in range(1, 32)]
        request["time"] = [f"{h:02d}:00" for h in range(24)]
        request["data_format"] = args.data_format

    if is_pressure:
        if not args.pressure_levels:
            raise ValueError(f"--pressure-levels required for {args.dataset}")
        request["pressure_level"] = args.pressure_levels

    if args.area:
        request["area"] = args.area
    if args.grid:
        request["grid"] = args.grid

    return request


def target_path(args, year, month):
    """Build the output file path for one year-month."""
    is_daily = args.dataset in DAILY_STATS_DATASETS
    ext = "zip" if is_daily else ("nc" if args.data_format == "netcdf" else "grib")
    prefix = args.dataset.replace("reanalysis-", "").replace("derived-", "")
    return os.path.join(args.output_dir, f"{prefix}_{year}_{month:02d}.{ext}")


def download_one(client, dataset, request, target):
    """Download one request. Returns status message."""
    if os.path.exists(target):
        return f"Skipped (exists): {target}"
    try:
        client.retrieve(dataset, request, target)
        return f"Downloaded: {target}"
    except Exception as e:
        return f"ERROR ({target}): {e}"


def main():
    args = parse_args()

    # Validate daily-stats requirements
    if args.dataset in DAILY_STATS_DATASETS and not args.daily_statistic:
        raise SystemExit(f"--daily-statistic required for {args.dataset}")

    os.makedirs(args.output_dir, exist_ok=True)
    client = cdsapi.Client()

    tasks = [
        (y, m)
        for y in range(args.years[0], args.years[1] + 1)
        for m in args.months
    ]

    if args.workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(args.workers, 4)) as pool:
            futures = {
                pool.submit(
                    download_one, client, args.dataset,
                    build_request(args, y, m), target_path(args, y, m),
                ): (y, m)
                for y, m in tasks
            }
            for future in as_completed(futures):
                print(future.result())
    else:
        for y, m in tasks:
            req = build_request(args, y, m)
            tgt = target_path(args, y, m)
            print(f"Requesting {y}-{m:02d}...")
            print(f"  {download_one(client, args.dataset, req, tgt)}")

    print("Done.")


if __name__ == "__main__":
    main()
