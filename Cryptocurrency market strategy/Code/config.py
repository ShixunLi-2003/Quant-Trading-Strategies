"""Define data sources, portfolio construction rules, and simulation settings."""

from __future__ import annotations

from pathlib import Path

from core.utils.path_kit import get_folder_path

start_date = "2021-01-01"
end_date = "2026-03-20"

spot_path = Path()
swap_path = Path()

backtest_name = "hk_quant_interview_core"
strategy = {
    "name": "CrossSectionalMomentumMix",
    "hold_period": "21D",
    "long_select_coin_num": 3,
    "short_select_coin_num": "long_nums",
    "factor_list": [
        ("W24", True, (3, 0.1), 1),
        ("W22", True, (1, 1, 10), 1),
        ("W42", False, (0.01, 0.99, True), 1),
        ("PctChange", False, 8, 5),
    ],
    "filter_list": [
        ("QuoteVolumeMean", 13, "pct:<0.55", True),
        ("VolumeMeanRatio", 14, "val:>=0.2", True),
        ("VolumeMeanRatio", 14, "val:<=2", True),
    ],
}

is_pure_long = False
use_offset = True

initial_usdt = 270
leverage = 1
swap_c_rate = 4 / 10000
spot_c_rate = 1 / 1000

min_kline_num = 168
black_list: list[str] = []

backtest_path = Path(get_folder_path("data", "backtest_results"))
stable_symbol = [
    "BKRW",
    "USDC",
    "USDP",
    "TUSD",
    "BUSD",
    "FDUSD",
    "DAI",
    "EUR",
    "GBP",
    "USBP",
    "SUSD",
    "PAXG",
    "AEUR",
]

if (not spot_path.exists()) or (not swap_path.exists()):
    print("Warning: market data paths do not exist. Update Code/config.py before running the pipeline.")
    print(f"spot_path={spot_path}")
    print(f"swap_path={swap_path}")
