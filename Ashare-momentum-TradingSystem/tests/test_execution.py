from ashare_momentum.execution import PositionOwnership


def test_legacy_position_protects_manual_inventory() -> None:
    ownership = PositionOwnership.migrate_legacy_position(
        stock_code="SAMPLE.SH",
        broker_quantity=3100,
        planned_quantity=100,
        recorded_quantity=3100,
    )
    assert ownership.managed_quantity == 100
    assert ownership.manual_quantity_floor == 3000
    assert ownership.sellable_quantity(3100) == 100
    assert ownership.reconcile_after_sell(3000) == 0


def test_new_strategy_buy_only_owns_incremental_shares() -> None:
    ownership = PositionOwnership.before_strategy_buy(
        stock_code="SAMPLE.SH",
        broker_quantity=600,
        planned_quantity=900,
    )
    assert ownership.reconcile_after_buy(1500) == 900
    assert ownership.sellable_quantity(1500) == 900
    assert ownership.manual_quantity_floor == 600

