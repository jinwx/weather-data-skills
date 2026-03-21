---
name: cds-download
description: >
  Download climate/weather data from the Copernicus Climate Data Store (CDS) using the CDS API.
  Use this skill whenever the user wants to download ERA5, ERA5-Land, seasonal forecasts,
  or any other CDS dataset. Also use it when the user mentions CDS, Climate Data Store,
  ECMWF reanalysis, cdsapi, .cdsapirc, or asks about downloading climate/weather reanalysis
  data — even if they don't say "CDS" explicitly. Covers: writing efficient download scripts,
  choosing the right dataset, configuring API access, optimizing request splitting, and
  selecting data formats (NetCDF vs GRIB).
---

# CDS Data Download Skill

This skill helps users download data from the Copernicus Climate Data Store (CDS) efficiently. It covers setup, dataset selection, and writing optimized Python download scripts.

## Quick Orientation

The CDS (https://cds.climate.copernicus.eu) is the main portal for Copernicus climate data.

**Reference files** — read the relevant one when you need dataset-specific details:
- `references/api-setup.md` — Account setup, .cdsapirc configuration, cdsapi installation. Read this when the user needs help getting started or has authentication issues.
- `references/era5.md` — ERA5 and ERA5-Land datasets: identifiers, variables, storage types, efficiency strategies, and download script usage. Read this for any ERA5/ERA5-Land download task.
- `references/seasonal.md` — Seasonal forecast datasets: identifiers, parameters, system versioning, efficiency strategies, and download script usage. Read this for seasonal prediction downloads.

A `scripts/` directory contains reusable download scripts for ERA5 and seasonal forecasts — see the reference files for usage. These scripts cover the common ERA5/ERA5-Land and C3S seasonal forecast workflows. For other CDS datasets, unsupported parameter combinations, or custom post-processing, read the relevant script source as a reference and write a tailored script.

## Workflow

When a user asks to download CDS data, follow this sequence:

### 1. Check Setup

Before writing any download script, confirm the user has CDS access configured:
- Do they have a CDS account? If not, direct them to register at https://cds.climate.copernicus.eu
- Is their `.cdsapirc` file configured? If unsure, read `references/api-setup.md` for the current format and walk them through it.
- Is `cdsapi` installed (`pip install "cdsapi>=0.7.7"`)? The version matters — older versions use incompatible syntax.

If the user seems experienced (they mention specific dataset names, already have scripts), skip the hand-holding and go straight to their request.

### 2. Identify the Right Dataset

If the user isn't sure which dataset they need, help them narrow it down. The CDS catalog (https://cds.climate.copernicus.eu/datasets) has hundreds of datasets organized by these dimensions:

**Product type** — What kind of data?
- **Reanalysis** — Gridded historical reconstruction of the atmosphere/land/ocean. Best for "what actually happened" questions. (e.g., ERA5, ERA5-Land)
- **Seasonal forecasts** — Multi-month predictions from coupled models. Best for "what is expected" questions.
- **Climate projections** — Long-term future scenarios (CMIP-based).
- **Satellite observations** — Remotely sensed measurements.
- **In-situ observations** — Ground station and radiosonde data.
- **Derived reanalysis** — Post-processed products like climate indicators, agrometeorological indices.

**Variable domain** — What part of the Earth system?
- Atmosphere (surface / upper air / composition)
- Land (physics / hydrology / biosphere / cryosphere)
- Ocean (physics / biology / biochemistry)

**Spatial coverage** — Global or regional (Europe, Arctic, Antarctic)?

**Temporal coverage** — Past, present, or future?

Walk the user through these questions to narrow down the right dataset. If they already know the general category (e.g., "I need reanalysis surface temperature"), you can go straight to the reference file. If the search is open-ended, browse the CDS catalog together or fetch the catalog page to find matching datasets.

For datasets not covered by the reference files, go to `https://cds.climate.copernicus.eu/datasets/<dataset-identifier>` to check the dataset description and download form. The "Show API request code" button on the download form generates correct API syntax — use this as the authoritative source for variable names and parameter formats.

### 3. Write an Efficient Download Script

This is where most of the value lies. **Read the relevant dataset reference file first** — each one contains dataset-specific efficiency strategies. The optimal request structure varies significantly between datasets because they use different storage backends and archival layouts.

General principles that apply to all CDS downloads:
- **Use `area` to subset geographically** when the user doesn't need global data
- **Use `grid` to request coarser resolution** if full resolution isn't needed
- **Make scripts resumable** — check if output files already exist before requesting
- **Put configuration at the top** of the script so users can modify parameters without reading the download logic
- **Handle errors gracefully** — wrap API calls in try/except so one failed request doesn't kill the whole batch
- **Never mix atmospheric, wave, and ensemble data** in one NetCDF request (different grids cause conversion errors)

For dataset-specific efficiency (request splitting, parallelization, grouping strategies), always consult the reference file. What works for ERA5 (split by month) can be counterproductive for seasonal forecasts (combine into fewer, larger requests).

### 4. Format Choice: NetCDF vs GRIB

Help the user choose if they're unsure:

| | NetCDF | GRIB |
|---|---|---|
| **Best for** | Analysis in Python (xarray), sharing | Operational meteorology, WRF input |
| **Ecosystem** | xarray, netCDF4, pandas | cfgrib, eccodes, wgrib2 |
| **File size** | Larger | Smaller (packed) |
| **Readability** | Self-describing, easy to inspect | Requires specialized tools |
| **CDS default** | No (must specify) | Yes |

**Default recommendation**: NetCDF for most research users, GRIB for operational/NWP workflows. Note that some datasets (e.g., seasonal forecasts) work better in their native GRIB format — NetCDF conversion can be lossy or slow.

### 5. Verify Before Downloading

Before finalizing any script, verify key details. The CDS API will reject requests with invalid parameter names, so accuracy matters:

- **For seasonal forecasts — use the constraints API**: System versions, temporal coverage, and product type availability vary greatly across centres. **Always query the CDS constraints API** to check what's available before writing a download script. See `references/seasonal.md` for details and code examples. This is far more reliable than hardcoding system versions.
- **For other datasets — check the download form**: Go to the dataset page on CDS (e.g., `https://cds.climate.copernicus.eu/datasets/<dataset-identifier>`) and use the download form. The **"Show API request code"** button at the bottom generates correct, verified API syntax.
- **Check temporal coverage**: Different datasets have different start dates.
- **Check available levels/variables**: Available options vary by dataset.

## Common Issues

- **Authentication errors**: User likely has an outdated `.cdsapirc` or old cdsapi version. See `references/api-setup.md`.
- **Very slow downloads**: Check the dataset's storage type. Read the relevant reference file for dataset-specific efficiency strategies.
- **Request failures**: Often caused by invalid variable names or parameter combinations. Verify against the CDS download form's "Show API request code" button.
- **License errors**: User needs to accept the dataset license on the CDS web interface (bottom of the download form) before API downloads work. This is a one-time step per dataset.
