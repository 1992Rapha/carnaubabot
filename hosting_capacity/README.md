# Transformer Hosting Capacity Analysis

Time-series screening tool for transformer hosting capacity with multiple downstream loads and multiple downstream generators.

## What it does

The script aggregates all columns prefixed with:

- `load_` as downstream demand in kW;
- `gen_` as downstream generation in kW.

For each timestamp it calculates:

- total load in kW;
- total generation in kW;
- net transformer power flow in kW;
- transformer apparent loading in kVA;
- loading percentage;
- reverse power/export through the transformer;
- transformer-only voltage-rise proxy;
- overload, reverse-power and voltage-rise-proxy violations.

It also performs a capacity sweep for additional load or additional generation and returns the largest added kW that does not violate the configured transformer limits.

## Input format

CSV with one `timestamp` column and any number of `load_*` and `gen_*` columns.

Example:

```csv
timestamp,load_house_01_kw,load_house_02_kw,gen_pv_01_kw
2026-01-01 12:00,1.4,1.0,6.5
```

All load and generation columns are interpreted as kW.

## Run example

From the repository root:

```bash
python hosting_capacity/hosting_capacity_transformer.py \
  --csv hosting_capacity/example_transformer_timeseries.csv \
  --transformer-kva 45 \
  --mode generation \
  --step-kw 1 \
  --overload-limit-pct 100 \
  --reverse-power-limit-pct 100 \
  --voltage-rise-limit-pct 3 \
  --transformer-impedance-pct 4
```

For added load hosting capacity:

```bash
python hosting_capacity/hosting_capacity_transformer.py \
  --csv hosting_capacity/example_transformer_timeseries.csv \
  --transformer-kva 45 \
  --mode load \
  --step-kw 1
```

## Outputs

By default, files are written to `hosting_capacity/output/`:

- `transformer_timeseries_result.csv`
- `hosting_capacity_sweep_generation.csv` or `hosting_capacity_sweep_load.csv`
- `hosting_capacity_report.json`

## Engineering interpretation

Positive `net_kw` means import from the grid into the transformer secondary loads.

Negative `net_kw` means export/reverse flow from downstream generators through the transformer.

The transformer apparent loading approximation is:

```text
kVA = abs(net_kW / power_factor)
```

The voltage-rise proxy is:

```text
voltage_rise_proxy_% = transformer_impedance_% * export_kVA / transformer_kVA_rating
```

This is only a transformer-level screening indicator. It is not a substitute for feeder voltage calculation.

## Limits checked

| Constraint | Meaning |
|---|---|
| `overload_limit_pct` | Maximum allowed transformer kVA loading |
| `reverse_power_limit_pct` | Maximum allowed export through transformer |
| `voltage_rise_limit_pct` | Maximum transformer-only voltage-rise proxy |

## Limitations

This script does **not** model:

- feeder voltage drop/rise along conductors;
- phase imbalance;
- neutral loading;
- conductor thermal constraints;
- protection coordination;
- short-circuit contribution;
- regulator/capacitor operation;
- harmonic distortion;
- stochastic simultaneity.

For complete distribution hosting capacity, use this as a first screening layer and then validate critical scenarios in OpenDSS, pandapower, DIgSILENT PowerFactory, CYME or equivalent.

## Recommended next extensions

1. Add per-phase columns: `load_a_*`, `load_b_*`, `load_c_*`, `gen_a_*`, etc.
2. Add transformer thermal aging model using top-oil/hot-spot approximation.
3. Add Monte Carlo load/generation scenarios.
4. Export feeder scenarios to OpenDSS.
5. Include voltage limits at customer nodes rather than only transformer proxy.
