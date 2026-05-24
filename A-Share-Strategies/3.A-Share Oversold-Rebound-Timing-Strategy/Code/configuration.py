"""Current production configuration for the oversold rebound timing strategy."""

import os
from pathlib import Path

start_date = "2010-01-01"
end_date = None

data_center_path = Path(r"F:\quantclass_live\datacenter")
stock_data_path = data_center_path / "stock-trading-data-pro-2026-03-27N"
index_data_path = data_center_path / "stock-main-index-data-2026-03-27"
fin_data_path = data_center_path / "stock-fin-data-xbx-2026-03-28"

strategy = {
    "name": "Oversold Rebound Timing Strategy",
    "hold_period": "5D",
    "select_num": 10,
    "factor_list": [
        ("Volume Contraction Factor", True, (15, 80), 0.5),
        ("Turnover Rate", False, 15, 0.7),
        ("Long-Term Low Volume", True, 30, 0.5),
        ("Oversold", True, 39, 12),
        ("Oversold", True, 270, 2),
        ("Net Capital Inflow", True, [6], 0.08),
    ],
    "filter_list": [
        ("Turnover Rate", 30, "pct:<=0.4"),
        ("Rolling PE", None, "val:<60"),
    ],
}

days_listed = 250
excluded_boards = ["bj"]

equity_timing = {
    "name": "Volume Expansion Moving Average Timing",
    "params": [40, 0.6, 15],
}

initial_cash = 100000
c_rate = 1.2 / 10000
t_rate = 1 / 1000
n_jobs = max((os.cpu_count() or 1) - 1, 1)

if not stock_data_path.exists():
    raise FileNotFoundError(f"Stock data path does not exist: {stock_data_path}")

if not index_data_path.exists():
    raise FileNotFoundError(f"Index data path does not exist: {index_data_path}")
