from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PositionOwnership:
    stock_code: str
    planned_quantity: int
    managed_quantity: int = 0
    manual_quantity_floor: int = 0

    @classmethod
    def before_strategy_buy(
        cls,
        stock_code: str,
        broker_quantity: int,
        planned_quantity: int,
    ) -> "PositionOwnership":
        return cls(
            stock_code=stock_code,
            planned_quantity=max(int(planned_quantity), 0),
            managed_quantity=0,
            manual_quantity_floor=max(int(broker_quantity), 0),
        )

    @classmethod
    def migrate_legacy_position(
        cls,
        stock_code: str,
        broker_quantity: int,
        planned_quantity: int,
        recorded_quantity: int,
    ) -> "PositionOwnership":
        planned = max(int(planned_quantity), 0)
        recorded = max(int(recorded_quantity), 0)
        managed = min(planned, recorded) if planned and recorded else planned or recorded
        return cls(
            stock_code=stock_code,
            planned_quantity=planned,
            managed_quantity=managed,
            manual_quantity_floor=max(int(broker_quantity) - managed, 0),
        )

    def reconcile_after_buy(self, broker_quantity: int) -> int:
        acquired = max(int(broker_quantity) - self.manual_quantity_floor, 0)
        self.managed_quantity = min(acquired, self.planned_quantity)
        return self.managed_quantity

    def sellable_quantity(self, broker_quantity: int) -> int:
        available_above_manual_floor = max(int(broker_quantity) - self.manual_quantity_floor, 0)
        return min(self.managed_quantity, available_above_manual_floor)

    def reconcile_after_sell(self, broker_quantity: int) -> int:
        self.managed_quantity = self.sellable_quantity(broker_quantity)
        return self.managed_quantity

