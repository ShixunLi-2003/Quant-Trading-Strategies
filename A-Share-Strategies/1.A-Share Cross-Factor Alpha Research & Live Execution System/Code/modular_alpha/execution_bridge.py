"""
HTTP execution bridge for forwarding target signals to a QMT gateway.

The goal of this file is to isolate external side effects. Portfolio logic
generates normalized target orders, while this bridge is responsible only for
payload shaping, symbol normalization, and network transport.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from .strategy_config import ExecutionConfig
from .strategy_types import TradeSignal


class QmtExecutionBridge:
    """Thin adapter around the cloud QMT order endpoint."""

    def __init__(
        self,
        settings: ExecutionConfig,
        session: requests.Session | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.logger = logger or logging.getLogger(__name__)

    @staticmethod
    def normalize_security_code(security: str) -> str:
        """Converts JoinQuant-style symbols to QMT exchange suffixes."""

        return security.replace(".XSHE", ".SZ").replace(".XSHG", ".SH")

    def build_payload(self, signal: TradeSignal) -> dict[str, Any]:
        """Builds the request payload for the QMT bridge."""

        order_type = (
            self.settings.buy_order_type if signal.is_buy else self.settings.sell_order_type
        )
        return {
            "stock_code": self.normalize_security_code(signal.security),
            "price": float(signal.price),
            "quantity": int(abs(signal.quantity)),
            "order_type": order_type,
        }

    def send_signal(self, signal: TradeSignal) -> dict[str, Any]:
        """Sends one trade signal to the execution endpoint."""

        payload = self.build_payload(signal)
        response = self.session.post(
            self.settings.order_url,
            json=payload,
            timeout=self.settings.http_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        self.logger.info(
            "QMT signal sent | %s | %s | qty=%s | px=%.2f | reason=%s",
            payload["stock_code"],
            "BUY" if signal.is_buy else "SELL",
            payload["quantity"],
            payload["price"],
            signal.reason,
        )
        return body
