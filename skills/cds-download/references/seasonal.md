# Seasonal Forecast Datasets

## Dataset Catalog

| CDS Identifier | Description | Temporal Res | Storage |
|---|---|---|---|
| `seasonal-monthly-single-levels` | Monthly statistics (means, etc.) on single levels | Monthly | MARS external (tape) |
| `seasonal-monthly-pressure-levels` | Monthly statistics on pressure levels | Monthly | MARS external (tape) |
| `seasonal-original-single-levels` | Daily/sub-monthly data on single levels | Daily | MARS external (tape) |
| `seasonal-original-pressure-levels` | Daily/sub-monthly data on pressure levels | Daily | MARS external (tape) |

### When to Use Which

- **Monthly means / anomalies**: Use `seasonal-monthly-*` — these are pre-aggregated and much smaller to download
- **Daily extremes or sub-monthly variability**: Use `seasonal-original-*` — full temporal resolution but much larger

## System Versioning — Critical Background

Seasonal forecast data is produced by multiple centres, each running their own model. Centres periodically upgrade their forecast systems, creating new "system" versions. This has major implications for downloading data:

### Hindcasts vs Real-Time Forecasts

Each system version produces two types of data:

- **Hindcasts (re-forecasts)**: Retrospective runs over a historical period (typically 1993–2016, some centres go back to 1981). Used for bias correction and skill assessment. Produced once when the system is set up.
- **Real-time forecasts**: Operational forecasts from the date the system went live until it was replaced by a newer version.

**Critical rule**: Hindcasts and real-time forecasts **must** come from the same system version for bias correction. Never mix system 5 hindcasts with system 51 real-time data — they may have different grids or model physics.

### Product Type Coverage Differs

Not all product types cover the same years within a system:

- **`ensemble_mean`** and **`hindcast_climate_mean`**: Typically only available for real-time forecast years (e.g., 2017 onward for ECMWF system 51). These are pre-computed summaries.
- **`monthly_mean`** (individual member statistics): Available for the full date range including hindcast years (e.g., 1981–present for ECMWF).

**If you need long-term data, you must use `monthly_mean` (individual members), not `ensemble_mean`**, even if you only want the ensemble mean. You can compute the mean yourself from the individual members.

### Using the Constraints API to Check Availability

**Always use the CDS constraints API before writing a download script** to verify which system/year/month/product_type combinations actually have data. The `scripts/cds_utils.py` module provides `query_constraints()` and `find_latest_system()` for this purpose.

The constraints API endpoint:
```
POST https://cds.climate.copernicus.eu/api/retrieve/v1/processes/{dataset-id}/constraints
Content-Type: application/json

{"inputs": {"originating_centre": ["ecmwf"], "system": ["51"], "product_type": ["monthly_mean"]}}
```

Pass a partial selection; the response contains valid values for all remaining parameters. No authentication required.

**Usage pattern**: Before downloading, run 1–2 constraint queries:
1. What systems exist for the centre: `{"inputs": {"originating_centre": ["<centre>"]}}`
2. What years/months are available: `{"inputs": {"originating_centre": ["<centre>"], "system": ["<sys>"], "product_type": ["<type>"]}}`

You can also query via `curl`:
```bash
curl -s -X POST \
  "https://cds.climate.copernicus.eu/api/retrieve/v1/processes/seasonal-monthly-single-levels/constraints" \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"originating_centre": ["ecmwf"], "system": ["51"]}}' \
  | python3 -m json.tool
```

**Important**: The constraints API returns flat lists of valid values per parameter. When querying without a year filter, the returned `month` list is the union across all years — not every (year, month) pair may be valid. To get exact months for a specific year, include `"year": ["2025"]` in the query. This is especially relevant for centres like UKMO where systems are activated mid-year.

The static constraints endpoint (`GET .../constraints.json`) returns every valid parameter combination as a JSON array — useful for a complete availability map, but the response is large.

### System Version Reference

Centres and their systems (as of early 2026):

| Centre | Current System | Previous Systems | Hindcast Start | Notes |
|---|---|---|---|---|
| ECMWF | `51` (Nov 2022–) | `5` (Nov 2017–Oct 2022), `4` (Sep–Oct 2017) | 1981 | Cleanest pattern. sys 51 changed grid interpolation vs sys 5. |
| Meteo-France | `9` (May 2025–) | `8`, `7`, `6`, `5` | 1993 | Hindcast end varies by system (sys 9: to 2024). |
| UKMO | `605` (Mar 2026–) | `604`, `603`, `602`, `601`, `600`, `15`, `14`, `13`, `12` | 1993 | On-the-fly hindcasts — each system number has its own hindcast set. Very complex. Jan 1993 missing for all UKMO systems. |
| DWD | `22` (Apr 2025–) | `21`, `2` | 1993 | |
| CMCC | `4` (Aug 2025–) | `35`, `3` | 1993 | |
| NCEP | `2` (Oct 2019–) | — | 1993 | Single system, stable. |
| JMA | — | `3` (Feb 2022–Feb 2026), `2` | 1993 (sys 3), 1981 (sys 2) | Discontinued from C3S multi-system Feb 2026. |
| ECCC | `4` & `5` (Jul 2024–) | `3`, `2`, `1` | 1993 | Two sub-models run in parallel (CanESM5.1p1bc + GEM5.2-NEMO). |
| BOM | `2` (May 2025–) | — | 1993 | Recently joined C3S. |

