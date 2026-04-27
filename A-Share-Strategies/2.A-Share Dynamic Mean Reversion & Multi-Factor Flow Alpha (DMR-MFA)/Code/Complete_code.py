'''
================================================================================
STRATEGY PROFILE: DMR-MFA (Dynamic Mean Reversion & Multi-Factor Flow Alpha)
================================================================================

1. MARKET REGIME ADAPTATION (Volatility-Based Exposure):
   Utilizes Bollinger Bands on the HS300 Index to define the market environment:
   - Bullish Regime (Price > Upper Band): Aggressive exposure (Max 7 holdings).
   - Bearish Regime (Price < Lower Band): Defensive exposure (Min 3 holdings).
   - Neutral Regime (Within Bands): Benchmark exposure (Base 5 holdings).

2. ALPHA SIGNAL GENERATION (Selection Logic):
   - Universe: A curated watchlist of 33 high-liquidity core equities.
   - Mean Reversion Factor: Identifies technical oversold conditions where the 
     asset is in a 10-day downtrend with a specific 3-day drawdown > 7%.
   - Money Flow Filtering: Integrates Level-2 "Net Main Inflow" data to ensure 
     institutional support during price rebounds, filtering out "falling knives."

3. MULTI-LAYERED RISK MANAGEMENT (Exit Strategy):
   - Static Constraints: 15% Take-Profit (TP) and -3.5% Hard Stop-Loss (SL).
   - OBV Divergence Exit: Detects price-volume exhaustion (OBV making new highs 
     while price stagnates) to lock in gains during weak technical rebounds.
   - BBI Dynamic Stop-Loss: Monitors the Bull and Bear Index (BBI) slope; if 
     PnL < -3% and the trend turns negative, the position is liquidated early.

4. EXECUTION & REBALANCING:
   - Dynamic Capacity Adjustment: Re-calibrates portfolio size daily at open.
   - Performance Pruning: When downsizing is required, the strategy prioritizes 
     selling lower-performing assets to maintain portfolio alpha.
================================================================================
'''
import jqdata
import numpy as np
import pandas as pd
from datetime import timedelta
from jqdata import get_money_flow

def initialize(context):
    log.info("=== Initialize: Oversold Rebound + Dynamic Positioning (3/5/7) + MFI Factor + Technical Exit ===")
    
    # ---------- System Settings ----------
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_slippage(FixedSlippage(0.002))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, 
                             open_commission=0.0003, close_commission=0.0003,
                             min_commission=5), type='stock')
    
    # ---------- Strategy Parameters ----------
    g.base_stock_num = 5                # Base portfolio size
    g.stock_num = 5                     # Active target portfolio size (dynamic)
    g.max_stock_num = 7                 # Upper bound for risk-on regime
    g.min_stock_num = 3                 # Lower bound for risk-off regime
    g.take_profit_pct = 0.15            # Static take-profit threshold
    g.stop_loss_pct = -0.035            # Static stop-loss threshold
    
    g.lookback_days = 10                # Momentum lookback window
    g.drop_days = 3                     # Reversion observation window
    g.drop_threshold = -0.07            # Entry trigger: n-day drawdown threshold
    
    # ---------- Bollinger Band Regime Parameters ----------
    g.bb_period = 20                    # Benchmark volatility window
    g.bb_std_multiplier = 2             # Standard deviation multiplier
    
    # ---------- Investment Universe (Customized 33-Ticker Pool) ----------
    g.stock_pool = [
        '601117.XSHG', '601600.XSHG', '601888.XSHG', '300274.XSHE', '300750.XSHE',
        '601919.XSHG', '002049.XSHE', '603881.XSHG', '002335.XSHE', '600089.XSHG',
        '002236.XSHE', '002056.XSHE', '300866.XSHE', '002611.XSHE', '600760.XSHG',
        '300693.XSHE', '002402.XSHE', '002600.XSHE', '300207.XSHE', '603486.XSHG',
        '000591.XSHE', '000027.XSHE', '600011.XSHG', '601899.XSHG', '603799.XSHG',
        '002340.XSHE', '002780.XSHE', '600160.XSHG', '601225.XSHG', '002555.XSHE',
        '600803.XSHG', '300059.XSHE', '002736.XSHE',
    ]
    
    g.days = 0
    g.portfolio_high = None
    
    # Pre-market: NAV peak recording
    run_daily(before_market_open, time='before_open')
    # Market Open: Dynamic rebalancing and signal execution
    run_daily(market_open, time='open')
    # Intraday: Risk control and exit signal monitoring
    run_daily(check_stop_loss_take_profit, time='11:25')
    run_daily(check_stop_loss_take_profit, time='14:50')

