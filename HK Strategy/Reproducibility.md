# Reproducibility

This package is self-contained. All commands below assume the working directory is `HK Strategy/Code`.

## Environment

- Python `3.11+`
- `pandas>=2.0`
- `numpy>=1.24`
- `matplotlib>=3.7`
- `vectorbt>=0.26`
- `backtrader>=1.9`

Install dependencies:

```bash
python -m pip install -r configs/requirements.txt
```

## Package-Local Layout

- Project config: `project.json`
- Active strategy config: `configs/vectorbt_w42_bear_defense_recommended.json`
- Equity data: `../HK Data/HK`
- Index data: `../HK Data/hs_index_data`
- Default benchmark: `../HK Data/hs_index_data/Hang_Seng_Index_HSI.csv`
- Output root: `../outputs`

## Reproduction Commands

Run the reported main strategy:

```bash
python scripts/run_vectorbt.py --config configs/vectorbt_w42_bear_defense_recommended.json
```

Generate stage and regime diagnostics:

```bash
python scripts/analyze_strategy_stages.py --config configs/vectorbt_w42_bear_defense_recommended.json --output-subdir strategy_stage_analysis_bear_defense_recommended
```

Run factor diagnostics:

```bash
python scripts/run_factor_analysis.py --config configs/w42_factor_analysis.json
```

Run the Backtrader reference example:

```bash
python scripts/run_backtrader.py --config configs/backtrader_ma_cross.json
```

## Notes

- `src/` is the runnable source tree.
- `src/hk_quant/` is a compatibility namespace that preserves the original import paths inside this standalone package.
- `framework/` is a review-oriented annotated copy of the core implementation.
- Fresh outputs are written to `HK Strategy/outputs/`.
- The research artifacts in this repository were produced from executable local code and package-local data.
