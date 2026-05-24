# Factor Library

This package contains the factor implementations used by the current strategy configuration.

- `volume_contraction_factor.py`: short-vs-long turnover compression.
- `turnover_rate.py`: rolling turnover-rate intensity.
- `long_term_low_volume.py`: long-window low-volume profile.
- `oversold.py`: configurable lookback drawdown signal.
- `net_capital_inflow.py`: short-window price-turnover flow proxy.
- `rolling_pe.py`: rolling PE filter based on TTM net profit.
