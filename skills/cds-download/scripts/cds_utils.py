"""
Shared CDS API utilities for seasonal forecast download scripts.

Usage:
    from cds_utils import query_constraints, find_latest_system
"""
import json
import urllib.request


def query_constraints(dataset, **selections):
    """Query the CDS dynamic constraints API to find valid parameter values.

    Pass a partial selection; the response contains valid values for all
    remaining parameters. No authentication required.

    Args:
        dataset: CDS dataset identifier (e.g., "seasonal-monthly-single-levels")
        **selections: Parameter filters (e.g., originating_centre=["ecmwf"],
                      system=["51"], product_type=["monthly_mean"])

    Returns:
        dict with parameter names as keys and lists of valid values as values.

    Example:
        >>> result = query_constraints(
        ...     "seasonal-monthly-single-levels",
        ...     originating_centre=["ecmwf"],
        ...     system=["51"],
        ... )
        >>> print(result["year"])  # all available years for ECMWF sys 51
    """
    url = f"https://cds.climate.copernicus.eu/api/retrieve/v1/processes/{dataset}/constraints"
    data = json.dumps({"inputs": selections}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def find_latest_system(dataset, centre, product_type="monthly_mean"):
    """Find the system with the most recent real-time data for a centre.

    Queries all systems for the given centre and returns the one whose
    available years extend furthest into the present.

    Args:
        dataset: CDS dataset identifier
        centre: Originating centre (e.g., "ecmwf", "ukmo")
        product_type: Product type to check (default: "monthly_mean")

    Returns:
        System version string (e.g., "51")

    Raises:
        ValueError: If no systems are found for the centre
    """
    result = query_constraints(dataset, originating_centre=[centre])
    systems = result.get("system", [])
    if not systems:
        raise ValueError(f"No systems found for centre '{centre}'")

    best_system = None
    best_max_year = 0
    for sys in systems:
        r = query_constraints(dataset, originating_centre=[centre], system=[sys],
                              product_type=[product_type])
        years = r.get("year", [])
        if years:
            max_year = max(int(y) for y in years)
            if max_year > best_max_year:
                best_max_year = max_year
                best_system = sys
    return best_system
