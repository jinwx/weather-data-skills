# ERA5 and ERA5-Land Datasets

## Dataset Catalog

### ERA5 (Atmosphere, 0.25° resolution)

| CDS Identifier | Time Scale | Storage | Temporal Coverage |
|---|---|---|---|
| `reanalysis-era5-single-levels` | Hourly | CDS disk (fast) | 1940–present |
| `reanalysis-era5-pressure-levels` | Hourly | CDS disk (fast) | 1940–present |
| `derived-era5-single-levels-daily-statistics` | Daily (computed on-the-fly) | CDS disk (fast) | 1940–present |
| `reanalysis-era5-single-levels-monthly-means` | Monthly | CDS disk (fast) | 1940–present |
| `reanalysis-era5-pressure-levels-monthly-means` | Monthly | CDS disk (fast) | 1940–present |
| `reanalysis-era5-complete` | Hourly | Tape (slow) | 1940–present |

### ERA5-Land (Land surface, 0.1° resolution)

| CDS Identifier | Time Scale | Storage | Temporal Coverage |
|---|---|---|---|
| `reanalysis-era5-land` | Hourly | CDS disk (fast) | 1950–present |
| `derived-era5-land-daily-statistics` | Daily (computed on-the-fly) | CDS disk (fast) | 1950–present |
| `reanalysis-era5-land-monthly-means` | Monthly | CDS disk (fast) | 1950–present |

**Key difference**: ERA5-Land has finer resolution (0.1° ≈ 9 km vs 0.25° ≈ 28 km) but only covers land surface variables — no atmospheric profiles, no ocean.

### Choosing a Dataset

- **Surface weather** (temperature, wind, precipitation, radiation): `reanalysis-era5-single-levels`
- **Atmospheric profiles** (upper-air temperature, wind, humidity, geopotential): `reanalysis-era5-pressure-levels`
- **Land hydrology** (soil moisture, snow, runoff, lake temperature): `reanalysis-era5-land`
- **Daily aggregates** (daily mean/min/max/sum without downloading hourly): `derived-era5-*-daily-statistics`
- **Model-level data** (full vertical resolution, rare): `reanalysis-era5-complete`
- **Climatological means** (long-term averages): `*-monthly-means` variants

## Time Scale Differences

### Hourly datasets
Standard ERA5 — request specific hours via the `time` parameter. This is the native resolution.

### Daily statistics datasets
These compute daily aggregates **on-the-fly** from hourly data. They have a different API format with extra required parameters:

| Parameter | Values | Notes |
|---|---|---|
| `daily_statistic` | `daily_mean`, `daily_minimum`, `daily_maximum`, `daily_sum` | Required. `daily_sum` only for accumulated variables (precipitation, radiation, etc.) and only for single-levels (not ERA5-Land). |
| `frequency` | `1_hourly`, `3_hourly`, `6_hourly` | Sub-daily sampling used to compute the statistic. |
| `time_zone` | `utc-12:00` through `utc+14:00` | Defines what constitutes a "day". Default: `utc+00:00`. |

Key differences from hourly datasets:
- **No `time` parameter** (output is one value per day)
- **No `data_format` or `download_format` choice** — always outputs NetCDF in a zip archive
- **No pressure-level variant** — only single-levels and ERA5-Land
- **Slower than hourly** because aggregation is computed at retrieval time (not pre-stored)

For large-scale daily data, it may be more efficient to download hourly data and aggregate locally.

### Monthly means datasets
Pre-computed monthly averages. No `day` or `time` parameters needed — just `year` and `month`.

## Commonly Used Variables

### Single Levels (surface)
- `2m_temperature` — near-surface air temperature
- `10m_u_component_of_wind`, `10m_v_component_of_wind` — 10m wind
- `total_precipitation` — accumulated precipitation
- `mean_sea_level_pressure` — MSLP
- `surface_pressure`
- `2m_dewpoint_temperature`
- `sea_surface_temperature`
- `total_cloud_cover`
- `surface_solar_radiation_downwards`
- `surface_thermal_radiation_downwards`

### Pressure Levels
- `temperature`
- `u_component_of_wind`, `v_component_of_wind`
- `geopotential` — geopotential (divide by 9.80665 for geopotential height in meters)
- `specific_humidity`
- `relative_humidity`
- `vertical_velocity`

