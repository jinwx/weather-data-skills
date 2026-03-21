# CDS API Setup Guide

## Account Registration

1. Go to https://cds.climate.copernicus.eu and click "Register"
2. Fill in your details and verify your email
3. Log in to your new account

## Get Your Personal Access Token

1. Log in at https://cds.climate.copernicus.eu
2. Go to your profile page: https://cds.climate.copernicus.eu/profile
3. Your **Personal Access Token** is displayed on this page — copy it

## Configure .cdsapirc

Create or update the file `~/.cdsapirc` with exactly this format:

```
url: https://cds.climate.copernicus.eu/api
key: <YOUR-PERSONAL-ACCESS-TOKEN>
```

**Important**: The `.cdsapirc` file should only contain `url` and `key`. If the user's file has a `uid` field or a different URL (like `/api/v2`), it's outdated — replace it with the format above.

On Windows, the file goes at `%USERPROFILE%\.cdsapirc` (e.g., `C:\Users\YourName\.cdsapirc`).

## Install the Python Client

Requires Python 3. Install or upgrade:

```bash
pip install "cdsapi>=0.7.7"
```

Version 0.7.7+ is required. If you have an older version, upgrade:

```bash
pip install --upgrade cdsapi
```

## Verify the Setup

Run the verification script to confirm everything works:

```bash
python scripts/verify_setup.py
```

If this fails, check:
- Is `.cdsapirc` in your home directory?
- Is the token correct (copy it fresh from your profile page)?
- Is `cdsapi` version 0.7.7 or newer? (`pip show cdsapi`)

## Accept Dataset Licenses

Before downloading any dataset for the first time, you must accept its license on the CDS website:

1. Navigate to the dataset page (e.g., https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels)
2. Scroll to the download form
3. Accept the terms and conditions

This only needs to be done once per dataset. If you get a license error from the API, this is almost certainly the cause.

## Alternative: Inline Credentials

If you can't create a `.cdsapirc` file (e.g., shared server, Docker), pass credentials directly:

```python
import cdsapi

client = cdsapi.Client(
    url="https://cds.climate.copernicus.eu/api",
    key="YOUR-PERSONAL-ACCESS-TOKEN",
)
```

Or via environment variables:

```bash
export CDSAPI_URL="https://cds.climate.copernicus.eu/api"
export CDSAPI_KEY="YOUR-PERSONAL-ACCESS-TOKEN"
```

## New Advanced Package (Optional)

A new package `ecmwf-datastores-client` is available with advanced features (metadata retrieval, async job submission, REST API). It's optional — `cdsapi` is fully supported. Only recommend this if the user specifically needs async patterns or metadata access.

```bash
pip install ecmwf-datastores-client
```

## Key URLs

- CDS Portal: https://cds.climate.copernicus.eu
- API Setup Guide: https://cds.climate.copernicus.eu/how-to-api
- Profile (API token): https://cds.climate.copernicus.eu/profile
- Migration Guide: https://confluence.ecmwf.int/x/uINmFw
- cdsapi on PyPI: https://pypi.org/project/cdsapi/
- cdsapi on GitHub: https://github.com/ecmwf/cdsapi
