from math import cos, radians
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt
from matplotlib.markers import MarkerStyle



project_dir = Path(__file__).resolve().parents[1]
track_path = project_dir / "data" / "raw" / "EX2104_DIVE06_Path.kml"

root = ET.parse(track_path).getroot()
coordinates = root.findtext(".//LineString/coordinates")
if not coordinates or not coordinates.strip():
    raise ValueError(f"No LineString coordinates found in {track_path}")

# Each entry is a comma-separated tuple. Whitespace separates the points.
points = [tuple(map(float, entry.split(","))) for entry in coordinates.split()]
longitudes, latitudes, altitudes = zip(*points)

print(f"Track points: {len(points):,}")
print(f"First point (lon, lat, alt): {points[0]}")
print(f"Last point  (lon, lat, alt): {points[-1]}")
print(f"KML altitude range: {min(altitudes):g} to {max(altitudes):g}")

fig, ax = plt.subplots(figsize=(9, 6), layout="constrained")
ax.plot(longitudes, latitudes, linewidth=1, label="Recorded track")
ax.scatter(longitudes[0], latitudes[0], zorder=3, label="First point")
ax.scatter(longitudes[-1], latitudes[-1], zorder=3, label="Last point")
ax.set(title="Castle Rock Seamount · Dive 06", xlabel="Longitude (°)", ylabel="Latitude (°)")
ax.ticklabel_format(useOffset=False)
ax.set_aspect(1 / cos(radians(sum(latitudes) / len(latitudes))))
ax.grid(alpha=0.25)
ax.scatter(
    -51.34791183,
    36.30069733,
    color="tab:purple",
    marker=MarkerStyle("D"),
    zorder=4,
    label="Glass sponge sample",
)
ax.legend()

output_path = project_dir / "experiments" / "castle_rock_dive_track.png"
fig.savefig(str(output_path), dpi=160)
print(f"Saved: {output_path}")