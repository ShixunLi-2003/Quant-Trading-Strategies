import numpy as np
import pandas as pd

from ashare_momentum.validation import factor_ic_robustness, newey_west_mean_test


def test_newey_west_mean_test_reports_positive_signal() -> None:
    values = pd.Series([0.01, 0.02, 0.015, 0.025, 0.018, 0.03, 0.022, 0.028])

    result = newey_west_mean_test(values, max_lag=3)

    assert result["n_observations"] == 8
    assert result["mean"] > 0
    assert result["standard_error"] > 0
    assert result["t_stat"] > 0
    assert 0 <= result["p_value_normal"] <= 1


def test_factor_ic_robustness_detects_monotonic_cross_section() -> None:
    rows = []
    for date_index, trade_date in enumerate(pd.date_range("2024-01-02", periods=12, freq="B")):
        for stock_index in range(20):
            factor = float(stock_index)
            rows.append(
                {
                    "trade_date": trade_date,
                    "stock_code": f"anonymous_{stock_index:03d}",
                    "factor": factor,
                    "target": factor + 0.01 * np.sin(date_index + stock_index),
                }
            )
    panel = pd.DataFrame(rows)

    result = factor_ic_robustness(panel, ["factor"], "target", hac_lag=3).iloc[0]

    assert result["n_days"] == 12
    assert result["mean_ic"] > 0.99
    assert result["positive_ic_ratio"] == 1.0
