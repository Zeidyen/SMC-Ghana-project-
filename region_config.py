"""
Per-region configuration for the three northern-Ghana models.

Each region is an independent single-node model (node id 1) with its own climate/
weather, coordinates, and (later) intervention coverage schedule + PfPR targets.
Shared model mechanics live in ghana_model.py / burnin.py.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

REGIONS = {
    "upper_east": dict(name="Navrongo", lat=10.90, lon=-1.09),
    "upper_west": dict(name="Wa",       lat=10.06, lon=-2.50),
    "northern":   dict(name="Tamale",   lat=9.40,  lon=-0.84),
}

# Concurrency for the Container platform (M4 Max: 16 cores). Default is 4.
# At 2k pop each sim uses ~0.3 GB, so memory is not a constraint -> core-bound;
# 14 leaves 2 cores for the OS. (At 20k it was memory-bound; use 10 there.)
MAX_JOB = 14


def weather_dir(region):
    return os.path.join(_HERE, "climate", f"emod_weather_{region}")


def coords(region):
    r = REGIONS[region]
    return r["lat"], r["lon"]


def check(region):
    if region not in REGIONS:
        raise SystemExit(f"unknown region {region!r}; choose from {list(REGIONS)}")
    wd = weather_dir(region)
    if not os.path.isdir(wd) or not os.listdir(wd):
        raise SystemExit(f"no weather files for {region} at {wd}; run build_weather.py")
    return region
