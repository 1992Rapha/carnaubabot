#!/usr/bin/env python3
"""
Three-phase transformer hosting capacity analysis with conductor modelling.

This is a screening-level time-series model for multiple loads and generators
connected downstream of a three-phase transformer.

It evaluates:
- per-phase load and generation;
- per-phase net power flow;
- transformer kVA loading;
- phase imbalance;
- estimated neutral current;
- conductor ampacity violation;
- approximate per-phase voltage drop/rise on the secondary conductor;
- hosting capacity sweep for additional three-phase load or generation.

Input column prefixes
---------------------
Loads:
    load_a_*, load_b_*, load_c_* in kW
Generators:
    gen_a_*, gen_b_*, gen_c_* in kW

Engineering note
----------------
This script is a transformer + secondary conductor screening model. It does not
replace a full unbalanced feeder power-flow study. For detailed feeder studies,
use hosting_capacity_opendss.py.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

Phase = Literal["a", "b", "c"]
HostingMode = Literal["load", "generation"]
PHASES: Tuple[Phase, Phase, Phase] = ("a", "b", "c")


@dataclass(frozen=True)
class ConductorConfig:
    name: str
    material: Literal["copper", "aluminum"]
    section_mm2: float
    ampacity_a: float
    r_ohm_per_km: float
    x_ohm_per_km: float = 0.08
    length_m: float = 50.0
    installation: str = "not specified"

    @property
    def length_km(self) -> float:
        return self.length_m / 1000.0

    @property
    def z_abs_ohm(self) -> float:
        return math.hypot(self.r_ohm_per_km, self.x_ohm_per_km) * self.length_km


@dataclass(frozen=True)
class ThreePhaseConfig:
    transformer_kva: float
    line_to_line_voltage_v: float = 380.0
    pf_load: float = 0.92
    pf_generation: float = 1.0
    overload_limit_pct: float = 100.0
    reverse_power_limit_pct: float = 100.0
    voltage_drop_limit_pct: float = 4.0
    voltage_rise_limit_pct: float = 3.0
    imbalance_limit_pct: float = 15.0
    timestep_minutes: int = 15
    conductor: ConductorConfig = ConductorConfig(
        name="Cu 25 mm2 default",
        material="copper",
        section_mm2=25.0,
        ampacity_a=89.0,
        r_ohm_per_km=0.727,
        x_ohm_per_km=0.08,
        length_m=50.0,
        installation="screening default; verify against applicable standard",
    )

    @property
    def phase_voltage_v(self) -> float:
        return self.line_to_line_voltage_v / math.sqrt(3.0)

    @property
    def overload_limit_kva(self) -> float:
        return self.transformer_kva * self.overload_limit_pct / 100.0

    @property
    def reverse_power_limit_kw(self) -> float:
        return self.transformer_kva * self.reverse_power_limit_pct / 100.0


def read_timeseries_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError("CSV must contain a timestamp column.")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    numeric_cols = [c for c in df.columns if c != "timestamp"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return df


def phase_columns(df: pd.DataFrame, kind: Literal["load", "gen"], phase: Phase) -> List[str]:
    prefix = f"{kind}_{phase}_"
    return [c for c in df.columns if c.lower().startswith(prefix)]


def aggregate_three_phase(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"timestamp": df["timestamp"]})
    for ph in PHASES:
        load_cols = phase_columns(df, "load", ph)
        gen_cols = phase_columns(df, "gen", ph)
        out[f"load_{ph}_kw"] = df[load_cols].sum(axis=1) if load_cols else 0.0
        out[f"gen_{ph}_kw"] = df[gen_cols].sum(axis=1) if gen_cols else 0.0
        out[f"net_{ph}_kw"] = out[f"load_{ph}_kw"] - out[f"gen_{ph}_kw"]

    total = sum(out[f"load_{ph}_kw"].abs().sum() + out[f"gen_{ph}_kw"].abs().sum() for ph in PHASES)
    if float(total) == 0.0:
        raise ValueError("No phase columns found. Use load_a_*, load_b_*, load_c_*, gen_a_*, gen_b_*, gen_c_*.")
    return out


def phase_current_a(net_kw: pd.Series, phase_voltage_v: float, pf_import: float, pf_export: float) -> pd.Series:
    pf = np.where(net_kw >= 0, pf_import, pf_export)
    return 1000.0 * np.abs(net_kw) / (phase_voltage_v * pf)


def estimate_neutral_current(ia: pd.Series, ib: pd.Series, ic: pd.Series) -> pd.Series:
    return np.sqrt(np.maximum(ia**2 + ib**2 + ic**2 - ia * ib - ib * ic - ic * ia, 0.0))


def voltage_delta_pct(net_kw: pd.Series, current_a: pd.Series, cfg: ThreePhaseConfig) -> pd.Series:
    dv_v = current_a * cfg.conductor.z_abs_ohm
    sign = np.where(net_kw >= 0, -1.0, 1.0)
    return 100.0 * sign * dv_v / cfg.phase_voltage_v


def evaluate(base: pd.DataFrame, cfg: ThreePhaseConfig) -> pd.DataFrame:
    out = base.copy()

    for ph in PHASES:
        out[f"current_{ph}_a"] = phase_current_a(out[f"net_{ph}_kw"], cfg.phase_voltage_v, cfg.pf_load, cfg.pf_generation)
        out[f"voltage_delta_{ph}_pct"] = voltage_delta_pct(out[f"net_{ph}_kw"], out[f"current_{ph}_a"], cfg)
        out[f"conductor_ampacity_violation_{ph}"] = out[f"current_{ph}_a"] > cfg.conductor.ampacity_a
        out[f"voltage_drop_violation_{ph}"] = out[f"voltage_delta_{ph}_pct"] < -cfg.voltage_drop_limit_pct
        out[f"voltage_rise_violation_{ph}"] = out[f"voltage_delta_{ph}_pct"] > cfg.voltage_rise_limit_pct

    out["total_load_kw"] = sum(out[f"load_{ph}_kw"] for ph in PHASES)
    out["total_generation_kw"] = sum(out[f"gen_{ph}_kw"] for ph in PHASES)
    out["total_net_kw"] = sum(out[f"net_{ph}_kw"] for ph in PHASES)
    out["reverse_power_kw"] = np.maximum(-out["total_net_kw"], 0.0)

    phase_kva = []
    for ph in PHASES:
        pf = np.where(out[f"net_{ph}_kw"] >= 0, cfg.pf_load, cfg.pf_generation)
        kva = np.abs(out[f"net_{ph}_kw"] / pf)
        out[f"phase_{ph}_kva"] = kva
        phase_kva.append(kva)

    out["transformer_kva"] = sum(phase_kva)
    out["loading_pct"] = 100.0 * out["transformer_kva"] / cfg.transformer_kva
    out["neutral_current_a"] = estimate_neutral_current(out["current_a_a"], out["current_b_a"], out["current_c_a"])

    current_avg = (out["current_a_a"] + out["current_b_a"] + out["current_c_a"]) / 3.0
    current_max_dev = pd.concat([
        (out["current_a_a"] - current_avg).abs(),
        (out["current_b_a"] - current_avg).abs(),
        (out["current_c_a"] - current_avg).abs(),
    ], axis=1).max(axis=1)
    out["current_imbalance_pct"] = np.where(current_avg > 0, 100.0 * current_max_dev / current_avg, 0.0)

    out["overload_violation"] = out["transformer_kva"] > cfg.overload_limit_kva
    out["reverse_power_violation"] = out["reverse_power_kw"] > cfg.reverse_power_limit_kw
    out["imbalance_violation"] = out["current_imbalance_pct"] > cfg.imbalance_limit_pct

    violation_cols = ["overload_violation", "reverse_power_violation", "imbalance_violation"]
    for ph in PHASES:
        violation_cols += [
            f"conductor_ampacity_violation_{ph}",
            f"voltage_drop_violation_{ph}",
            f"voltage_rise_violation_{ph}",
        ]
    out["any_violation"] = out[violation_cols].any(axis=1)
    return out


def summarize(result: pd.DataFrame, cfg: ThreePhaseConfig) -> Dict[str, Any]:
    dt_h = cfg.timestep_minutes / 60.0
    summary: Dict[str, Any] = {
        "transformer_kva_rating": cfg.transformer_kva,
        "conductor": asdict(cfg.conductor),
        "peak_transformer_kva": float(result["transformer_kva"].max()),
        "peak_loading_pct": float(result["loading_pct"].max()),
        "peak_import_kw": float(result["total_net_kw"].max()),
        "peak_export_kw": float(result["reverse_power_kw"].max()),
        "peak_neutral_current_a": float(result["neutral_current_a"].max()),
        "peak_current_imbalance_pct": float(result["current_imbalance_pct"].max()),
        "load_energy_kwh": float((result["total_load_kw"] * dt_h).sum()),
        "generation_energy_kwh": float((result["total_generation_kw"] * dt_h).sum()),
        "violation_points": int(result["any_violation"].sum()),
        "overload_points": int(result["overload_violation"].sum()),
        "reverse_power_violation_points": int(result["reverse_power_violation"].sum()),
        "imbalance_violation_points": int(result["imbalance_violation"].sum()),
    }
    for ph in PHASES:
        summary[f"peak_current_{ph}_a"] = float(result[f"current_{ph}_a"].max())
        summary[f"max_voltage_drop_{ph}_pct"] = float(result[f"voltage_delta_{ph}_pct"].min())
        summary[f"max_voltage_rise_{ph}_pct"] = float(result[f"voltage_delta_{ph}_pct"].max())
        summary[f"conductor_ampacity_violation_points_{ph}"] = int(result[f"conductor_ampacity_violation_{ph}"].sum())
        summary[f"voltage_drop_violation_points_{ph}"] = int(result[f"voltage_drop_violation_{ph}"].sum())
        summary[f"voltage_rise_violation_points_{ph}"] = int(result[f"voltage_rise_violation_{ph}"].sum())
    return summary


def sweep_hosting_capacity(base: pd.DataFrame, cfg: ThreePhaseConfig, mode: HostingMode, step_kw: float, max_kw: Optional[float]) -> Tuple[float, pd.DataFrame]:
    if step_kw <= 0:
        raise ValueError("step_kw must be positive.")
    if max_kw is None:
        max_kw = 3.0 * cfg.transformer_kva

    hours = base["timestamp"].dt.hour.to_numpy() + base["timestamp"].dt.minute.to_numpy() / 60.0
    if mode == "generation":
        profile = np.maximum(0.0, np.sin(np.pi * (hours - 6.0) / 12.0))
    else:
        profile = np.ones(len(base))

    feasible_kw = 0.0
    rows: List[Dict[str, Any]] = []
    for added_kw in np.arange(0.0, max_kw + step_kw, step_kw):
        candidate = base.copy()
        per_phase_kw = added_kw / 3.0
        for ph in PHASES:
            if mode == "load":
                candidate[f"load_{ph}_kw"] = candidate[f"load_{ph}_kw"] + per_phase_kw * profile
            else:
                candidate[f"gen_{ph}_kw"] = candidate[f"gen_{ph}_kw"] + per_phase_kw * profile
            candidate[f"net_{ph}_kw"] = candidate[f"load_{ph}_kw"] - candidate[f"gen_{ph}_kw"]

        evaluated = evaluate(candidate, cfg)
        row = summarize(evaluated, cfg)
        row["added_total_three_phase_kw"] = float(added_kw)
        rows.append(row)
        if row["violation_points"] == 0:
            feasible_kw = float(added_kw)
        else:
            break
    return feasible_kw, pd.DataFrame(rows)


def analyze(csv_path: Path, cfg: ThreePhaseConfig, mode: HostingMode, step_kw: float, max_kw: Optional[float], output_dir: Path) -> Dict[str, Any]:
    raw = read_timeseries_csv(csv_path)
    base = aggregate_three_phase(raw)
    result = evaluate(base, cfg)
    base_summary = summarize(result, cfg)
    hc_kw, sweep = sweep_hosting_capacity(base, cfg, mode, step_kw, max_kw)

    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "three_phase_timeseries_result.csv"
    sweep_path = output_dir / f"three_phase_hosting_capacity_sweep_{mode}.csv"
    report_path = output_dir / "three_phase_hosting_capacity_report.json"
    result.to_csv(result_path, index=False)
    sweep.to_csv(sweep_path, index=False)

    report = {
        "input_csv": str(csv_path),
        "mode": mode,
        "base_case": base_summary,
        "hosting_capacity_added_total_three_phase_kw_without_violations": hc_kw,
        "limits": {
            "transformer_overload_limit_kva": cfg.overload_limit_kva,
            "reverse_power_limit_kw": cfg.reverse_power_limit_kw,
            "conductor_ampacity_a": cfg.conductor.ampacity_a,
            "voltage_drop_limit_pct": cfg.voltage_drop_limit_pct,
            "voltage_rise_limit_pct": cfg.voltage_rise_limit_pct,
            "imbalance_limit_pct": cfg.imbalance_limit_pct,
        },
        "output_files": [str(result_path), str(sweep_path), str(report_path)],
    }
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Three-phase transformer hosting capacity with conductor screening.")
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--transformer-kva", required=True, type=float)
    parser.add_argument("--mode", choices=["load", "generation"], default="generation")
    parser.add_argument("--step-kw", type=float, default=1.0)
    parser.add_argument("--max-kw", type=float, default=None)
    parser.add_argument("--line-to-line-voltage-v", type=float, default=380.0)
    parser.add_argument("--pf-load", type=float, default=0.92)
    parser.add_argument("--pf-generation", type=float, default=1.0)
    parser.add_argument("--overload-limit-pct", type=float, default=100.0)
    parser.add_argument("--reverse-power-limit-pct", type=float, default=100.0)
    parser.add_argument("--voltage-drop-limit-pct", type=float, default=4.0)
    parser.add_argument("--voltage-rise-limit-pct", type=float, default=3.0)
    parser.add_argument("--imbalance-limit-pct", type=float, default=15.0)
    parser.add_argument("--timestep-minutes", type=int, default=15)
    parser.add_argument("--conductor-name", default="Cu 25 mm2")
    parser.add_argument("--conductor-material", choices=["copper", "aluminum"], default="copper")
    parser.add_argument("--conductor-section-mm2", type=float, default=25.0)
    parser.add_argument("--conductor-ampacity-a", type=float, default=89.0)
    parser.add_argument("--conductor-r-ohm-km", type=float, default=0.727)
    parser.add_argument("--conductor-x-ohm-km", type=float, default=0.08)
    parser.add_argument("--conductor-length-m", type=float, default=50.0)
    parser.add_argument("--conductor-installation", default="screening default; verify against applicable standard")
    parser.add_argument("--output-dir", type=Path, default=Path("hosting_capacity/output"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    conductor = ConductorConfig(
        name=args.conductor_name,
        material=args.conductor_material,
        section_mm2=args.conductor_section_mm2,
        ampacity_a=args.conductor_ampacity_a,
        r_ohm_per_km=args.conductor_r_ohm_km,
        x_ohm_per_km=args.conductor_x_ohm_km,
        length_m=args.conductor_length_m,
        installation=args.conductor_installation,
    )
    cfg = ThreePhaseConfig(
        transformer_kva=args.transformer_kva,
        line_to_line_voltage_v=args.line_to_line_voltage_v,
        pf_load=args.pf_load,
        pf_generation=args.pf_generation,
        overload_limit_pct=args.overload_limit_pct,
        reverse_power_limit_pct=args.reverse_power_limit_pct,
        voltage_drop_limit_pct=args.voltage_drop_limit_pct,
        voltage_rise_limit_pct=args.voltage_rise_limit_pct,
        imbalance_limit_pct=args.imbalance_limit_pct,
        timestep_minutes=args.timestep_minutes,
        conductor=conductor,
    )
    report = analyze(args.csv, cfg, args.mode, args.step_kw, args.max_kw, args.output_dir)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
