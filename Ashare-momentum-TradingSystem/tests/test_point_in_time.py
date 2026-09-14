import pandas as pd

from ashare_momentum.data import enforce_point_in_time_universe
from ashare_momentum.risk import build_etf_exposure_schedule


def test_universe_membership_respects_effective_dates() -> None:
    observations = pd.DataFrame(
        {
            "stock_code": ["SAMPLE.SH", "SAMPLE.SH", "SAMPLE.SH"],
            "trade_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "close": [10.0, 10.1, 10.2],
        }
    )
    membership = pd.DataFrame(
        {
            "stock_code": ["SAMPLE.SH"],
            "effective_from": ["2026-01-02"],
            "effective_to": ["2026-01-03"],
        }
    )
    result = enforce_point_in_time_universe(observations, membership)
    assert result["trade_date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-01-02", "2026-01-03"]


def test_etf_exposure_is_effective_next_session() -> None:
    regime = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]),
            "breadth": [0.7, 0.3, 0.2, 0.8],
        }
    )
    schedule = build_etf_exposure_schedule(
        regime,
        breadth_threshold=0.5,
        confirmation_days=2,
        half_after=2,
        cash_after=3,
    )
    assert schedule.loc[2, "risk_exposure"] == 0.5
    assert schedule.loc[2, "effective_trade_date"] == pd.Timestamp("2026-01-08")
