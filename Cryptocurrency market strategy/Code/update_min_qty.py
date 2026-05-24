"""Download exchange lot-size metadata used to discretize target positions."""

from __future__ import annotations

from pathlib import Path

import ccxt
import pandas as pd

from core.utils.path_kit import get_folder_path

min_qty_path = Path(get_folder_path("data", "min_qty"))


def _normalize_symbol(raw_symbol: str) -> str:
    if raw_symbol.endswith("USDT"):
        return raw_symbol.replace("USDT", "-USDT")
    if raw_symbol.endswith("BUSD"):
        return raw_symbol.replace("BUSD", "-BUSD")
    return raw_symbol


def update(proxies: dict | None = None) -> None:
    """Refresh minimum tradable quantity files for spot and perpetual markets."""
    exchange = ccxt.binance({"proxies": proxies or {}})

    for market in ("swap", "spot"):
        data = (
            exchange.fapiPublicGetExchangeInfo()
            if market == "swap"
            else exchange.publicGetExchangeInfo()
        )
        symbols = [
            item for item in data["symbols"]
            if item["symbol"].endswith("USDT") or item["symbol"].endswith("BUSD")
        ]

        rows = [
            {
                "symbol": _normalize_symbol(item["symbol"]),
                "min_qty": item["filters"][1]["minQty"],
            }
            for item in symbols
        ]
        new_df = pd.DataFrame(rows)
        file_path = min_qty_path / f"min_qty_{market}.csv"

        if file_path.exists():
            old_df = pd.read_csv(file_path, encoding="utf-8-sig")
            all_data = pd.concat([new_df, old_df], ignore_index=True)
        else:
            all_data = new_df

        all_data = all_data.drop_duplicates(subset=["symbol"], keep="first")
        all_data.to_csv(file_path, encoding="utf-8-sig", index=False)
        print(f"Updated {market} lot sizes: {len(all_data):,} symbols")


if __name__ == "__main__":
    update()
