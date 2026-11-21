import csv
from datetime import UTC, datetime
from io import TextIOWrapper
from math import cos, hypot, isfinite, radians
from pathlib import Path
from zipfile import ZipFile


project_dir = Path(__file__).resolve().parents[1]
archive_path = project_dir / "data" / "raw" / "ex2104-DIVE06-ancillary-data.zip"
track_file = "EX2104_DIVE06_20210709/EX2104_DIVE06_RovTrack1Hz.csv"

event_time = datetime(2021, 7, 9, 15, 2, 11, tzinfo=UTC)
reported_lat, reported_lon = 36.30069733, -51.34791183
reported_depth = 2265.042969
search_window_seconds = 5

candidates = []
with ZipFile(archive_path) as archive:
    with TextIOWrapper(archive.open(track_file), encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            fields = [row[key].strip() for key in ("UNIXTIME", "LAT_DD", "LON_DD", "DEPTH")]
            if not all(fields):
                continue

            timestamp, lat, lon, raw_depth = map(float, fields)
            if not all(map(isfinite, (timestamp, lat, lon, raw_depth))):
                continue

            offset = timestamp - event_time.timestamp()
            if abs(offset) <= search_window_seconds:
                candidates.append((offset, lat, lon, -raw_depth))

if not candidates:
    raise ValueError("No complete navigation reading within 5 seconds of the sample event")

offset, lat, lon, depth = min(candidates, key=lambda reading: abs(reading[0]))

# Approximate the local east-west and north-south offsets in meters.
earth_radius_m = 6_371_000
north_m = earth_radius_m * radians(lat - reported_lat)
east_m = earth_radius_m * radians(lon - reported_lon) * cos(radians(reported_lat))

print(f"Navigation time offset: {offset:+.3f} s")
print(f"Navigation position: {lat:.8f}, {lon:.8f}")
print(f"Horizontal separation from report: {hypot(east_m, north_m):.2f} m")
print(f"Navigation depth: {depth:.2f} m")
print(f"Depth difference from report: {depth - reported_depth:+.2f} m")