def before_market_open(context):
    if g.portfolio_high is None:
        g.portfolio_high = context.portfolio.total_value
    else:
        g.portfolio_high = max(g.portfolio_high, context.portfolio.total_value)

def market_open(context):
    g.days += 1
    # 1. Update target exposure based on HS300 regime (Bollinger Bands)
    update_target_stock_num(context)
    # 2. Portfolio pruning: Reduce exposure to target size
    adjust_to_target_num(context)
    # 3. Portfolio deployment: Increase exposure to target size
    rebalance_if_needed(context)

def update_target_stock_num(context):
    """Calibrate target asset count based on benchmark Bollinger Regime"""
    status = get_bb_status(context)
    if status == 'up':
        new_num = g.max_stock_num
    elif status == 'down':
        new_num = g.min_stock_num
    else:
        new_num = g.base_stock_num
    
    if new_num != g.stock_num:
        log.info(f"Market Regime: {status} | Adjusting Target Capacity: {g.stock_num} -> {new_num}")
        g.stock_num = new_num

def get_bb_status(context):
    """Determine the volatility regime of the HS300 Index"""
    try:
        df = attribute_history('000300.XSHG', g.bb_period + 1, '1d', ['close'], skip_paused=True, df=True)
        if df is None or len(df) < g.bb_period + 1:
            return 'neutral'
        closes = df['close'].values
        ma = np.mean(closes[:-1])
        std = np.std(closes[:-1])
        upper_band = ma + g.bb_std_multiplier * std
        lower_band = ma - g.bb_std_multiplier * std
        current_price = closes[-1]
        if current_price > upper_band:
            return 'up'
        elif current_price < lower_band:
            return 'down'
        else:
            return 'neutral'
    except Exception as e:
        log.warn(f"Regime Detection Error: {e}")
        return 'neutral'

def adjust_to_target_num(context):
    """Prune portfolio to align with dynamic capacity constraints"""
    current_holdings = [(stock, pos) for stock, pos in context.portfolio.positions.items() if pos.total_amount > 0]
    current_count = len(current_holdings)
    if current_count <= g.stock_num:
        return
    sell_num = current_count - g.stock_num
    stock_profit = []
    for stock, pos in current_holdings:
        avg_cost = pos.avg_cost
        if avg_cost <= 0:
            profit_rate = 0
        else:
            current_price = get_current_data()[stock].last_price
            profit_rate = (current_price - avg_cost) / avg_cost
        stock_profit.append((stock, profit_rate))
    
    # Prioritize selling underperformers during downsizing
    stock_profit.sort(key=lambda x: x[1])
    to_sell = [stock for stock, _ in stock_profit[:sell_num]]
    for stock in to_sell:
        order_target_value(stock, 0)

def rebalance_if_needed(context):
    """Deployment of capital to meet target exposure capacity"""
    current_holdings = [stock for stock, pos in context.portfolio.positions.items() if pos.total_amount > 0]
    current_count = len(current_holdings)
    if current_count >= g.stock_num:
        return
    need_buy = g.stock_num - current_count
    candidates = select_best_stocks(context)
    candidates = [s for s in candidates if s not in current_holdings]
    if len(candidates) == 0:
        return
    to_buy = candidates[:need_buy]
    cash = context.portfolio.available_cash
    if cash <= 0:
        return
    per_value = cash / len(to_buy)
    for stock in to_buy:
        order_target_value(stock, per_value)

