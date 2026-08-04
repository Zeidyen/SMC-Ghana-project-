"""Convert Ghana ADM1 GeoJSON to compact SVG paths for the dashboard map.
Study regions (old 3-region north): Upper East, Upper West, and Northern
(= Northern + Savannah + North East, the 2019 split). Everything else = faint
context. Equirectangular projection, decimated + rounded to keep it small."""
import json, math

gj = json.load(open("/tmp/gha_adm1.json"))
STUDY = {"upper_east": ["Upper East Region"],
         "upper_west": ["Upper West Region"],
         "northern":   ["Northern Region", "Savannah Region", "North East Region"]}
name2key = {n: k for k, ns in STUDY.items() for n in ns}

# bbox over all of Ghana
xs, ys = [], []
def walk(coords, depth):
    if depth == 0:
        xs.append(coords[0]); ys.append(coords[1])
    else:
        for c in coords: walk(c, depth - 1)
for f in gj["features"]:
    g = f["geometry"]; d = 1 if g["type"] == "Polygon" else 2
    walk(g["coordinates"], d + 1)
lonmin, lonmax = min(xs), max(xs); latmin, latmax = min(ys), max(ys)
latmid = math.radians((latmin + latmax) / 2)
W = 300.0
sx = W / ((lonmax - lonmin) * math.cos(latmid))
H = (latmax - latmin) * sx
def proj(lon, lat):
    return ((lon - lonmin) * math.cos(latmid) * sx, (latmax - lat) * sx)

def ring_to_path(ring):
    # decimate: keep ~every other point on long rings; always keep endpoints
    n = len(ring)
    step = 2 if n > 60 else 1
    pts = [ring[i] for i in range(0, n, step)]
    if pts[-1] != ring[-1]: pts.append(ring[-1])
    out = []
    for i, (lon, lat) in enumerate(pts):
        x, y = proj(lon, lat)
        out.append(("M" if i == 0 else "L") + f"{x:.1f} {y:.1f}")
    return "".join(out) + "Z"

def geom_to_path(g):
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    segs = []
    for poly in polys:
        for ring in poly:
            if len(ring) >= 4:
                segs.append(ring_to_path(ring))
    return "".join(segs)

study = {k: "" for k in STUDY}
labels = {k: [[], []] for k in STUDY}   # accumulate projected pts for centroid
context = []
def acc_pts(g, key):
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for poly in polys:
        for lon, lat in poly[0]:
            x, y = proj(lon, lat); labels[key][0].append(x); labels[key][1].append(y)
for f in gj["features"]:
    nm = f["properties"].get("shapeName")
    path = geom_to_path(f["geometry"])
    if nm in name2key:
        k = name2key[nm]; study[k] += path; acc_pts(f["geometry"], k)
    else:
        context.append(path)
lab = {k: [round(sum(v[0]) / len(v[0]), 1), round(sum(v[1]) / len(v[1]), 1)]
       for k, v in labels.items()}
out = {"study": study, "context": "".join(context), "labels": lab,
       "viewBox": f"0 0 {W:.0f} {H:.0f}"}
json.dump(out, open("data/ghana_paths.json", "w"), separators=(",", ":"))
print("viewBox", out["viewBox"], "| bytes", len(json.dumps(out)))
