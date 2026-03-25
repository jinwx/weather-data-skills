# ERA5 and ERA5-Land Datasets

## Dataset Catalog

### ERA5 (Atmosphere, 0.25° resolution)

| CDS Identifier | Time Scale | Storage | Temporal Coverage |
|---|---|---|---|
| `reanalysis-era5-single-levels` | Hourly | CDS disk (fast) | 1940–present |
| `reanalysis-era5-pressure-levels` | Hourly | CDS disk (fast) | 1940–present |
| `derived-era5-single-levels-daily-statistics` | Daily (on-the-fly) | CDS disk (fast) | 1940–present |
| `derived-era5-pressure-levels-daily-statistics` | Daily (on-the-fly) | CDS disk (fast) | 1940–present |
| `reanalysis-era5-single-levels-monthly-means` | Monthly | CDS disk (fast) | 1940–present |
| `reanalysis-era5-pressure-levels-monthly-means` | Monthly | CDS disk (fast) | 1940–present |
| `reanalysis-era5-complete` | Hourly | Tape (slow) | 1940–present |

### ERA5-Land (Land surface, 0.1° resolution)

| CDS Identifier | Time Scale | Storage | Temporal Coverage |
|---|---|---|---|
| `reanalysis-era5-land` | Hourly | CDS disk (fast) | 1950–present |
| `derived-era5-land-daily-statistics` | Daily (on-the-fly) | CDS disk (fast) | 1950–present |
| `reanalysis-era5-land-monthly-means` | Monthly | CDS disk (fast) | 1950–present |

**Note:** CDS also offers point-based time-series datasets (`reanalysis-era5-single-levels-timeseries`, `reanalysis-era5-land-timeseries`) optimized for extracting long time series at a single location (NetCDF/CSV). These use an ARCO backend and are not covered by the download script.

### Choosing a Dataset

Narrow down by these dimensions in order:

1. **Variable domain** — What are you measuring?
   - *Surface weather* (2m temperature, 10m wind, precipitation, pressure, radiation, SST, cloud cover, dewpoint): ERA5 single-levels datasets
   - *Upper-air profiles* (temperature, wind, geopotential, humidity, vertical velocity on pressure levels): ERA5 pressure-levels datasets
   - *Land surface hydrology* (soil temperature/moisture, snow, runoff, evaporation, lake temperature): ERA5-Land datasets
   - *Full model-level or wave data*: ERA5-complete (tape-stored, slow; use only when the above don't cover your variable)

2. **Spatial resolution** — How fine do you need?
   - 0.25° (≈ 28 km): ERA5 — covers atmosphere, ocean, and land
   - 0.1° (≈ 9 km): ERA5-Land — land surface variables only (overlaps with ERA5 for some surface variables like 2m temperature, precipitation), no atmospheric profiles, no ocean

3. **Time scale** — What temporal resolution do you need?
   - *Hourly*: native resolution; most flexible
   - *Daily aggregates* (mean/min/max/sum): daily-statistics datasets — avoids downloading hourly and aggregating locally, but slower (computed on-the-fly). For large domains or long time ranges, downloading hourly and aggregating locally may be faster.
   - *Monthly averages*: monthly-means datasets — pre-computed, fast, good for climatologies

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

For variables not listed here, query the process description API. Variable names can be unintuitive.

## Download Script

`scripts/download_era5.py` covers common bulk-download scenarios: hourly data (all hours/days per month) and monthly means for the 6 datasets listed above. It splits requests by month, handles `product_type` automatically, and supports parallel downloads. Run `python scripts/download_era5.py --help` for all options.

For daily statistics, ERA5-complete, time-series datasets, ensemble/by-hour-of-day product types, or selecting specific hours/days, write custom download code using the CDS API directly.

## CDS API Reference

**Always explicitly specify all parameters supported by the dataset.** Omitting or misusing parameters can silently return incorrect data. If any ambiguity remains, ask the user before proceeding.

- Some datasets have a `product_type` parameter — do not omit it, as incorrect or missing values can silently return wrong data.

- Time dimensions required per dataset type:

  | Parameter | Hourly | Daily statistics | Monthly means |
  |---|---|---|---|
  | `year` | required | required | required |
  | `month` | required | required | required |
  | `day` | required | required | — |
  | `time` | required | — | required |

- Use `grib` for `data_format`. Daily statistics datasets have no format choice — they always output NetCDF in a zip archive.

- **Split requests by month** for all ERA5 datasets. One month = one tape for `reanalysis-era5-complete`; multi-month requests force multiple tape mounts and get deprioritized. Within each monthly request, include all variables, days, and times — don't split by variable or day.

- `reanalysis-era5-complete` is tape-archived (hours to days per request). All other datasets are on CDS disk (minutes). Avoid `era5-complete` unless you need model levels.

- Use `area` ([North, West, South, East]) to subset geographically. Do not mix atmospheric + wave + ensemble data in one NetCDF request (different grids cause errors).

- To query the full parameter schema for any dataset (no authentication required):

  ```
  GET https://cds.climate.copernicus.eu/api/retrieve/v1/processes/{dataset}
  ```

  This returns all supported parameters, valid values, and constraints. Use it to verify variable names and discover parameters not listed above.

## Documentation Links

- ERA5 overview: https://confluence.ecmwf.int/display/CKB/ERA5
- How to download ERA5: https://confluence.ecmwf.int/display/CKB/How+to+download+ERA5
- ERA5 data documentation: https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation
- ERA5-Land: https://confluence.ecmwf.int/display/CKB/ERA5-Land
- CDS dataset catalog: https://cds.climate.copernicus.eu/datasets
