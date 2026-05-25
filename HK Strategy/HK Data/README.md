# HK Data

This directory contains the package-local market data snapshot used by the strategy package.

## Structure

- `HK/`: daily stock-level OHLCV and turnover CSV files in wide-universe single-name format.
- `hs_index_data/`: benchmark and sector index CSV files used for regime detection and reference comparison.

## Naming Convention

All index files in `hs_index_data/` use English filenames:

- `Hang_Seng_Index_HSI.csv`
- `Hang_Seng_China_Enterprises_Index_ETF_2828_HK.csv`
- `Hang_Seng_Tech_Index_ETF_3067_HK.csv`
- `Hang_Seng_Finance_Subindex_HSNF.csv`
- `Hang_Seng_Utilities_Subindex_HSNU.csv`

## Equity File Format

Each stock file follows the pattern `price_<symbol>.csv` and contains:

- `timetag`
- `open`
- `high`
- `low`
- `close`
- `volumn`
- `amount`
- `open_ineterst`

## Notes

- Equity data in this package supports the research sample used in the report.
- The package-local configuration in `Code/project.json` resolves all paths against this directory.
