"""Paths used by the emodpy-malaria build. Bootstrapped binary + schema live in ./download."""
import os

_here = os.path.dirname(os.path.abspath(__file__))

# EMOD Eradication binary (Linux x86-64) and its schema, from emod_malaria.bootstrap
eradication_path = os.path.join(_here, "download", "Eradication")
schema_file = os.path.join(_here, "download", "schema.json")

# Where idmtools assembles simulation assets
assets_input_dir = os.path.join(_here, "Assets")

# Local job directory for the Container platform
job_directory = os.path.join(_here, "jobs")


def latest_proj_exp(region):
    """Newest projection experiment for a region that HAS results, chosen by the
    most recently WRITTEN MalariaSummaryReport. Experiment-dir mtimes are fixed at
    launch (and can be touched later), so they're unreliable; empty/failed
    experiments (no reports) are ignored entirely."""
    import glob
    exps = glob.glob(os.path.join(job_directory, f"e_ghana_proj_{region}_*"))
    scored = []
    for e in exps:
        reps = glob.glob(os.path.join(e, "*", "output", "MalariaSummaryReport.json"))
        if reps:
            scored.append((max(os.path.getmtime(p) for p in reps), e))
    if not scored:
        raise SystemExit(f"no projection experiments with results for {region}")
    return max(scored)[1]