**These version numbers change over time.** Always verify against the constraints API rather than relying on this table for the latest values.

For the full real-time system timeline (which system was active each month for each centre), see: https://confluence.ecmwf.int/display/CKB/Summary+of+available+data

## Download Strategies

Downloading a consistent long-term seasonal forecast dataset (e.g., 1993–2025) is complicated because system versions change. The `scripts/query_seasonal_plan.py` script automates the planning step for Strategy A and B below.

### Strategy A: Single-System (Simplest, Recommended)

Pick one system version and download all data it covers. The latest system typically has hindcasts covering 1993–2016 (or longer) plus real-time forecasts from activation to present. This gives an **internally consistent** dataset — same model physics throughout.

```bash
python scripts/query_seasonal_plan.py --centre ecmwf -o plan.json
```

### Strategy B: Maximum Coverage (Best for ML/Data-Driven Work)

When temporal coverage matters more than strict single-system consistency:

1. Use the **latest system's hindcasts** for the historical period (typically 1993–2016)
2. **Chain real-time data** from successive systems for 2017 onward, preferring the newer system for overlapping months

For centres like ECMWF where the latest system already covers 1981–present, this collapses to Strategy A. Chaining is primarily needed for centres like UKMO where each system covers only 1–2 real-time years.

```bash
python scripts/query_seasonal_plan.py --centre ukmo --strategy max-coverage -o plan.json
```

### Strategy C: Chained Systems (Strict Real-Time Only)

Cover only the real-time period (2017–present) with each system's operational data, plus hindcasts from one system for bias correction. Data from different systems is **not directly comparable** without recalibration. Build this plan manually or adapt the max-coverage script.

### Strategy D: Multi-Centre Ensemble

Download from multiple centres for the same period. The common hindcast period across all centres is typically **1993–2016**.

```bash
python scripts/query_seasonal_plan.py \
    --centres ecmwf meteo_france dwd cmcc ukmo -o plan.json
```

## Key Parameters

Seasonal forecast requests have unique parameters compared to ERA5:

- **`originating_centre`**: `ecmwf`, `meteo_france`, `dwd`, `cmcc`, `ukmo`, `ncep`, `jma`, `eccc`, `bom`
- **`system`**: Model version number. **Always verify with the constraints API** — these change when centres upgrade.
- **`leadtime_month`**: Forecast lead time in months. Values 1–6 are typical; some centres provide longer.
- **`product_type`**:
  - `monthly_mean` — per-member monthly mean (available for both hindcast and real-time years)
  - `monthly_maximum` / `monthly_minimum` / `monthly_standard_deviation` — per-member statistics
  - `ensemble_mean` — pre-computed ensemble mean (often only for real-time years)
  - `hindcast_climate_mean` — climatological mean from the hindcast period

## Efficiency Tips

Seasonal forecast data is stored on tape, so efficient request construction matters — but the strategy is **very different from ERA5**.

### Combine as much as possible into each request

Unlike ERA5 (split by month), seasonal forecast efficiency means **maximizing what you request from the same tape**. In each request, combine:
- All **variables** you need
- All **pressure levels** (for pressure-level datasets)
- All **product types**
- All **leadtime months**

### Split on initialization date

Each initialization month (year + month) sits on a different tape. Use **separate requests per initialization date**. The download scripts handle this automatically.

### Other tips

- **Expect slow retrieval**: Tape-based data can take hours.
- **Use monthly statistics when possible**: `seasonal-monthly-*` is much smaller than `seasonal-original-*`.
- **GRIB is strongly recommended**: Native format. NetCDF conversion is experimental — can be slow and lossy.
- **Test request size via the web form first**: The CDS download form warns when requests are too large.

Reference: https://confluence.ecmwf.int/display/CKB/Recommendations+and+efficiency+tips+for+C3S+seasonal+forecast+datasets

## Download

After building a plan with `scripts/query_seasonal_plan.py` (see strategy examples above), download with:

```bash
python scripts/download_seasonal.py --plan plan.json \
    --variables 2m_temperature total_precipitation \
    --leadtime-months 1 2 3 4 5 6 \
    --format grib \
    -o ./seasonal_data
```

Options: `--area N W S E` for geographic subset, `--workers 2` for parallelism (max recommended: 4).

## Documentation Links

- Seasonal forecasts overview: https://confluence.ecmwf.int/display/CKB/Seasonal+forecasts
- Summary of available data (system timeline): https://confluence.ecmwf.int/display/CKB/Summary+of+available+data
- Start dates per forecast system: https://confluence.ecmwf.int/display/CKB/Start+dates+available+in+the+CDS+per+forecast+system
- C3S seasonal forecast documentation: https://climate.copernicus.eu/seasonal-forecasts
- CDS dataset pages:
  - https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels
  - https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels
- Efficiency tips: https://confluence.ecmwf.int/display/CKB/Recommendations+and+efficiency+tips+for+C3S+seasonal+forecast+datasets
