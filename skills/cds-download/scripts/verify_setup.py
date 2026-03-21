#!/usr/bin/env python3
"""
Verify CDS API setup by making a small test request.

Usage:
    python verify_setup.py

Requires:
    - ~/.cdsapirc configured with url and key
    - pip install "cdsapi>=0.7.7"
"""
import cdsapi

client = cdsapi.Client()

# Small test request — one hour of 2m temperature, small area
client.retrieve(
    "reanalysis-era5-single-levels",
    {
        "product_type": ["reanalysis"],
        "variable": ["2m_temperature"],
        "year": ["2024"],
        "month": ["01"],
        "day": ["01"],
        "time": ["00:00"],
        "data_format": "netcdf",
        "area": [50, -5, 45, 5],
    },
    "test_download.nc",
)
print("Success! CDS API is configured correctly.")
