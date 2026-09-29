"""Paste this file into ALGOGENE Backtest after uploading nasdaq100_dl to /lib."""

from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
import json
from pathlib import Path

MODEL_BUNDLE = "auto"
ORDER_PREFIX = "NDX100DL_"
PLATFORM_MAX_INSTRUMENTS = 100


class AlgoEvent:
    def __init__(self):
        self.evt = None
        self.bundle = None
        self.engine = None
        self.pending_plan = []
        self.order_sequence = 0
        self.top_n = 5
        self.max_capital = 10000.0
        self.limit_buffer = 0.002

    def start(self, mEvt):
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt._include("nasdaq100_dl")
        global inference, online, fundamentals
        import inference
        import online
        import fundamentals

        selected = list(dict.fromkeys(mEvt.get("subscribeList", [])))
        if len(selected) > PLATFORM_MAX_INSTRUMENTS:
            raise RuntimeError("ALGOGENE account limit exceeded: {} > {}".format(
                len(selected), PLATFORM_MAX_INSTRUMENTS))
        if MODEL_BUNDLE == "auto":
            run_root = Path(self.evt.path_lib) / "nasdaq100_dl_runs"
            pointer = json.loads((run_root / "latest.json").read_text(encoding="utf-8"))
            bundle_path = run_root / pointer["bundle"]
        else:
            bundle_path = Path(self.evt.path_lib) / MODEL_BUNDLE
        self.bundle = inference.FrozenBundle(bundle_path)
        settings = self.bundle.manifest["config"]
        self.top_n = int(settings.get("selection_top_n", 5))
        self.max_capital = float(settings.get("initial_capital_usd", 10000))
        self.limit_buffer = float(settings.get("limit_buffer", 0.002))
        universe_path = bundle_path / self.bundle.manifest["universe_file"]
        trained = [line.strip() for line in universe_path.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        context = (self.bundle.manifest["config"].get("market_context", []) +
                   self.bundle.manifest["config"].get("sector_context", []))
        if context:
            raise RuntimeError(
                "platform Nasdaq-100 bundle must use empty external context lists; "
                "all 100 subscription slots are reserved for stocks")
        stocks = [symbol for symbol in trained if symbol in selected]
        missing = [symbol for symbol in trained if symbol not in selected]
        unexpected = [symbol for symbol in selected if symbol not in trained]
        if missing or unexpected or len(stocks) != len(trained):
            raise RuntimeError("subscription must match frozen universe exactly; missing={} "
                               "unexpected={}".format(missing, unexpected))
        fundamental_config = dict(
            self.bundle.manifest["config"].get("fundamentals", {}))
        financial_prefix = str(fundamental_config.get("feature_prefix", "fin_"))
        fundamental_config["feature_columns"] = [
            name[len(financial_prefix):]
            for name in self.bundle.feature_columns
            if name.startswith(financial_prefix)
        ]
        fundamental_table = None
        fundamentals_file = self.bundle.manifest.get("fundamentals_file")
        if fundamental_config.get("enabled", False):
            if not fundamentals_file:
                raise RuntimeError("trained model requires fundamentals but bundle has no table")
            fundamental_table = fundamentals.load_point_in_time_fundamentals(
                bundle_path / fundamentals_file,
                availability_lag_hours=float(
                    fundamental_config.get("availability_lag_hours", 24)))
        self.engine = online.OnlineFeatureEngine(
            stocks, [], fundamentals=fundamental_table,
            fundamental_config=fundamental_config)
        self.evt.consoleLog("MODEL VERIFIED", self.bundle.manifest["job_name"],
                            self.bundle.manifest["model_sha256"][:12], "stocks", str(len(stocks)))
        self.evt.start()

    def _opened_trades(self):
        try:
            _, opened, _ = self.evt.getSystemOrders()
            return opened if isinstance(opened, dict) else {}
        except Exception as exc:
            self.evt.consoleLog("POSITION QUERY ERROR", str(exc)[:120])
            return {}

    def _close_model_positions(self):
        submitted = 0
        for trade_id, item in self._opened_trades().items():
            reference = str(item.get("orderRef", item.get("order_Ref", "")))
            if reference.startswith(ORDER_PREFIX):
                self.evt.sendOrder(AlgoAPIUtil.OrderObject(
                    tradeID=str(trade_id), openclose="close"))
                submitted += 1
        return submitted

    def _submit_pending(self):
        if not self.pending_plan or self._opened_trades():
            return
        budget = self.max_capital / max(self.top_n, 1)
        submitted = 0
        for symbol, score in self.pending_plan:
            price = self.engine.latest_prices.get(symbol)
            if not price:
                continue
            units = int(budget // price)
            if units <= 0:
                continue
            self.order_sequence += 1
            reference = "{}{:08d}".format(ORDER_PREFIX, self.order_sequence)
            self.evt.sendOrder(AlgoAPIUtil.OrderObject(
                instrument=symbol, openclose="open", buysell=1, ordertype=1,
                volume=units, price=round(price * (1.0 + self.limit_buffer), 4),
                orderRef=reference))
            submitted += 1
        self.evt.consoleLog("MODEL ORDERS", str(submitted), str(self.pending_plan))
        self.pending_plan = []

    def on_bulkdatafeed(self, isSync, bd, ab):
        if not isSync or self.engine is None:
            return
        features = self.engine.update(bd)
        if not features.empty:
            usable = features.dropna(subset=self.bundle.feature_columns).copy()
            if not usable.empty:
                usable["score"] = self.bundle.predict(usable)
                ranked = usable.sort_values("score", ascending=False).head(self.top_n)
                self.pending_plan = list(zip(ranked["symbol"], ranked["score"]))
                closed = self._close_model_positions()
                self.evt.consoleLog("NEW MODEL PLAN", str(self.pending_plan), "closed", str(closed))
        self._submit_pending()

    def on_marketdatafeed(self, md, ab):
        pass

    def on_orderfeed(self, of):
        self.evt.consoleLog("ORDER", str(of))

    def on_dailyPLfeed(self, pl):
        self.evt.consoleLog("DAILY PL", str(pl))

    def on_openPositionfeed(self, op, oo, uo):
        pass
