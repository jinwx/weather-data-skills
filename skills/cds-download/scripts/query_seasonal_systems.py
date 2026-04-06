#!/usr/bin/env python3
"""Summarize seasonal system coverage for one centre.

This script is intentionally narrow: it supports the monthly atmospheric and
postprocessed seasonal datasets used in Step 3 of references/seasonal.md.
It queries exact available (year, month) pairs from the CDS constraints API,
then summarizes each system in two groups:

- hindcast: months before 2017
- forecast: months from 2017 onward
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SUPPORTED_DATASETS = {
    "seasonal-monthly-single-levels",
    "seasonal-monthly-pressure-levels",
    "seasonal-postprocessed-single-levels",
    "seasonal-postprocessed-pressure-levels",
}
CONSTRAINTS_URL = "https://cds.climate.copernicus.eu/api/retrieve/v1/processes/{dataset}/constraints"
REQUEST_TIMEOUT_SECONDS = 60
FORECAST_START_YEAR = 2017
DEFAULT_OUTPUT_DIR = "seasonal-query-output"


def query_constraints(dataset: str, inputs: dict[str, list[str]]) -> dict[str, list[str]]:
    payload = json.dumps({"inputs": inputs}).encode()
    request = urllib.request.Request(
        CONSTRAINTS_URL.format(dataset=dataset),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace").strip()
        raise SystemExit(f"CDS request failed with HTTP {exc.code}: {message or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"CDS request failed: {exc.reason}") from exc


def query_systems(dataset: str, centre: str, product_type: str) -> list[str]:
    response = query_constraints(
        dataset,
        {
            "originating_centre": [centre],
            "product_type": [product_type],
        },
    )
    return sorted(response["system"], key=int)


def query_available_months(
    dataset: str,
    centre: str,
    system: str,
    product_type: str,
    workers: int,
) -> list[str]:
    base_inputs = {
        "originating_centre": [centre],
        "system": [system],
        "product_type": [product_type],
    }
    response = query_constraints(dataset, base_inputs)
    years = sorted(response["year"], key=int)

    if not years:
        return []

    def fetch_year(year: str) -> list[str]:
        year_response = query_constraints(dataset, {**base_inputs, "year": [year]})
        year_months = sorted(year_response["month"], key=int)
        return [f"{year}-{month}" for month in year_months]

    months: list[str] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(years))) as pool:
        for year_months in pool.map(fetch_year, years):
            months.extend(year_months)
    return months


def build_segments(months: list[str]) -> list[dict[str, str]]:
    if not months:
        return []

    segments: list[dict[str, str]] = []
    start = months[0]
    previous_year, previous_month = [int(part) for part in months[0].split("-")]

    for ym in months[1:]:
        year, month = [int(part) for part in ym.split("-")]
        if year * 12 + month != previous_year * 12 + previous_month + 1:
            segments.append({"start": start, "end": f"{previous_year:04d}-{previous_month:02d}"})
            start = ym

        previous_year = year
        previous_month = month

    segments.append({"start": start, "end": f"{previous_year:04d}-{previous_month:02d}"})
    return segments


def summarize_period(months: list[str]) -> dict[str, Any] | None:
    if not months:
        return None

    first = months[0]
    last = months[-1]
    first_year, first_month = [int(part) for part in first.split("-")]
    last_year, last_month = [int(part) for part in last.split("-")]
    span_length = (last_year - first_year) * 12 + (last_month - first_month) + 1
    return {
        "first": first,
        "last": last,
        "span_coverage": round(len(months) / span_length, 3),
    }


def build_payload(
    dataset: str, centre: str, product_type: str, workers: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    systems = query_systems(dataset, centre, product_type)
    if not systems:
        raise SystemExit(
            f"No systems found for centre '{centre}' in dataset '{dataset}' with product_type '{product_type}'."
        )

    header = {"centre": centre, "dataset": dataset, "product_type": product_type}
    detail_systems: list[dict[str, Any]] = []
    summary_systems: list[dict[str, Any]] = []
    for system in systems:
        months = query_available_months(dataset, centre, system, product_type, workers)
        hindcast_months = [m for m in months if int(m.split("-")[0]) < FORECAST_START_YEAR]
        forecast_months = months[len(hindcast_months):]
        detail_system = {
            "system": system,
            "hindcast": summarize_period(hindcast_months),
            "forecast": summarize_period(forecast_months),
            "segments": build_segments(months),
        }
        detail_systems.append(detail_system)
        summary_systems.append({key: value for key, value in detail_system.items() if key != "segments"})

    return (
        {**header, "systems": detail_systems},
        {**header, "systems": summary_systems},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize hindcast/forecast coverage for seasonal systems at one centre."
    )
    parser.add_argument("--centre", required=True, help="Single centre (for example: ecmwf)")
    parser.add_argument(
        "--dataset",
        default="seasonal-monthly-single-levels",
        choices=sorted(SUPPORTED_DATASETS),
        help="CDS dataset ID (default: seasonal-monthly-single-levels)",
    )
    parser.add_argument(
        "--product-type",
        default="monthly_mean",
        help="Exact product_type to query (default: monthly_mean)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Parallel year queries per system (default: 8)",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Write detail JSON to this working-directory folder (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    detail_payload, summary_payload = build_payload(args.dataset, args.centre, args.product_type, args.workers)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{args.centre}.json").write_text(json.dumps(detail_payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary_payload, indent=2))


if __name__ == "__main__":
    main()
