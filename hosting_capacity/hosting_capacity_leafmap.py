#!/usr/bin/env python3
"""
Leafmap visualization for hosting-capacity studies.

This module creates an interactive HTML map for transformer, three-phase and
OpenDSS feeder hosting-capacity results.

It can visualize:
- buses/nodes with latitude and longitude;
- feeder line segments between buses;
- voltage limits by bus;
- line loading limits by segment;
- hosting-capacity violations;
- optional transformer/load/generator point layers.

Dependencies
------------
    pip install leafmap pandas

Optional, for GeoJSON export workflows:
    pip install geopandas shapely

Required input files
--------------------
Use a folder containing at least:

    buses.csv
    lines.csv

Optional result files:

    bus_results.csv
    line_results.csv
    generators.csv
    loads.csv

buses.csv schema:
    bus,lat,lon,kv,role

lines.csv schema:
    name,bus1,bus2,phases,kv,length_km,ampacity_a,conductor

bus_results.csv schema:
    bus,min_voltage_pu,max_voltage_pu,voltage_unbalance_pct,violation

line_results.csv schema:
    name,max_current_a,max_loading_pct,violation
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import pandas as pd


def import_leafmap():
    try:
        import leafmap.foliumap as leafmap  # type: ignore
        return leafmap
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("leafmap is not installed. Install with: pip install leafmap") from exc


def read_csv(folder: Path, name: str) -> pd.DataFrame:
    path = folder / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def normalize_bus_name(bus: Any) -> str:
    text = str(bus).strip()
    return text.split(".")[0]


def color_by_voltage(min_v: Optional[float], max_v: Optional[float], vmin: float, vmax: float) -> str:
    if min_v is None or max_v is None:
        return "gray"
    if min_v < vmin or max_v > vmax:
        return "red"
    if min_v < vmin + 0.02 or max_v > vmax - 0.02:
        return "orange"
    return "green"


def color_by_loading(loading_pct: Optional[float], limit_pct: float) -> str:
    if loading_pct is None:
        return "gray"
    if loading_pct > limit_pct:
        return "red"
    if loading_pct > 0.9 * limit_pct:
        return "orange"
    return "blue"


def as_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value == "" or value is None:
            return default
        return float(value)
    except Exception:
        return default


def build_bus_lookup(buses: pd.DataFrame) -> Dict[str, Tuple[float, float]]:
    required = {"bus", "lat", "lon"}
    missing = required - set(buses.columns)
    if missing:
        raise ValueError(f"buses.csv missing columns: {sorted(missing)}")

    lookup: Dict[str, Tuple[float, float]] = {}
    for _, row in buses.iterrows():
        bus = normalize_bus_name(row["bus"])
        lat = as_float(row["lat"])
        lon = as_float(row["lon"])
        if lat is None or lon is None:
            continue
        lookup[bus] = (lat, lon)
    if not lookup:
        raise ValueError("buses.csv has no valid lat/lon coordinates.")
    return lookup


def merge_bus_results(buses: pd.DataFrame, bus_results: pd.DataFrame) -> pd.DataFrame:
    buses = buses.copy()
    buses["bus_norm"] = buses["bus"].map(normalize_bus_name)
    if bus_results.empty:
        return buses
    results = bus_results.copy()
    results["bus_norm"] = results["bus"].map(normalize_bus_name)
    return buses.merge(results.drop(columns=["bus"], errors="ignore"), on="bus_norm", how="left")


def merge_line_results(lines: pd.DataFrame, line_results: pd.DataFrame) -> pd.DataFrame:
    lines = lines.copy()
    if "name" not in lines.columns:
        raise ValueError("lines.csv must contain a name column.")
    if line_results.empty:
        return lines
    return lines.merge(line_results, on="name", how="left", suffixes=("", "_result"))


def create_map(
    folder: Path,
    output_html: Path,
    vmin_pu: float = 0.92,
    vmax_pu: float = 1.05,
    line_loading_limit_pct: float = 100.0,
    basemap: str = "OpenStreetMap",
) -> Dict[str, Any]:
    leafmap = import_leafmap()

    buses = read_csv(folder, "buses.csv")
    lines = read_csv(folder, "lines.csv")
    bus_results = read_csv(folder, "bus_results.csv")
    line_results = read_csv(folder, "line_results.csv")
    loads = read_csv(folder, "loads.csv")
    generators = read_csv(folder, "generators.csv")

    if buses.empty:
        raise ValueError("buses.csv is required for leafmap visualization.")
    if lines.empty:
        raise ValueError("lines.csv is required for leafmap visualization.")

    bus_lookup = build_bus_lookup(buses)
    buses_m = merge_bus_results(buses, bus_results)
    lines_m = merge_line_results(lines, line_results)

    center_lat = sum(lat for lat, _ in bus_lookup.values()) / len(bus_lookup)
    center_lon = sum(lon for _, lon in bus_lookup.values()) / len(bus_lookup)

    m = leafmap.Map(center=(center_lat, center_lon), zoom=15)
    try:
        m.add_basemap(basemap)
    except Exception:
        pass

    # Draw feeder lines first.
    line_count = 0
    line_violations = 0
    for _, row in lines_m.iterrows():
        bus1 = normalize_bus_name(row.get("bus1", ""))
        bus2 = normalize_bus_name(row.get("bus2", ""))
        if bus1 not in bus_lookup or bus2 not in bus_lookup:
            continue
        loading = as_float(row.get("max_loading_pct"))
        violation = str(row.get("violation", "")).lower() in {"1", "true", "yes", "sim"}
        color = "red" if violation else color_by_loading(loading, line_loading_limit_pct)
        if color == "red":
            line_violations += 1
        popup = (
            f"<b>Line:</b> {row.get('name', '')}<br>"
            f"<b>Bus1:</b> {bus1}<br>"
            f"<b>Bus2:</b> {bus2}<br>"
            f"<b>Conductor:</b> {row.get('conductor', row.get('linecode', ''))}<br>"
            f"<b>Phases:</b> {row.get('phases', '')}<br>"
            f"<b>kV:</b> {row.get('kv', '')}<br>"
            f"<b>Length km:</b> {row.get('length_km', '')}<br>"
            f"<b>Ampacity A:</b> {row.get('ampacity_a', '')}<br>"
            f"<b>Max loading %:</b> {row.get('max_loading_pct', '')}<br>"
            f"<b>Violation:</b> {row.get('violation', '')}"
        )
        m.add_polyline(
            locations=[bus_lookup[bus1], bus_lookup[bus2]],
            color=color,
            weight=5 if color == "red" else 3,
            opacity=0.85,
            popup=popup,
        )
        line_count += 1

    # Draw buses.
    bus_count = 0
    bus_violations = 0
    for _, row in buses_m.iterrows():
        bus = normalize_bus_name(row.get("bus", ""))
        if bus not in bus_lookup:
            continue
        min_v = as_float(row.get("min_voltage_pu"))
        max_v = as_float(row.get("max_voltage_pu"))
        violation = str(row.get("violation", "")).lower() in {"1", "true", "yes", "sim"}
        color = "red" if violation else color_by_voltage(min_v, max_v, vmin_pu, vmax_pu)
        if color == "red":
            bus_violations += 1
        radius = 8 if str(row.get("role", "")).lower() == "source" else 6
        popup = (
            f"<b>Bus:</b> {bus}<br>"
            f"<b>Role:</b> {row.get('role', '')}<br>"
            f"<b>kV:</b> {row.get('kv', '')}<br>"
            f"<b>Min V pu:</b> {row.get('min_voltage_pu', '')}<br>"
            f"<b>Max V pu:</b> {row.get('max_voltage_pu', '')}<br>"
            f"<b>Unbalance %:</b> {row.get('voltage_unbalance_pct', '')}<br>"
            f"<b>Violation:</b> {row.get('violation', '')}"
        )
        m.add_circle_marker(
            location=bus_lookup[bus],
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=0.9,
            popup=popup,
        )
        bus_count += 1

    # Optional load and generator markers are placed at their bus coordinates.
    for layer_name, df, marker_color, power_col in [
        ("Load", loads, "purple", "kw"),
        ("Generator", generators, "darkgreen", "kw"),
    ]:
        if df.empty or "bus" not in df.columns:
            continue
        for _, row in df.iterrows():
            bus = normalize_bus_name(row.get("bus", ""))
            if bus not in bus_lookup:
                continue
            popup = (
                f"<b>{layer_name}:</b> {row.get('name', '')}<br>"
                f"<b>Bus:</b> {bus}<br>"
                f"<b>kW:</b> {row.get(power_col, '')}<br>"
                f"<b>Phases:</b> {row.get('phases', '')}<br>"
                f"<b>kV:</b> {row.get('kv', '')}"
            )
            m.add_marker(location=bus_lookup[bus], popup=popup, icon=marker_color)

    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999; background: white; padding: 10px; border: 1px solid #888; font-size: 13px;">
      <b>Hosting Capacity Map</b><br>
      <span style="color:green;">●</span> Voltage OK<br>
      <span style="color:orange;">●</span> Near limit<br>
      <span style="color:red;">●</span> Violation<br>
      <span style="color:blue;">━</span> Line OK<br>
      <span style="color:orange;">━</span> Line near ampacity<br>
      <span style="color:red;">━</span> Line violation
    </div>
    """
    try:
        m.get_root().html.add_child(leafmap.folium.Element(legend_html))
    except Exception:
        pass

    output_html.parent.mkdir(parents=True, exist_ok=True)
    m.to_html(str(output_html))

    summary = {
        "output_html": str(output_html),
        "bus_count": bus_count,
        "line_count": line_count,
        "bus_violations": bus_violations,
        "line_violations": line_violations,
        "center": {"lat": center_lat, "lon": center_lon},
    }
    (output_html.parent / "leafmap_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a leafmap HTML visualization for hosting-capacity studies.")
    parser.add_argument("--folder", required=True, type=Path, help="Folder containing buses.csv, lines.csv and optional result CSV files.")
    parser.add_argument("--output-html", type=Path, default=Path("hosting_capacity/output/hosting_capacity_map.html"))
    parser.add_argument("--vmin-pu", type=float, default=0.92)
    parser.add_argument("--vmax-pu", type=float, default=1.05)
    parser.add_argument("--line-loading-limit-pct", type=float, default=100.0)
    parser.add_argument("--basemap", default="OpenStreetMap")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = create_map(
        folder=args.folder,
        output_html=args.output_html,
        vmin_pu=args.vmin_pu,
        vmax_pu=args.vmax_pu,
        line_loading_limit_pct=args.line_loading_limit_pct,
        basemap=args.basemap,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
