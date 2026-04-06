# Seasonal Forecast Datasets

## Step 1: Choose the Dataset

- Monthly statistics of absolute values (most common starting point)
  - `seasonal-monthly-single-levels`
  - `seasonal-monthly-pressure-levels`

- Daily/subdaily resolution. Use only when you need daily or sub-daily variability.
  - `seasonal-original-single-levels`
  - `seasonal-original-pressure-levels`

- Monthly anomalies (departures from each system's climatology over `1993-2016`).
  - `seasonal-postprocessed-single-levels`
  - `seasonal-postprocessed-pressure-levels`

- Ocean sub-surface and circulation variables (e.g. depth-resolved temperature/salinity, mixed layer depth, ocean currents).
  - `seasonal-monthly-ocean`

## Step 2: Inspect Schema and Confirm Selectors

For a candidate dataset, the Agent may query its parameter schema:

```
GET https://cds.climate.copernicus.eu/api/retrieve/v1/processes/{dataset-id}
```

The response `inputs` object lists every parameter with its full enum of valid values. No authentication is required. Use this object to identify the selectors that matter for the dataset. This step is only for understanding the request shape. Actual availability is resolved in Step 3 via the constraints API. For familiar monthly atmospheric workflows, if the required selectors are already clear from this guide, the Agent may skip this query.

### Key parameters of monthly datasets

> **Hindcasts vs forecasts.** Hindcasts (re-forecasts) are retrospective runs over a historical period. Forecasts are operational runs produced after a system goes live. For monthly datasets, hindcasts generally end in 2016 and forecasts begin from 2017 onwards.

**`product_type`** (on `seasonal-monthly-*` and `seasonal-postprocessed-*`):

`monthly_mean` is the primary product type. It provides per-member monthly means and is the only product type that spans both hindcasts and forecasts — **use it whenever you need hindcast data**. Compute ensemble statistics or anomalies yourself.

Other product types:
- `monthly_maximum` / `monthly_minimum` / `monthly_standard_deviation` — extra per-member statistics, `seasonal-monthly-single-levels` only. Same coverage as `monthly_mean`.
- `ensemble_mean` — mean across all members of `monthly_mean`. Forecast years only.
- `hindcast_climate_mean` — climatology (ensemble mean over 1993–2016 hindcasts) for each `system` + nominal start `month` + `leadtime_month`. Only on `seasonal-monthly-*`. Must request a forecast year (≥2017), but the result is year-invariant — any single valid year returns the same climatology.

Additional notes:

- `seasonal-postprocessed-*` = `seasonal-monthly-*` minus `hindcast_climate_mean`, for both `monthly_mean` and `ensemble_mean`.
- `seasonal-monthly-ocean` has no `product_type`; it uses `forecast_type` (`hindcast` or `forecast`) instead.
- `seasonal-original-*` has neither `product_type` nor `forecast_type`.

### Confirm selections before proceeding

Before moving to Step 3, confirm the following with the user (or infer from their requirements):
- Which `originating_centre`(s) to include.
- Which `product_type` or `forecast_type` to use.
- The desired time range (years/months).

These choices determine what system versions need to be resolved in Step 3.

## Step 3: Version Selection and Plan

Seasonal forecast data is versioned by `system`. A long record for one centre may span multiple systems with overlapping coverage, mid-year transitions, or parallel current systems.

This step uses two scripts that work with `seasonal-monthly-*` and `seasonal-postprocessed-*` datasets. For `seasonal-original-*` and `seasonal-monthly-ocean`, the Agent can follow this process as a reference but should query and plan manually.

### 3a. Query system coverage

First confirm the user's version-selection preference. Common choices include:
- **Use a fixed system** — specify a single system for the entire time range.
- **Let the Agent decide** — the Agent proposes a mapping based on heuristics (prefer newest system, prefer fewer systems, fall back to older systems only when coverage is missing).
- **Provide their own mapping** — the user specifies which system to use for which period.

Then run `scripts/query_seasonal_systems.py` for each centre:

```bash
python scripts/query_seasonal_systems.py \
    --dataset seasonal-monthly-single-levels \
    --centre ecmwf \
    --product-type monthly_mean \
    [--workers 8] \
    [--output-dir seasonal-query-output]
```

Output:

```json
{
  "centre": "ecmwf",
  "dataset": "seasonal-monthly-single-levels",
  "product_type": "monthly_mean",
  "systems": [
    {
      "system": "4",
      "hindcast": {"first": "1993-09", "last": "2015-10", "span_coverage": 0.173},
      "forecast": {"first": "2017-09", "last": "2017-10", "span_coverage": 1.0}
    },
    ...
  ]
}
```

Fields:
- `hindcast` / `forecast`: summary for months before 2017 / from 2017 onward. Either field may be `null` if the system has no data in that period.
- `first` / `last`: first and last `(year, month)` with data in that period.
- `span_coverage`: fraction of months with data in the `first`–`last` span (1.0 = no gaps). A quick density hint; inspect `segments` in the detail JSON for exact coverage.

The script also writes a per-centre detail JSON file (default: `seasonal-query-output/{centre}.json` in the working directory). In that file, each system also includes `segments`: exact contiguous `(year, month)` ranges for the full record.

Use the stdout summary first. If coverage is simple, it may already be enough. If systems overlap, have gaps, or show low `span_coverage`, read the detail JSON and use `segments` to decide where systems switch.

### 3b. Compile the plan

Once the version-selection decision is made, write a plan JSON that maps each centre's time range to specific systems. Within each centre, segments must be ordered by `start` and must not overlap. Prefer the newest system with coverage; fall back to older systems only for periods the newer one does not cover.

```json
{
  "dataset": "seasonal-monthly-single-levels",
  "product_type": "monthly_mean",
  "centres": [
    {
      "centre": "ecmwf",
      "segments": [
        {"system": "51", "start": "1981-01", "end": "2026-03"}
      ]
    },
    {
      "centre": "ukmo",
      "segments": [
        {"system": "603", "start": "1993-01", "end": "2025-02"},
        {"system": "604", "start": "2025-03", "end": "2026-02"}
      ]
    }
  ]
}
```

Then validate the plan against the saved 3a coverage data:

```bash
python scripts/check_seasonal_plan.py \
    --plan plan.json \
    --coverage-dir seasonal-query-output
```

The checker validates:
- per-centre segment order and non-overlap
- that every segment is fully covered by the saved 3a `segments`

If `ok` in the output JSON is true, report the plan to the user together with the remaining download parameters identified in Step 2 (variables, leadtime, format, area, etc.). Proceed to Step 4 once the user agrees.

## Step 4: Download

This step uses `download_seasonal.py`, which works with `seasonal-monthly-*` and `seasonal-postprocessed-*` datasets. For `seasonal-original-*` and `seasonal-monthly-ocean`, use this process only as a reference and query and plan manually.

```bash
python scripts/download_seasonal.py \
    --plan plan.json \
    --variables VAR [VAR ...] \
    --leadtime-months 1 2 3 4 5 6 \
    [--pressure-levels 500 850 ...] \
    --format grib \
    [--area N W S E] \
    [-o ./seasonal_data] \
    [--workers 4]
```

Each file is downloaded to `*.downloading` first, then renamed after completion. This avoids leaving an incomplete final file when CDS creates an empty target before data transfer finishes.

### Efficiency tips

CDS stores seasonal data in "leaves" — data cubes defined by a set of fixed selectors. Parameters within a leaf can be requested together efficiently; parameters that split leaves cannot.

| Dataset family | Leaf-splitting selectors | Within one leaf |
|---|---|---|
| `seasonal-monthly-*`, `seasonal-postprocessed-*` | `originating_centre`, `product_type`, `system`, `year` | `month`, `leadtime_month`, `variable` (+ `pressure_level`) |
| `seasonal-original-*` | `originating_centre`, `system`, `year`, `month`, `day` | `leadtime_hour`, `variable` (+ `pressure_level`) |
| `seasonal-monthly-ocean` | `forecast_type`, `originating_centre`, `system`, `year` | `month`, `variable` |

Keep all leaf-splitting selectors fixed within one request. Combine as many within-leaf parameters as practical. How to split requests across leaves (e.g. one request per year vs. per month) is up to the Agent — consider the plan's system boundaries and request size.

References:
- ECMWF efficiency note: https://confluence.ecmwf.int/display/CKB/Recommendations+and+efficiency+tips+for+C3S+seasonal+forecast+datasets
- ECMWF seasonal catalogue leaf browser: https://apps.ecmwf.int/data-catalogues/c3s-seasonal/?class=c3

## Documentation Links

- C3S Seasonal Forecasts: https://confluence.ecmwf.int/display/CKB/C3S+Seasonal+Forecasts
- Summary of available data: https://confluence.ecmwf.int/display/CKB/Summary+of+available+data
- Start dates available in the CDS per forecast system: https://confluence.ecmwf.int/display/CKB/Start+dates+available+in+the+CDS+per+forecast+system
- CDS dataset pages:
  - https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels
  - https://cds.climate.copernicus.eu/datasets/seasonal-monthly-pressure-levels
  - https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels
  - https://cds.climate.copernicus.eu/datasets/seasonal-original-pressure-levels
  - https://cds.climate.copernicus.eu/datasets/seasonal-postprocessed-single-levels
  - https://cds.climate.copernicus.eu/datasets/seasonal-postprocessed-pressure-levels
  - https://cds.climate.copernicus.eu/datasets/seasonal-monthly-ocean
