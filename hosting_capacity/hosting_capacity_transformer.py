#!/usr/bin/env python3
"""
Transformer hosting capacity analysis for multiple loads and generators.

Model scope
-----------
This script evaluates transformer loading over a time series for:
- multiple loads connected downstream of one transformer;
- multiple generators connected downstream of the same transformer;
- optional per-unit capacity sweep for additional load or generation;
- transformer overload, reverse-power, voltage-rise proxy and energy-balance metrics.

Important engineering note
--------------------------
This is a transformer-level hosting-capacity screening model. It does not replace
full feeder power-flow studies when voltage drop/rise, conductor loading,
protection, phase imbalance, fault current or regulator/capacitor interactions are relevant.
For feeder-level analysis, export the same time-series data to OpenDSS, pandapower,
PowerFactory, CYME or equivalent.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

HostingMode = Literal["load", "generation"]


@dataclass(frozen=True)
class TransformerConfig:
    kva_rating: float
    pf_load: float = 0.92
    pf_generation: float = 1.00
    overload_limit_pct: float = 100.0
    reverse_power_limit_pct: float = 100.0
    voltage_rise_limit_pct: float = 3.0
    transformer_impedance_pct: float = 4.0
    timestep_minutes: int = 15

    @property
    def overload_limit_kva(self) -> float:
        return self.kva_rating * self.overload_limit_pct / 100.0

    @property
    def reverse_power_limit_kw(self) -> float:
        return self.kva_rating * self.reverse_power_limit_pct / 100.0


def read_timeseries_csv(path: Path) -> pd.DataFrame:
    """Read a CSV with column 'timestamp' plus load_* and gen_* columns in kW."""
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError("CSV must contain a 'timestamp' column.")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    numeric_cols = [c for c in df.columns if c != "timestamp"]
    if not numeric_cols:
        raise ValueError("CSV must contain at least one load_* or gen_* kW column.")
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return df


def aggregate_power(df: pd.DataFrame) -> pd.DataFrame:
    load_cols = [c for c in df.columns if c.lower().startswith("load_")]
    gen_cols = [c for c in df.columns if c.lower().startswith("gen_")]

    if not load_cols and not gen_cols:
        raise ValueError("CSV must contain columns prefixed with load_ and/or gen_.")

    out = pd.DataFrame({"timestamp": df["timestamp"]})
    out["load_kw"] = df[load_cols].sum(axis=1) if load_cols else 0.0
    out["generation_kw"] = df[gen_cols].sum(axis=1) if gen_cols else 0.0
    out["net_kw"] = out["load_kw"] - out["generation_kw"]
    return out


def evaluate_transformer(base: pd.DataFrame, cfg: TransformerConfig) -> pd.DataFrame:
    """Evaluate apparent power, reverse power and proxy voltage-rise constraints."""
    out = base.copy()

    # Approximate apparent loading. Positive net = import/load. Negative net = export.
    pf = np.where(out["net_kw"] >= 0, cfg.pf_load, cfg.pf_generation)
    out["transformer_kva"] = np.abs(out["net_kw"] / pf)
    out["loading_pct"] = 100.0 * out["transformer_kva"] / cfg.kva_rating
    out["reverse_power_kw"] = np.maximum(-out["net_kw"], 0.0)
    out["reverse_power_pct"] = 100.0 * out["reverse_power_kw"] / cfg.kva_rating

    # Transformer-only voltage-rise proxy: deltaV% ~= Z% * export_kVA / transformer_kVA_rating.
    # This is a screening indicator, not a feeder voltage calculation.
    export_kva = out["reverse_power_kw"] / max(cfg.pf_generation, 1e-9)
    out["voltage_rise_proxy_pct"] = cfg.transformer_impedance_pct * export_kva / cfg.kva_rating

    out["overload_violation"] = out["transformer_kva"] > cfg.overload_limit_kva
    out["reverse_power_violation"] = out["reverse_power_kw"] > cfg.reverse_power_limit_kw
    out["voltage_rise_proxy_violation"] = out["voltage_rise_proxy_pct"] > cfg.voltage_rise_limit_pct
    out["any_violation"] = (
        out["overload_violation"]
        | out["reverse_power_violation"]
        | out["voltage_rise_proxy_violation"]
    )
    return out


def summarize(result: pd.DataFrame, cfg: TransformerConfig) -> Dict[str, Any]:
    dt_h = cfg.timestep_minutes / 60.0
    peak_import_kw = float(result["net_kw"].max())
    peak_export_kw = float(result["reverse_power_kw"].max())
    peak_kva = float(result["transformer_kva"].max())

    return {
        "transformer_kva_rating": cfg.kva_rating,
        "peak_import_kw": peak_import_kw,
        "peak_export_kw": peak_export_kw,
        "peak_transformer_kva": peak_kva,
        "peak_loading_pct": float(result["loading_pct"].max()),
        "peak_voltage_rise_proxy_pct": float(result["voltage_rise_proxy_pct"].max()),
        "load_energy_kwh": float((result["load_kw"] * dt_h).sum()),
        "generation_energy_kwh": float((result["generation_kw"] * dt_h).sum()),
        "net_import_energy_kwh": float((result["net_kw"].clip(lower=0) * dt_h).sum()),
        "net_export_energy_kwh": float(((-result["net_kw"]).clip(lower=0) * dt_h).sum()),
        "violation_points": int(result["any_violation"].sum()),
        "overload_points": int(result["overload_violation"].sum()),
        "reverse_power_violation_points": int(result["reverse_power_violation"].sum()),
        "voltage_rise_proxy_violation_points": int(result["voltage_rise_proxy_violation"].sum()),
    }


def sweep_hosting_capacity(
    base: pd.DataFrame,
    cfg: TransformerConfig,
    mode: HostingMode,
    step_kw: float = 1.0,
    max_kw: Optional[float] = None,
    profile_col: Optional[str] = None,
    raw_df: Optional[pd.DataFrame] = None,
) -> Tuple[float, pd.DataFrame]:
    """
    Sweep additional load or generation capacity.

    If profile_col is provided, the added capacity is multiplied by that normalized profile.
    Otherwise, load is added as flat 1.0 profile and generation is added using a simple solar bell curve.
    """
    if step_kw <= 0:
        raise ValueError("step_kw must be positive.")
    if max_kw is None:
        max_kw = 3.0 * cfg.kva_rating

    if profile_col:
        if raw_df is None or profile_col not in raw_df.columns:
            raise ValueError("profile_col was provided but not found in the input CSV.")
        profile = pd.to_numeric(raw_df[profile_col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        profile = np.clip(profile, 0.0, None)
        if profile.max() > 0:
            profile = profile / profile.max()
    elif mode == "generation":
        hours = base["timestamp"].dt.hour.to_numpy() + base["timestamp"].dt.minute.to_numpy() / 60.0
        profile = np.maximum(0.0, np.sin(np.pi * (hours - 6.0) / 12.0))
    else:
        profile = np.ones(len(base))

    feasible_kw = 0.0
    rows: List[Dict[str, Any]] = []

    for added_kw in np.arange(0.0, max_kw + step_kw, step_kw):
        candidate = base.copy()
        if mode == "load":
            candidate["load_kw"] = candidate["load_kw"] + added_kw * profile
        else:
            candidate["generation_kw"] = candidate["generation_kw"] + added_kw * profile
        candidate["net_kw"] = candidate["load_kw"] - candidate["generation_kw"]

        evaluated = evaluate_transformer(candidate, cfg)
        summary = summarize(evaluated, cfg)
        summary["added_kw"] = float(added_kw)
        rows.append(summary)

        if summary["violation_points"] == 0:
            feasible_kw = float(added_kw)
        else:
            break

    return feasible_kw, pd.DataFrame(rows)


def analyze(
    csv_path: Path,
    cfg: TransformerConfig,
    mode: HostingMode,
    step_kw: float,
    max_kw: Optional[float],
    profile_col: Optional[str],
    output_dir: Path,
) -> Dict[str, Any]:
    raw = read_timeseries_csv(csv_path)
    base = aggregate_power(raw)
    result = evaluate_transformer(base, cfg)
    base_summary = summarize(result, cfg)

    hc_kw, sweep = sweep_hosting_capacity(
        base=base,
        cfg=cfg,
        mode=mode,
        step_kw=step_kw,
        max_kw=max_kw,
        profile_col=profile_col,
        raw_df=raw,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_dir / "transformer_timeseries_result.csv", index=False)
    sweep.to_csv(output_dir / f"hosting_capacity_sweep_{mode}.csv", index=False)

    report = {
        "input_csv": str(csv_path),
        "mode": mode,
        "base_case": base_summary,
        "hosting_capacity_added_kw_without_violations": hc_kw,
        "limits": {
            "overload_limit_kva": cfg.overload_limit_kva,
            "reverse_power_limit_kw": cfg.reverse_power_limit_kw,
            "voltage_rise_proxy_limit_pct": cfg.voltage_rise_limit_pct,
        },
        "output_files": [
            str(output_dir / "transformer_timeseries_result.csv"),
            str(output_dir / f"hosting_capacity_sweep_{mode}.csv"),
        ],
    }

    with (output_dir / "hosting_capacity_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transformer hosting capacity time-series analysis.")
    parser.add_argument("--csv", required=True, type=Path, help="Input CSV with timestamp, load_* and gen_* columns in kW.")
    parser.add_argument("--transformer-kva", required=True, type=float, help="Transformer nominal rating in kVA.")
    parser.add_argument("--mode", choices=["load", "generation"], default="generation", help="Added capacity type to sweep.")
    parser.add_argument("--step-kw", type=float, default=1.0, help="Hosting capacity sweep step in kW.")
    parser.add_argument("--max-kw", type=float, default=None, help="Maximum added capacity to test in kW.")
    parser.add_argument("--pf-load", type=float, default=0.92, help="Load power factor for kVA estimate.")
    parser.add_argument("--pf-generation", type=float, default=1.0, help="Generation power factor for kVA estimate.")
    parser.add_argument("--overload-limit-pct", type=float, default=100.0, help="Allowed transformer loading percentage.")
    parser.add_argument("--reverse-power-limit-pct", type=float, default=100.0, help="Allowed reverse power percentage of transformer kVA.")
    parser.add_argument("--voltage-rise-limit-pct", type=float, default=3.0, help="Transformer-only voltage-rise proxy limit.")
    parser.add_argument("--transformer-impedance-pct", type=float, default=4.0, help="Transformer impedance percentage.")
    parser.add_argument("--timestep-minutes", type=int, default=15, help="Time-step duration in minutes.")
    parser.add_argument("--profile-col", default=None, help="Optional normalized profile column to shape added load/gen.")
    parser.add_argument("--output-dir", type=Path, default=Path("hosting_capacity/output"), help="Output directory.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    cfg = TransformerConfig(
        kva_rating=args.transformer_kva,
        pf_load=args.pf_load,
        pf_generation=args.pf_generation,
        overload_limit_pct=args.overload_limit_pct,
        reverse_power_limit_pct=args.reverse_power_limit_pct,
        voltage_rise_limit_pct=args.voltage_rise_limit_pct,
        transformer_impedance_pct=args.transformer_impedance_pct,
        timestep_minutes=args.timestep_minutes,
    )
    report = analyze(
        csv_path=args.csv,
        cfg=cfg,
        mode=args.mode,
        step_kw=args.step_kw,
        max_kw=args.max_kw,
        profile_col=args.profile_col,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