def select_best_stocks(context):
    """Core Alpha Signal: Mean Reversion + Net Inflow Filtering"""
    candidates = []
    for stock in g.stock_pool:
        current_data = get_current_data()[stock]
        if current_data.paused:
            continue
        try:
            # Factor 1: Smart Money Net Inflow (Institutional Flow)
            mf = get_money_flow(stock, count=1, end_date=context.current_dt)
            if mf is None or len(mf) == 0:
                continue
            net_main = mf['net_amount_main'].iloc[-1]
            if net_main <= 0:
                continue
        except Exception as e:
            continue
        try:
            # Factor 2: Extreme Short-term Reversion
            df = attribute_history(stock, g.lookback_days + g.drop_days + 1, 
                                   '1d', ['close'], skip_paused=True, df=True)
            if df is None or len(df) < g.lookback_days + g.drop_days:
                continue
            close = df['close'].values
            is_down_10d = close[-1] < close[-1 - g.lookback_days]
            drop_3d = (close[-1] - close[-1 - g.drop_days]) / close[-1 - g.drop_days]
            if is_down_10d and drop_3d < g.drop_threshold:
                candidates.append((stock, drop_3d))
        except Exception as e:
            continue
    
    # Rank by maximum drawdown for highest rebound potential
    candidates.sort(key=lambda x: x[1])
    result = [stock for stock, _ in candidates]
    return result

# ======================== Advanced Exit Management ========================

def check_stop_loss_take_profit(context):
    """Risk Management: OBV Divergence Exit & BBI Trend Decay Stop-Loss"""
    positions = context.portfolio.positions
    for stock in list(positions.keys()):
        position = positions[stock]
        if position.total_amount == 0:
            continue
        current_price = get_current_data()[stock].last_price
        avg_cost = position.avg_cost
        if avg_cost <= 0:
            continue
        profit_rate = (current_price - avg_cost) / avg_cost
        
        # 1. Static Profit Target (Hard TP)
        if profit_rate >= g.take_profit_pct:
            log.info(f"【Hard TP Triggered】{stock} PnL: {profit_rate:.2%}")
            order_target_value(stock, 0)
            continue
            
        # 2. OBV Divergence Exit (Early TP for Price-Volume Exhaustion)
        if profit_rate > 0.01: 
            if is_obv_stagnant(stock):
                log.info(f"【OBV Divergence Exit】{stock} Price-Volume Anomaly | Early Exit")
                order_target_value(stock, 0)
                continue

        # 3. Static Risk Limit (Hard SL)
        if profit_rate <= g.stop_loss_pct:
            log.warn(f"【Hard SL Triggered】{stock} PnL: {profit_rate:.2%}")
            order_target_value(stock, 0)
            continue
            
        # 4. BBI Dynamic Trailing Exit (Trend Reversal Protection)
        if profit_rate <= -0.03:
            if is_bbi_down(stock):
                log.warn(f"【BBI Dynamic Exit】{stock} -3% Drawdown + Negative Momentum | Liquidating")
                order_target_value(stock, 0)

# ======================== Quantitative Indicators ========================

def is_obv_stagnant(stock):
    """Logic: Price-Volume Divergence Check (OBV Peaks while Price Lags)"""
    try:
        df = attribute_history(stock, 10, '1d', ['close', 'volume'])
        if len(df) < 5: return False
        
        diff = df['close'].diff()
        direction = diff.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        obv = (direction * df['volume']).fillna(0).cumsum()
        
        # Signal: OBV makes 5-day high but Price fails to confirm
        if (obv.iloc[-1] > obv.iloc[-6:-1].max()) and (df['close'].iloc[-1] <= df['close'].iloc[-6:-1].max()):
            return True
    except:
        pass
    return False

def is_bbi_down(stock):
    """Logic: Bull/Bear Index (BBI) Slope Verification"""
    try:
        df = attribute_history(stock, 30, '1d', ['close'])
        if len(df) < 24: return False
        
        # Multi-timeframe MA cross average
        def bbi_val(d): return (d[-10:].mean() + d[-20:].mean() + d[-30:].mean() + d[-60:].mean()) / 4.0
        curr_bbi = bbi_val(df['close'].values)
        prev_bbi = bbi_val(df['close'].values[:-1])
        return curr_bbi < prev_bbi 
    except:
        pass
    return False

def after_market_close(context):
    pass