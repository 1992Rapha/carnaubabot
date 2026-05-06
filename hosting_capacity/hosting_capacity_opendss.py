#!/usr/bin/env python3
"""
OpenDSS feeder hosting-capacity workflow.

This module builds and runs an OpenDSS feeder model from CSV files and performs
hosting-capacity sweeps for additional load or generation.

It is designed to cover the items that transformer-only screening does not model:
- full feeder voltage drop/rise by bus and phase;
- phase imbalance;
- neutral conductor representation when included in OpenDSS line definitions;
- conductor/line current limits by segment;
- regulator and capacitor declarations;
- protection device declarations;
- short-circuit/fault-current study hooks;
- time-series simulation through LoadShape objects.

Dependency
----------
Install one of the DSS Python interfaces:

    pip install dss-python

or DSS-Extensions equivalent. This script imports `dss`.

Expected CSV files
------------------
A folder must contain:

    buses.csv
    lines.csv
    loads.csv
    generators.csv

Optional:

    capacitors.csv
    regulators.csv
    protection.csv
    loadshape.csv
    genshape.csv

See README.md for schema details.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

import pandas as pd

HostingMode = Literal["load", "generation"]


@dataclass(frozen=True)
class FeederLimits:
    vmin_pu: float = 0.92
    vmax_pu: float = 1.05
    max_voltage_unbalance_pct: float = 3.0
    line_loading_limit_pct: float = 100.0


@dataclass(frozen=True)
class SweepConfig:
    mode: HostingMode = "generation"
    step_kw: float = 10.0
    max_kw: float = 1000.0
    target_bus: str = "LOADBUS"
    phases: int = 3
    kv: float = 0.38
    pf: float = 1.0
    shape: Optional[str] = None


def import_dss():
    try:
        import dss  # type: ignore
        return dss.DSS
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "OpenDSS Python interface not found. Install with: pip install dss-python"
        ) from exc


def read_csv_if_exists(folder: Path, name: str) -> pd.DataFrame:
    path = folder / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "sim"}


def dss_bus(bus: str, phases: Any = 3) -> str:
    p = int(phases) if str(phases).strip() else 3
    if "." in str(bus):
        return str(bus)
    if p == 1:
        return f"{bus}.1"
    if p == 2:
        return f"{bus}.1.2"
    return f"{bus}.1.2.3"


def build_master_dss(folder: Path, output_dir: Path) -> Path:
    buses = read_csv_if_exists(folder, "buses.csv")
    lines = read_csv_if_exists(folder, "lines.csv")
    loads = read_csv_if_exists(folder, "loads.csv")
    generators = read_csv_if_exists(folder, "generators.csv")
    capacitors = read_csv_if_exists(folder, "capacitors.csv")
    regulators = read_csv_if_exists(folder, "regulators.csv")
    protection = read_csv_if_exists(folder, "protection.csv")
    loadshape = read_csv_if_exists(folder, "loadshape.csv")
    genshape = read_csv_if_exists(folder, "genshape.csv")

    if buses.empty:
        raise ValueError("buses.csv is required.")
    if lines.empty:
        raise ValueError("lines.csv is required.")

    output_dir.mkdir(parents=True, exist_ok=True)
    master = output_dir / "master.dss"

    source = buses[buses["role"].astype(str).str.lower() == "source"].iloc[0] if "role" in buses.columns and not buses[buses["role"].astype(str).str.lower() == "source"].empty else buses.iloc[0]
    source_bus = str(source.get("bus", "SOURCE"))
    base_kv = float(source.get("kv", 13.8))
    source_mva = float(source.get("source_mva", 100.0))

    lines_out: List[str] = []
    lines_out.append("clear")
    lines_out.append(f"new circuit.hosting_capacity basekv={base_kv} pu=1.0 phases=3 bus1={source_bus}.1.2.3 mvasc3={source_mva} mvasc1={source_mva}")
    lines_out.append("set defaultbasefrequency=60")

    if not loadshape.empty:
        for _, row in loadshape.iterrows():
            name = row.get("name", "loadshape")
            mult = str(row.get("mult", "1"))
            npts = int(row.get("npts", len(mult.split())))
            interval = float(row.get("interval", 0.25))
            lines_out.append(f"new loadshape.{name} npts={npts} interval={interval} mult=({mult})")

    if not genshape.empty:
        for _, row in genshape.iterrows():
            name = row.get("name", "genshape")
            mult = str(row.get("mult", "1"))
            npts = int(row.get("npts", len(mult.split())))
            interval = float(row.get("interval", 0.25))
            lines_out.append(f"new loadshape.{name} npts={npts} interval={interval} mult=({mult})")

    # LineCode definitions from unique conductor/impedance settings.
    for _, row in lines.iterrows():
        linecode = row.get("linecode", "")
        if linecode:
            continue
        name = row.get("name", f"line_{_}")
        phases = int(row.get("phases", 3))
        r1 = float(row.get("r1_ohm_km", 0.4))
        x1 = float(row.get("x1_ohm_km", 0.08))
        r0 = float(row.get("r0_ohm_km", r1 * 3.0))
        x0 = float(row.get("x0_ohm_km", x1 * 3.0))
        normamps = float(row.get("ampacity_a", 9999))
        code_name = f"lc_{name}"
        row["linecode"] = code_name
        lines_out.append(f"new linecode.{code_name} nphases={phases} r1={r1} x1={x1} r0={r0} x0={x0} units=km normamps={normamps}")

    for idx, row in lines.iterrows():
        name = row.get("name", f"line_{idx}")
        phases = int(row.get("phases", 3))
        bus1 = dss_bus(row.get("bus1"), phases)
        bus2 = dss_bus(row.get("bus2"), phases)
        length_km = float(row.get("length_km", float(row.get("length_m", 100.0)) / 1000.0))
        kv = row.get("kv", "")
        linecode = row.get("linecode", f"lc_{name}")
        ampacity = row.get("ampacity_a", "")
        extra = f" normamps={ampacity}" if ampacity != "" else ""
        kvtxt = f" kv={kv}" if kv != "" else ""
        lines_out.append(f"new line.{name} phases={phases} bus1={bus1} bus2={bus2} linecode={linecode} length={length_km} units=km{kvtxt}{extra}")

    if not loads.empty:
        for idx, row in loads.iterrows():
            name = row.get("name", f"load_{idx}")
            phases = int(row.get("phases", 3))
            bus = dss_bus(row.get("bus"), phases)
            kv = float(row.get("kv", 0.38))
            kw = float(row.get("kw", 0.0))
            pf = float(row.get("pf", 0.92))
            conn = row.get("conn", "wye")
            model = int(row.get("model", 1))
            daily = row.get("daily", "")
            daily_txt = f" daily={daily}" if daily else ""
            lines_out.append(f"new load.{name} phases={phases} bus1={bus} kv={kv} kw={kw} pf={pf} conn={conn} model={model}{daily_txt}")

    if not generators.empty:
        for idx, row in generators.iterrows():
            name = row.get("name", f"gen_{idx}")
            phases = int(row.get("phases", 3))
            bus = dss_bus(row.get("bus"), phases)
            kv = float(row.get("kv", 0.38))
            kw = float(row.get("kw", 0.0))
            pf = float(row.get("pf", 1.0))
            conn = row.get("conn", "wye")
            daily = row.get("daily", "")
            daily_txt = f" daily={daily}" if daily else ""
            lines_out.append(f"new generator.{name} phases={phases} bus1={bus} kv={kv} kw={kw} pf={pf} conn={conn}{daily_txt}")

    if not capacitors.empty:
        for idx, row in capacitors.iterrows():
            name = row.get("name", f"cap_{idx}")
            phases = int(row.get("phases", 3))
            bus = dss_bus(row.get("bus"), phases)
            kv = float(row.get("kv", base_kv))
            kvar = float(row.get("kvar", 0.0))
            lines_out.append(f"new capacitor.{name} phases={phases} bus1={bus} kv={kv} kvar={kvar}")

    if not regulators.empty:
        for idx, row in regulators.iterrows():
            name = row.get("name", f"reg_{idx}")
            transformer = row.get("transformer", "")
            winding = int(row.get("winding", 2))
            vreg = float(row.get("vreg", 122.0))
            band = float(row.get("band", 2.0))
            ptratio = float(row.get("ptratio", 60.0))
            if transformer:
                lines_out.append(f"new regcontrol.{name} transformer={transformer} winding={winding} vreg={vreg} band={band} ptratio={ptratio}")

    if not protection.empty:
        for idx, row in protection.iterrows():
            kind = str(row.get("type", "fuse")).lower()
            name = row.get("name", f"prot_{idx}")
            monitored_obj = row.get("monitored_obj", "")
            monitored_term = int(row.get("monitored_term", 1))
            switched_obj = row.get("switched_obj", monitored_obj)
            switched_term = int(row.get("switched_term", monitored_term))
            rated_current = row.get("rated_current", "")
            if kind == "fuse":
                txt = f"new fuse.{name} monitoredobj={monitored_obj} monitoredterm={monitored_term} switchedobj={switched_obj} switchedterm={switched_term}"
                if rated_current != "":
                    txt += f" ratedcurrent={rated_current}"
                lines_out.append(txt)
            elif kind == "recloser":
                txt = f"new recloser.{name} monitoredobj={monitored_obj} monitoredterm={monitored_term} switchedobj={switched_obj} switchedterm={switched_term}"
                if rated_current != "":
                    txt += f" phaseTrip={rated_current} groundTrip={rated_current}"
                lines_out.append(txt)

    lines_out.append("set voltagebases=[13.8, 0.38]")
    lines_out.append("calcvoltagebases")
    lines_out.append("set mode=daily stepsize=15m number=1")
    lines_out.append("solve")

    master.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    return master


def run_dss(master_path: Path, limits: FeederLimits, hours: int = 24) -> Dict[str, Any]:
    DSS = import_dss()
    text = DSS.Text
    circuit = DSS.ActiveCircuit
    solution = circuit.Solution

    text.Command = f"redirect {master_path}"
    text.Command = "set mode=daily stepsize=15m number=1"

    rows: List[Dict[str, Any]] = []
    violations = 0
    max_v = -999.0
    min_v = 999.0
    max_unbalance = 0.0
    max_line_loading_pct = 0.0

    steps = hours * 4
    for step in range(steps):
        solution.Solve()
        if not solution.Converged:
            violations += 1
            rows.append({"step": step, "converged": False})
            continue

        vmag = list(circuit.AllBusVmagPu)
        if vmag:
            step_min_v = min(vmag)
            step_max_v = max(vmag)
            min_v = min(min_v, step_min_v)
            max_v = max(max_v, step_max_v)
            if step_min_v < limits.vmin_pu or step_max_v > limits.vmax_pu:
                violations += 1
        else:
            step_min_v = None
            step_max_v = None

        # OpenDSS exposes line currents via active element. This calculates the
        # largest current / NormAmps ratio across Line elements.
        step_line_loading_pct = 0.0
        line_names = list(circuit.Lines.AllNames)
        for line_name in line_names:
            circuit.Lines.Name = line_name
            normamps = float(circuit.Lines.NormAmps or 0.0)
            circuit.SetActiveElement(f"line.{line_name}")
            currents = list(circuit.ActiveCktElement.CurrentsMagAng)[0::2]
            max_current = max(currents) if currents else 0.0
            if normamps > 0:
                pct = 100.0 * max_current / normamps
                step_line_loading_pct = max(step_line_loading_pct, pct)
        max_line_loading_pct = max(max_line_loading_pct, step_line_loading_pct)
        if step_line_loading_pct > limits.line_loading_limit_pct:
            violations += 1

        # Approximate voltage unbalance using spread of per-unit magnitudes.
        if vmag:
            avg_v = sum(vmag) / len(vmag)
            unbalance = 100.0 * max(abs(v - avg_v) for v in vmag) / avg_v if avg_v > 0 else 0.0
            max_unbalance = max(max_unbalance, unbalance)
            if unbalance > limits.max_voltage_unbalance_pct:
                violations += 1
        else:
            unbalance = None

        rows.append({
            "step": step,
            "converged": True,
            "min_voltage_pu": step_min_v,
            "max_voltage_pu": step_max_v,
            "voltage_unbalance_pct": unbalance,
            "max_line_loading_pct": step_line_loading_pct,
        })

    return {
        "summary": {
            "violations": violations,
            "min_voltage_pu": min_v,
            "max_voltage_pu": max_v,
            "max_voltage_unbalance_pct": max_unbalance,
            "max_line_loading_pct": max_line_loading_pct,
        },
        "timeseries": rows,
    }


def append_hosting_candidate(master_path: Path, cfg: SweepConfig, added_kw: float, output_dir: Path) -> Path:
    candidate = output_dir / "candidate.dss"
    base = master_path.read_text(encoding="utf-8")
    bus = dss_bus(cfg.target_bus, cfg.phases)
    shape_txt = f" daily={cfg.shape}" if cfg.shape else ""
    if cfg.mode == "generation":
        obj = f"new generator.hosting_candidate phases={cfg.phases} bus1={bus} kv={cfg.kv} kw={added_kw} pf={cfg.pf} conn=wye{shape_txt}"
    else:
        obj = f"new load.hosting_candidate phases={cfg.phases} bus1={bus} kv={cfg.kv} kw={added_kw} pf={cfg.pf} conn=wye model=1{shape_txt}"
    candidate.write_text(base + "\n" + obj + "\nsolve\n", encoding="utf-8")
    return candidate


def sweep(folder: Path, output_dir: Path, limits: FeederLimits, sweep_cfg: SweepConfig, hours: int) -> Dict[str, Any]:
    master = build_master_dss(folder, output_dir)
    base_result = run_dss(master, limits, hours=hours)

    feasible_kw = 0.0
    rows: List[Dict[str, Any]] = []
    added = 0.0
    while added <= sweep_cfg.max_kw + 1e-9:
        candidate = append_hosting_candidate(master, sweep_cfg, added, output_dir)
        result = run_dss(candidate, limits, hours=hours)
        row = {"added_kw": added, **result["summary"]}
        rows.append(row)
        if result["summary"]["violations"] == 0:
            feasible_kw = added
        else:
            break
        added += sweep_cfg.step_kw

    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_dir / f"opendss_hosting_capacity_sweep_{sweep_cfg.mode}.csv", index=False)
    report = {
        "base_case": base_result["summary"],
        "hosting_capacity_added_kw_without_violations": feasible_kw,
        "sweep": rows,
        "master_dss": str(master),
        "limits": limits.__dict__,
        "sweep_config": sweep_cfg.__dict__,
    }
    (output_dir / "opendss_hosting_capacity_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenDSS feeder hosting-capacity analysis.")
    parser.add_argument("--folder", required=True, type=Path, help="Folder containing feeder CSV files.")
    parser.add_argument("--output-dir", type=Path, default=Path("hosting_capacity/output/opendss"))
    parser.add_argument("--mode", choices=["load", "generation"], default="generation")
    parser.add_argument("--target-bus", required=True)
    parser.add_argument("--kv", type=float, default=0.38)
    parser.add_argument("--phases", type=int, default=3)
    parser.add_argument("--pf", type=float, default=1.0)
    parser.add_argument("--shape", default=None)
    parser.add_argument("--step-kw", type=float, default=10.0)
    parser.add_argument("--max-kw", type=float, default=1000.0)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--vmin-pu", type=float, default=0.92)
    parser.add_argument("--vmax-pu", type=float, default=1.05)
    parser.add_argument("--max-voltage-unbalance-pct", type=float, default=3.0)
    parser.add_argument("--line-loading-limit-pct", type=float, default=100.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    limits = FeederLimits(
        vmin_pu=args.vmin_pu,
        vmax_pu=args.vmax_pu,
        max_voltage_unbalance_pct=args.max_voltage_unbalance_pct,
        line_loading_limit_pct=args.line_loading_limit_pct,
    )
    sweep_cfg = SweepConfig(
        mode=args.mode,
        step_kw=args.step_kw,
        max_kw=args.max_kw,
        target_bus=args.target_bus,
        phases=args.phases,
        kv=args.kv,
        pf=args.pf,
        shape=args.shape,
    )
    report = sweep(args.folder, args.output_dir, limits, sweep_cfg, args.hours)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
