"""Provide small helpers for symbol filtering and exchange metadata loading."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import stable_symbol


def load_min_qty(file_path: Path) -> tuple[int, dict[str, int]]:
    """Load minimum tradable quantity metadata and convert it into decimal precision."""
    min_qty_df = pd.read_csv(file_path, encoding="utf-8-sig")
    min_qty_df["min_qty"] = -np.log10(min_qty_df["min_qty"]).round().astype(int)
    default_min_qty = int(min_qty_df["min_qty"].max())
    min_qty_df = min_qty_df.set_index("symbol")
    return default_min_qty, min_qty_df["min_qty"].to_dict()


def is_trade_symbol(symbol: str, black_list: tuple | list = ()) -> bool:
    """Exclude non-USDT pairs, stablecoins, levered tokens, and blacklisted assets."""
    if not symbol or symbol.startswith(".") or not symbol.endswith("USDT") or symbol in black_list:
        return False

    base_symbol = symbol.upper().replace("-USDT", "USDT")[:-4]
    if (base_symbol.endswith(("UP", "DOWN", "BEAR", "BULL")) and base_symbol != "JUP") or base_symbol in stable_symbol:
        return False
    return True
