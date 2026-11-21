import sys
import csv
from bisect import bisect_left
from datetime import UTC, datetime
from io import TextIOWrapper
from math import isfinite
from pathlib import Path
from statistics import median
from zipfile import ZipFile

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.layout_engine import ConstrainedLayoutEngine
from matplotlib.markers import MarkerStyle
from matplotlib.widgets import Slider
from matplotlib.widgets import Button, Slider


project_dir = Path(__file__).resolve().parents[1]
archive_path = project_dir / "data" / "raw" / "ex2104-DIVE06-ancillary-data.zip"
track_file = "EX2104_DIVE06_20210709/EX2104_DIVE06_RovTrack1Hz.csv"

in_water = datetime.fromisoformat("2021-07-09T12:18:51.439449+00:00")
on_bottom = datetime.fromisoformat("2021-07-09T13:44:02.688767+00:00")
off_bottom = datetime.fromisoformat("2021-07-09T19:20:53.142459+00:00")
out_water = datetime.fromisoformat("2021-07-09T20:34:57.710442+00:00")
reported_max_depth = 2331.3

samples = []
with ZipFile(archive_path) as archive:
    with TextIOWrapper(archive.open(track_file), encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row["UNIXTIME"].strip() or not row["DEPTH"].strip():
                continue

            timestamp = float(row["UNIXTIME"])
            # The track stores underwater depths as negative values.
            depth = -float(row["DEPTH"])
            if not isfinite(timestamp) or not isfinite(depth):
                continue

            time = datetime.fromtimestamp(timestamp, tz=UTC)
            if in_water <= time <= out_water:
                lat = float(row["LAT_DD"].strip() or "nan")
                lon = float(row["LON_DD"].strip() or "nan")
                samples.append((time, depth, lat, lon))

if len(samples) < 2:
    raise ValueError("Need at least two valid depth readings within the dive window")

samples.sort()
times, depths, latitudes, longitudes = zip(*samples)
intervals = [(later - earlier).total_seconds() for earlier, later in zip(times, times[1:])]
deepest_time, deepest_depth, _, _ = max(samples, key=lambda sample: sample[1])

print(f"Depth readings in dive window: {len(samples):,}")
print(f"Median interval between readings: {median(intervals):.3f} s")
print(f"Largest interval between readings: {max(intervals):.3f} s")
print(f"Deepest reading: {deepest_depth:.2f} m at {deepest_time.isoformat()}")
print(f"Difference from dive report: {deepest_depth - reported_max_depth:+.2f} m")

interactive = "--interactive" in sys.argv

if interactive:
    fig = plt.figure(figsize=(14, 6), layout="constrained")
    fig.set_layout_engine(
        ConstrainedLayoutEngine(rect=(0.0, 0.18, 1.0, 0.82))
    )
    panels = fig.add_gridspec(1, 2, width_ratios=(1.35, 1.0))
    ax = fig.add_subplot(panels[0, 0])
    map_ax = fig.add_subplot(panels[0, 1])
else:
    fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
    map_ax = None
ax.plot(times, depths, linewidth=1, label="Recorded depth")
ax.axvspan(
    float(mdates.date2num(on_bottom)),
    float(mdates.date2num(off_bottom)),
    alpha=0.15,
    label="Logged bottom time",
)
ax.scatter(float(mdates.date2num(deepest_time)), deepest_depth, color="tab:orange", zorder=3, label="Deepest reading")
ax.set(title="Castle Rock Seamount · Dive 06", xlabel="Time (UTC)", ylabel="Depth (m)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=UTC))
ax.invert_yaxis()
ax.grid(alpha=0.25)
sponge_time = datetime(2021, 7, 9, 15, 2, 11, tzinfo=UTC)

ax.scatter(
    float(mdates.date2num(sponge_time)),
    2265.042969,
    color="tab:purple",
    marker=MarkerStyle("D"),
    zorder=4,
    label="Glass sponge sample",
)
ax.legend()

output_path = project_dir / "experiments" / "castle_rock_dive_depth.png"
if not interactive:

    fig.savefig(str(output_path), dpi=160)
    print(f"Saved: {output_path}")

if map_ax is not None:
    elapsed = [(time - times[0]).total_seconds() for time in times]

    slider_ax = fig.add_axes((0.16, 0.06, 0.57, 0.04))
    slider = Slider(slider_ax, "Elapsed (s)", 0, elapsed[-1], valinit=0)
    cursor = ax.axvline(float(mdates.date2num(times[0])), color="tab:red")
    readout = ax.set_title("Castle Rock Seamount · Dive 06")

    map_ax.plot(longitudes, latitudes, linewidth=1, color="tab:blue")
    rov_marker, = map_ax.plot([], [], "ro")
    map_ax.scatter(
        -51.34791183,
        36.30069733,
        s=120,
        facecolors="none",
        edgecolors="tab:purple",
        marker=MarkerStyle("D"),
        zorder=4,
        label="Reported sponge location",
    )
    map_ax.legend(loc="upper left")
    map_ax.set(
        title="Castle Rock · ROV position",
        xlabel="Longitude (°)",
        ylabel="Latitude (°)",
    )
    map_ax.ticklabel_format(useOffset=False)

    def update(seconds: float) -> None:
        right = min(bisect_left(elapsed, seconds), len(elapsed) - 1)
        left = max(0, right - 1)
        index = min((left, right), key=lambda i: abs(elapsed[i] - seconds))

        x = float(mdates.date2num(times[index]))
        cursor.set_xdata([x, x])
        readout.set_text(
            f"Castle Rock Seamount · Dive 06 · "
            f"{times[index]:%H:%M:%S} UTC · {depths[index]:,.1f} m"
        )
        lat, lon = latitudes[index], longitudes[index]
        if isfinite(lat) and isfinite(lon):
            rov_marker.set_data([lon], [lat])
        else:
            rov_marker.set_data([], [])

        fig.canvas.draw_idle()

    slider.on_changed(update)

    update(0)
    sponge_elapsed = (sponge_time - times[0]).total_seconds()
    sponge_button_ax = fig.add_axes((0.81, 0.045, 0.17, 0.07))
    sponge_button = Button(sponge_button_ax, "Jump to sponge")
    sponge_button.on_clicked(lambda _event: slider.set_val(sponge_elapsed))
    plt.show()