Common pressure levels (hPa): 1000, 925, 850, 700, 500, 300, 250, 200, 100, 50, 10

### ERA5-Land
- `2m_temperature`
- `soil_temperature_level_1` through `_level_4`
- `volumetric_soil_water_layer_1` through `_layer_4`
- `snow_depth`, `snow_depth_water_equivalent`
- `total_precipitation`
- `total_evaporation`
- `surface_runoff`, `sub_surface_runoff`
- `lake_mix_layer_temperature`

**Always verify variable names** using the "Show API request code" button on the dataset's CDS download form. Variable names can be unintuitive and the form is the authoritative source.

## Download Efficiency

### Storage and Speed

**CDS disk** — standard ERA5 datasets (hourly, daily stats, monthly means):
- Fast access (minutes to tens of minutes)
- Still benefits from monthly splitting to avoid queue penalties

**Tape archive** — `reanalysis-era5-complete`:
- Expect **hours to days** for requests
- Inefficient requests may be cancelled by administrators

### The Tape Rule

For tape-stored data: **always split requests by month**. One month of analysis data = one tape. A request spanning Jan–Dec forces 12 tape mounts; 12 monthly requests each touch one tape.

### Request Splitting Strategy

**Split by month for all ERA5 datasets.** Within each monthly request, include **all** variables, days, and times you need — don't split by variable or day (that creates unnecessary queue overhead).

### Do's and Don'ts

**Do:**
- Split by month
- Request all variables in one monthly request
- Use `area` to subset geographically — `[North, West, South, East]`
- Use `grid` for coarser resolution when full resolution isn't needed
- Use disk-hosted datasets when possible (avoid `era5-complete` unless you need model levels)

**Don't:**
- Request an entire year in one API call (gets deprioritized)
- Split by individual variable (wasteful)
- Mix atmospheric + wave + ensemble data in one NetCDF request (different grids cause errors)

### Download Format

The hourly and monthly-means datasets support two parameters for output:
- **`data_format`**: `"netcdf"` or `"grib"` — the file format itself
- **`download_format`**: `"unarchived"` (default) or `"zip"` — how the result is packaged

`"unarchived"` returns a bare file when the result is a single file, or a zip when multiple files are produced (common with NetCDF conversion). `"zip"` always wraps in a zip. **Use the default `"unarchived"` for programmatic workflows** — no need to specify it explicitly.

Daily statistics datasets have no format choice — they always output NetCDF in a zip.

## Download Script

Use `scripts/download_era5.py` for all ERA5/ERA5-Land downloads. It handles hourly, daily statistics, and monthly means, with optional parallelism. Run `python scripts/download_era5.py --help` for all options. Examples:

```bash
# ERA5 hourly 2m temperature, Europe, 2020-2024
python scripts/download_era5.py \
    --dataset reanalysis-era5-single-levels \
    --variables 2m_temperature total_precipitation \
    --years 2020 2024 --area 60 -10 30 40 --format netcdf

# ERA5 pressure levels
python scripts/download_era5.py \
    --dataset reanalysis-era5-pressure-levels \
    --variables temperature geopotential \
    --pressure-levels 500 700 850 925 1000 \
    --years 2020 2024

# ERA5-Land monthly means
python scripts/download_era5.py \
    --dataset reanalysis-era5-land-monthly-means \
    --variables 2m_temperature --years 2000 2024

# Derived daily statistics
python scripts/download_era5.py \
    --dataset derived-era5-single-levels-daily-statistics \
    --variables 2m_temperature --daily-statistic daily_mean \
    --years 2020 2024

# Parallel (4 workers)
python scripts/download_era5.py \
    --dataset reanalysis-era5-single-levels \
    --variables 2m_temperature --years 2020 2024 --workers 4
```


## Documentation Links

- ERA5 overview: https://confluence.ecmwf.int/display/CKB/ERA5
- How to download ERA5: https://confluence.ecmwf.int/display/CKB/How+to+download+ERA5
- ERA5 data documentation: https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation
- ERA5-Land: https://confluence.ecmwf.int/display/CKB/ERA5-Land
- CDS dataset catalog: https://cds.climate.copernicus.eu/datasets
