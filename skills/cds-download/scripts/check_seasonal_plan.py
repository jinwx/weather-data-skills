#!/usr/bin/env python3
"""Check a seasonal download plan against saved coverage JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_COVERAGE_DIR = "seasonal-query-output"


def ym_index(value: str) -> int:
    year_text, month_text = value.split("-")
    year = int(year_text)
    month = int(month_text)
    if len(year_text) != 4 or len(month_text) != 2 or not 1 <= month <= 12:
        raise ValueError(value)
    return year * 12 + month - 1


def build_coverage(
    coverage_dir: Path, dataset: str, product_type: str, centres: list[str],
) -> dict[str, dict[str, list[tuple[int, int]]]]:
    coverage: dict[str, dict[str, list[tuple[int, int]]]] = {}

    for centre in centres:
        path = coverage_dir / f"{centre}.json"
        coverage_json = json.loads(path.read_text(encoding="utf-8"))
        if coverage_json["dataset"] != dataset or coverage_json["product_type"] != product_type:
            raise SystemExit(f"{path} does not match dataset/product_type in plan")

        coverage[centre] = {
            item["system"]: [
                (ym_index(segment["start"]), ym_index(segment["end"]))
                for segment in item["segments"]
            ]
            for item in coverage_json["systems"]
        }

    return coverage


def check_plan(plan: dict[str, Any], coverage_dir: Path) -> list[str]:
    dataset = plan["dataset"]
    product_type = plan["product_type"]
    centres = plan["centres"]
    coverage = build_coverage(
        coverage_dir,
        dataset,
        product_type,
        sorted(item["centre"] for item in centres),
    )
    errors: list[str] = []

    for centre_item in centres:
        centre = centre_item["centre"]
        previous_end: int | None = None

        for index, item in enumerate(centre_item["segments"], start=1):
            system = item["system"]
            start = item["start"]
            end = item["end"]
            start_index = ym_index(start)
            end_index = ym_index(end)

            if start_index > end_index:
                errors.append(f"{centre} segment {index} has start after end")
                continue
            if previous_end is not None and start_index <= previous_end:
                errors.append(f"{centre} segment {index} overlaps the previous segment or is out of order")
                continue

            previous_end = end_index
            available = coverage[centre].get(system)
            if not available:
                errors.append(f"{centre} segment {index} uses unknown system {system}")
            elif not any(seg_start <= start_index and end_index <= seg_end for seg_start, seg_end in available):
                errors.append(f"{centre} segment {index} is not fully available for system {system}: {start}..{end}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check a seasonal download plan.")
    parser.add_argument("--plan", required=True, help="Plan JSON to check")
    parser.add_argument(
        "--coverage-dir",
        default=DEFAULT_COVERAGE_DIR,
        help=f"Folder containing per-centre coverage JSON (default: {DEFAULT_COVERAGE_DIR})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan_json = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    errors = check_plan(plan_json, Path(args.coverage_dir))
    report: dict[str, Any] = {"ok": not errors}
    if errors:
        report["errors"] = errors
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
