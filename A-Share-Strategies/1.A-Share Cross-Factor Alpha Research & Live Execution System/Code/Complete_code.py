"""
PROJECT: A-Share Cross-Factor Alpha Research & Live Execution System (QMT Integrated)
DESCRIPTION:
- Composite alpha model blending technical (momentum, volatility, volume ratio, RSI, breakout) and
  fundamental (TTM PE, forecast growth, gross margin, debt ratio, market cap) factors with dynamic
  regime-based weight adjustments.
- Industry rotation overlay: sector boom checks via futures/ETF proxies and regional bonus scoring.
- Execution: real-time order forwarding to cloud QMT through HTTP bridge.
- Risk management: multi-tier stop-loss/take-profit, portfolio drawdown control, and pre-trade
  filters for ST, suspension, excessive returns, and earnings decline.

CODE MAP:
- Lines 1-26   : QMT Signal Execution Bridge
- Lines 28-140 : Global Configuration, Hyperparameters & Backtest Setup
- Lines 142-190: Pre-Market & Stop-Loss/Take-Profit Logic
- Lines 192-211: Intraday Scheduling & After-Market Summaries
- Lines 213-230: Portfolio Drawdown Control & Position Reduction
- Lines 232-261: Dynamic Regime Adaptation & Benchmark Estimation
- Lines 263-335: Rebalancing Core & Composite Score Aggregation
- Lines 337-425: Stock Eligibility Filters & Boom Check
- Lines 427-472: TTM PE & Expected Growth Calculation
- Lines 474-568: Technical Alpha Factors
- Lines 570-714: Fundamental Alpha Factors
- Lines 716-823: Scoring Utilities, Industry & Region Bonus, Financial Data Helpers
- Lines 825-867: Order Generation & Position Adjustment
- Lines 869-End: ST Detection, Profit TTM Growth & Stock Rise Filters
"""
import jqdata
# ====================== Trade Execution Gateway (QMT Cloud Adapter) ======================
import requests

def send_trade_signal(security, is_buy, amount, price):
    """
    Transmit order instructions to the QMT cloud execution engine.
    Converts JoinQuant security codes to QMT-compatible formats (XSHE->SZ, XSHG->SH).
    Order types: 23=Buy, 24=Sell.
    """
    url = "http://<YOUR_CLOUD_HOST_IP>:8080/order"
    order_type = 23 if is_buy else 24
    stock_code = security.replace('.XSHE', '.SZ').replace('.XSHG', '.SH')

    payload = {
        "stock_code": stock_code,
        "price": float(price),
        "quantity": int(abs(amount)),
        "order_type": order_type
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        log.info(f"[QMT] Signal sent | {stock_code} | {'BUY' if is_buy else 'SELL'} | Qty:{int(abs(amount))} | Px:{float(price):.2f} | Resp:{resp.json()}")
    except Exception as e:
        log.error(f"[QMT] Signal failed | {stock_code} | Error: {str(e)}")
# ========================================================================================

import numpy as np
import pandas as pd
from jqdata import *
from datetime import timedelta, datetime

def initialize(context):
    log.info("=== Strategy Initialization ===")
    set_params(context)
    set_backtest(context)
    log.info("=== Initialization Complete ===")

    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    run_daily(market_open_rebalance, time='09:30', reference_security='000300.XSHG')
    run_daily(market_open_stop_loss, time='11:25', reference_security='000300.XSHG')
    run_daily(market_open_stop_loss, time='14:50', reference_security='000300.XSHG')
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')

def set_params(context):
    # --- Risk Management ---
    g.enable_boom_check = True
    g.boom_check_period = 20
    g.boom_pass_threshold = 0

    g.stop_loss_threshold_1 = 0.05
    g.stop_loss_threshold_2 = 0.07

    g.max_drawdown_threshold = 0.06
    g.max_drawdown_reduce_ratio = 0.7
    g.max_drawdown_trigger_multiplier = 1.2

    # --- Scoring System ---
    g.scoring_system = {
        'technical': {
            'momentum':     {'weight': 8,  'optimal_range': (0.05, 0.15)},
            'volatility':   {'weight': 10, 'optimal_range': (0.10, 0.20)},
            'volume_ratio': {'weight': 7,  'optimal_range': (1.0, 1.5)},
            'rsi':          {'weight': 7,  'optimal_range': (40, 60)},
            'breakout':     {'weight': 8,  'threshold': 0.03}
        },
        'fundamental': {
            'pe_ratio':                  {'weight': 12, 'optimal_range': (15, 20), 'max_threshold': 30},
            'expected_growth':            {'weight': 10, 'optimal_range': (0.30, 1.0), 'min_threshold': 0.05},
            'net_profit_expected_growth': {'weight': 10, 'optimal_range': (0.30, 1.0), 'min_threshold': 0.05},
            'gross_margin':               {'weight': 10, 'optimal_range': (0.30, 0.50), 'min_threshold': 0.10},
            'debt_ratio':                 {'weight': 8,  'optimal_range': (0.20, 0.30), 'max_threshold': 0.60},
            'market_cap':                 {'weight': 10, 'optimal_range': (200, 500), 'acceptable_range': (100, 1000)}
        }
    }

    # --- Industry Classification & Sentiment Mapping ---
    g.industry_system = {
        'growth_industries': ['锂电池', '新能源', '光伏', '芯片', '半导体', '算力', '人工智能', '云计算', '生物医药', '创新药', '光模块', '铜'],
        'value_industries': ['银行', '保险', '证券', '煤炭', '钢铁', '有色金属', '建筑材料'],
        'cyclical_industries': ['化工', '机械', '汽车', '家电', '消费电子', '食品饮料'],
        'avoid_industries': ['地产', '旅游', '农业'],
        'region_bonus': {'新疆': 5},
        'bonus_scores': {'growth': 8, 'value': 3, 'cyclical': 5}
    }

    g.industry_boom_map = {
        '煤炭': 'JM', '化工': 'MA', '钢铁': 'RB', '有色': 'CU', '铜': 'CU', '铝': 'AL',
        '原油': 'SC', '石油石化': 'SC',
        '人工智能': '801750.XSHG', '算力': '801750.XSHG', '芯片': '801080.XSHG', '半导体': '801080.XSHG',
        '新能源': '801730.XSHG', '光伏': '801730.XSHG', '锂电池': '801730.XSHG',
        '创新药': '801150.XSHG', '生物医药': '801150.XSHG'
    }

    # --- Portfolio Parameters ---
    g.stock_num = 5
    g.rebalance_days = 10
    g.max_position_per_stock = 0.20
    g.max_drawdown_control = True

    g.period = {
        'momentum': 20,
        'volatility': 20,
        'volume_ratio': [5, 20],
        'rsi': 14,
        'breakout': 10
    }

    g.dynamic_weight = {
        'market_status': 'normal',
        'tech_weight_multiplier': 1.0,
        'fundamental_weight_multiplier': 1.0
    }

    # --- Cache & Flags ---
    g.industry_cache = {}
    g.price_cache = {}
    g.region_cache = {}
    g.debug = False
    g.last_portfolio_value = None

    # --- Enhanced Filters (Price Momentum & Earnings Quality) ---
    g.enable_rise_filter = True
    g.short_rise_period = 120
    g.short_rise_threshold = 1.5
    g.long_rise_period = 720
    g.long_rise_threshold = 4.0

    g.enable_profit_drop_filter = True
    g.profit_drop_threshold = -0.5

def set_backtest(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_slippage(FixedSlippage(0.002))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001,
                             open_commission=0.0003, close_commission=0.0003,
                             min_commission=5), type='stock')
    g.days = 0
    g.portfolio_high = context.portfolio.total_value

def before_market_open(context):
    current_value = context.portfolio.total_value
    if current_value > g.portfolio_high:
        g.portfolio_high = current_value

def stop_loss_check(context):
    """Individual position stop-loss / take-profit evaluation."""
    positions = context.portfolio.positions
    if not positions:
        return

    for stock, pos in positions.items():
        try:
            cur_data = get_current_data()[stock]
            if cur_data.paused:
                continue

            avg_cost = pos.avg_cost
            cur_price = cur_data.last_price
            if avg_cost <= 0:
                continue

            pnl = (cur_price - avg_cost) / avg_cost

            # Take-profit logic
            if 0.20 <= pnl < 0.30:
                target_amt = int(pos.total_amount * 0.5)
                if target_amt >= 100:
                    log.info(f"Take-profit 50%: {stock} | PnL:{pnl:.2%}")
                    order_target(stock, target_amt)
                    send_trade_signal(stock, False, pos.total_amount - target_amt, cur_price)
            elif pnl >= 0.30:
                log.info(f"Take-profit 100%: {stock} | PnL:{pnl:.2%}")
                order_target_value(stock, 0)
                send_trade_signal(stock, False, pos.total_amount, cur_price)
            # Stop-loss logic
            elif -g.stop_loss_threshold_1 >= pnl > -g.stop_loss_threshold_2:
                target_amt = int(pos.total_amount * 0.5)
                if target_amt >= 100:
                    log.warn(f"Stop-loss 50%: {stock} | PnL:{pnl:.2%}")
                    order_target(stock, target_amt)
                    send_trade_signal(stock, False, pos.total_amount - target_amt, cur_price)
            elif pnl <= -g.stop_loss_threshold_2:
                log.warn(f"Stop-loss 100%: {stock} | PnL:{pnl:.2%}")
                order_target_value(stock, 0)
                send_trade_signal(stock, False, pos.total_amount, cur_price)

        except Exception as e:
            log.warn(f"Stop-loss check error {stock}: {str(e)}")

def market_open_rebalance(context):
    g.days += 1

    if g.max_drawdown_control:
        check_max_drawdown(context)

    adjust_dynamic_weights(context)

    if g.days % g.rebalance_days == 1:
        rebalance_portfolio(context)

def market_open_stop_loss(context):
    stop_loss_check(context)

def after_market_close(context):
    if g.last_portfolio_value and g.last_portfolio_value > 0:
        daily_ret = (context.portfolio.total_value - g.last_portfolio_value) / g.last_portfolio_value
        log.info(f"Daily return: {daily_ret:.4%} | Portfolio value: {context.portfolio.total_value:.2f}")

    g.last_portfolio_value = context.portfolio.total_value

def check_max_drawdown(context):
    current_value = context.portfolio.total_value
    dd = (g.portfolio_high - current_value) / g.portfolio_high

    if dd > g.max_drawdown_threshold:
        log.warn(f"Max drawdown {dd:.2%} exceeded threshold {g.max_drawdown_threshold:.2%}")
        if dd > g.max_drawdown_threshold * g.max_drawdown_trigger_multiplier:
            reduce_positions(context, g.max_drawdown_reduce_ratio)

def reduce_positions(context, ratio=0.5):
    for stock, pos in context.portfolio.positions.items():
        target_amt = int(pos.total_amount * (1 - ratio))
        if target_amt >= 100:
            order_target(stock, target_amt)
            log.info(f"Risk reduction: {stock} | ratio {ratio:.0%} | target {target_amt}")
        elif target_amt == 0:
            order_target_value(stock, 0)
            log.info(f"Risk liquidation: {stock}")

def adjust_dynamic_weights(context):
    bench_ret = get_benchmark_returns(context)

    if bench_ret > 0.05:
        g.dynamic_weight['market_status'] = 'bull'
        g.dynamic_weight['tech_weight_multiplier'] = 1.2
        g.dynamic_weight['fundamental_weight_multiplier'] = 0.9
        g.rebalance_days = 10
    elif bench_ret < -0.05:
        g.dynamic_weight['market_status'] = 'bear'
        g.dynamic_weight['tech_weight_multiplier'] = 0.8
        g.dynamic_weight['fundamental_weight_multiplier'] = 1.2
        g.rebalance_days = 15
    else:
        g.dynamic_weight['market_status'] = 'normal'
        g.dynamic_weight['tech_weight_multiplier'] = 1.0
        g.dynamic_weight['fundamental_weight_multiplier'] = 1.0
        g.rebalance_days = 10

def get_benchmark_returns(context, days=20):
    end_date = context.current_dt
    start_date = end_date - timedelta(days=days + 10)
    try:
        prices = get_price('000300.XSHG', start_date=start_date, end_date=end_date,
                           frequency='daily', fields=['close'])
        if len(prices) >= days:
            return (prices['close'].iloc[-1] - prices['close'].iloc[-days]) / prices['close'].iloc[-days]
    except:
        pass
    return 0

def rebalance_portfolio(context):
    try:
        stock_list = get_index_stocks('000300.XSHG', date=context.current_dt)
        if not stock_list:
            log.error("Empty stock universe.")
            return

        tradable = [s for s in stock_list if check_stock_eligibility(s, context)]
        if not tradable:
            log.warn("No tradable stocks.")
            return

        scored = calculate_comprehensive_scores(context, tradable)
        if scored.empty:
            log.warn("No valid scores.")
            return

        selected = select_top_stocks_with_boom_check(context, scored)
        log.info(f"Selected {len(selected)} stocks for rebalance: {selected}")

        adjust_positions(context, selected)
    except Exception as e:
        log.error(f"Rebalance failed: {str(e)}")
        import traceback
        log.error(traceback.format_exc())

def calculate_comprehensive_scores(context, stock_list):
    records = []
    for stock in stock_list:
        try:
            if not check_stock_eligibility(stock, context):
                continue

            total = 0
            detail = {}

            tech = calculate_technical_scores(context, stock)
            if tech:
                tech_sum = sum(v for v in tech.values() if isinstance(v, (int, float)))
                tech_sum *= g.dynamic_weight['tech_weight_multiplier']
                total += tech_sum
                detail.update(tech)
                detail['technical_total'] = tech_sum
            else:
                detail['technical_total'] = 0

            fund = calculate_fundamental_scores(context, stock)
            if fund:
                fund_sum = sum(v for v in fund.values() if isinstance(v, (int, float)))
                fund_sum *= g.dynamic_weight['fundamental_weight_multiplier']
                total += fund_sum
                detail.update(fund)
                detail['fundamental_total'] = fund_sum
            else:
                detail['fundamental_total'] = 0

            ind_score = calculate_enhanced_industry_score(stock, context)
            reg_score = calculate_region_score(stock, context)
            total += ind_score + reg_score
            detail['industry_bonus'] = ind_score
            detail['region_bonus'] = reg_score

            detail['stock'] = stock
            detail['total_score'] = total
            records.append(detail)
        except Exception as e:
            log.warn(f"Score error {stock}: {str(e)}")

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).set_index('stock')
    return df.sort_values('total_score', ascending=False)

def check_stock_eligibility(stock, context):
    try:
        cur_data = get_current_data()[stock]
        if cur_data.paused or is_st_stock(stock) or cur_data.last_price <= 0:
            return False

        # Filter: excessive short/long-term returns
        if g.enable_rise_filter:
            short_rise = calculate_stock_rise(stock, context, g.short_rise_period)
            if short_rise >= g.short_rise_threshold:
                return False
            long_rise = calculate_stock_rise(stock, context, g.long_rise_period)
            if long_rise >= g.long_rise_threshold:
                return False

        # Filter: TTM profit drop
        if g.enable_profit_drop_filter:
            profit_growth = calculate_profit_ttm_growth(stock, context)
            if profit_growth <= g.profit_drop_threshold:
                return False

        return True
    except:
        return False

def check_single_stock_boom(stock, context):
    if not g.enable_boom_check:
        return True

    try:
        # Cache industry info
        if stock not in g.industry_cache:
            g.industry_cache[stock] = get_industry(stock, date=context.current_dt)
        industry_data = g.industry_cache[stock]

        industry_name = ""
        if industry_data:
            for _, info in industry_data.items():
                if isinstance(info, dict) and 'industry_name' in info:
                    industry_name = info['industry_name']
                    break

        # Map to boom proxy
        target_symbol = None
        for key, sym in g.industry_boom_map.items():
            if key in industry_name:
                target_symbol = sym
                break

        if not target_symbol:
            return True

        if len(target_symbol) <= 3:
            dom = get_dominant_future(target_symbol)
            if not dom:
                return True
            check_symbol = dom
        else:
            check_symbol = target_symbol

        end_date = context.current_dt
        start_date = end_date - timedelta(days=g.boom_check_period + 10)
        df = get_price(check_symbol, start_date=start_date, end_date=end_date,
                       frequency='daily', fields=['close'])
        if len(df) < g.boom_check_period:
            return True

        momentum = (df['close'].iloc[-1] - df['close'].iloc[-g.boom_check_period]) / df['close'].iloc[-g.boom_check_period]
        return momentum >= g.boom_pass_threshold

    except Exception as e:
        log.warn(f"Boom check error {stock}: {str(e)}")
        return True

def select_top_stocks_with_boom_check(context, scored_stocks):
    selected = []
    for stock in scored_stocks.index:
        if len(selected) >= g.stock_num:
            break
        if check_stock_eligibility(stock, context) and check_single_stock_boom(stock, context):
            selected.append(stock)

    if len(selected) < g.stock_num:
        log.warn(f"Insufficient qualified stocks, using top {g.stock_num}")
        supplement = scored_stocks.head(g.stock_num).index.tolist()
        for s in supplement:
            if s not in selected and len(selected) < g.stock_num:
                selected.append(s)
    return selected

def calculate_ttm_pe(stock, context):
    try:
        q = query(income.code, income.net_profit, income.report_type).filter(
            income.code == stock
        ).order_by(income.statDate.desc()).limit(4)
        df = get_fundamentals(q, date=context.current_dt)
        if len(df) < 4:
            return None
        ttm_profit = df['net_profit'].sum()
        if ttm_profit <= 0:
            return None

        q_val = query(valuation.market_cap).filter(valuation.code == stock)
        df_val = get_fundamentals(q_val, date=context.current_dt)
        if df_val.empty:
            return None

        mkt_cap = df_val['market_cap'][0] * 100000000
        return mkt_cap / ttm_profit
    except:
        return None

def calculate_expected_growth(stock, context):
    try:
        q = query(income.net_profit).filter(income.code == stock).order_by(income.statDate.desc()).limit(4)
        df = get_fundamentals(q, date=context.current_dt)
        if len(df) < 4:
            return 0.08
        ttm = df['net_profit'].sum()
        if ttm <= 0:
            return 0.08

        q_fc = query(forecast.code, forecast.forecast_net_profit, forecast.forecast_year).filter(
            forecast.code == stock,
            forecast.forecast_type == 1,
            forecast.pub_date < context.current_dt
        ).order_by(forecast.pub_date.desc()).limit(2)
        df_fc = get_fundamentals(q_fc, date=context.current_dt)
        if df_fc.empty:
            return 0.08

        expected = df_fc['forecast_net_profit'].iloc[0]
        growth = (expected - ttm) / abs(ttm)
        return max(min(growth, 1.0), -0.5)
    except:
        return 0.08

def calculate_technical_scores(context, stock):
    end_date = context.current_dt
    max_window = max(g.period['momentum'], g.period['volatility'],
                     max(g.period['volume_ratio']), g.period['rsi'], g.period['breakout'])
    start_date = end_date - timedelta(days=max_window + 30)

    try:
        prices = get_price(stock, start_date=start_date, end_date=end_date,
                           frequency='daily', fields=['close', 'high', 'low', 'volume'],
                           skip_paused=True, fq='pre')
        if prices is None or len(prices) < max_window:
            return None

        close = prices['close']
        high = prices['high']
        low = prices['low']
        volume = prices['volume']
        scores = {}

        tech_cfg = g.scoring_system['technical']

        # Momentum
        if 'momentum' in tech_cfg:
            try:
                mom = (close.iloc[-1] / close.iloc[-g.period['momentum']] - 1)
                scores['momentum_score'] = calculate_range_score(mom, tech_cfg['momentum']['optimal_range'],
                                                                  tech_cfg['momentum']['weight'])
            except:
                scores['momentum_score'] = 0

        # Volatility
        if 'volatility' in tech_cfg:
            try:
                rets = np.log(close / close.shift(1)).dropna()
                if len(rets) >= g.period['volatility']:
                    vol = rets.rolling(g.period['volatility']).std().iloc[-1]
                    if not np.isnan(vol):
                        scores['volatility_score'] = calculate_range_score(vol, tech_cfg['volatility']['optimal_range'],
                                                                           tech_cfg['volatility']['weight'], reverse=True)
                    else:
                        scores['volatility_score'] = 0
                else:
                    scores['volatility_score'] = 0
            except:
                scores['volatility_score'] = 0

        # Volume ratio
        if 'volume_ratio' in tech_cfg:
            try:
                sp, lp = g.period['volume_ratio']
                if len(volume) >= lp:
                    vol_ratio = (volume.rolling(sp).mean().iloc[-1] / volume.rolling(lp).mean().iloc[-1]) \
                                if volume.rolling(lp).mean().iloc[-1] != 0 else 1
                    scores['volume_ratio_score'] = calculate_range_score(vol_ratio, tech_cfg['volume_ratio']['optimal_range'],
                                                                         tech_cfg['volume_ratio']['weight'])
                else:
                    scores['volume_ratio_score'] = 0
            except:
                scores['volume_ratio_score'] = 0

        # RSI
        if 'rsi' in tech_cfg:
            try:
                if len(close) >= g.period['rsi']:
                    delta = close.diff()
                    gain = delta.where(delta > 0, 0).rolling(g.period['rsi']).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(g.period['rsi']).mean()
                    rs = gain / loss
                    rsi_val = 100 - (100 / (1 + rs))
                    if not np.isnan(rsi_val):
                        scores['rsi_score'] = calculate_range_score(rsi_val, tech_cfg['rsi']['optimal_range'],
                                                                     tech_cfg['rsi']['weight'])
                    else:
                        scores['rsi_score'] = 0
                else:
                    scores['rsi_score'] = 0
            except:
                scores['rsi_score'] = 0

        # Breakout
        if 'breakout' in tech_cfg:
            try:
                if len(close) >= g.period['breakout']:
                    recent_high = high.rolling(g.period['breakout']).max().iloc[-2]
                    breakout = (close.iloc[-1] - recent_high) / recent_high
                    scores['breakout_score'] = tech_cfg['breakout']['weight'] if breakout >= tech_cfg['breakout']['threshold'] else 0
                else:
                    scores['breakout_score'] = 0
            except:
                scores['breakout_score'] = 0

        return scores
    except Exception as e:
        log.warn(f"Tech score error {stock}: {str(e)}")
        return None

def calculate_fundamental_scores(context, stock):
    try:
        scores = {}
        fp = g.scoring_system['fundamental']

        # PE
        if 'pe_ratio' in fp:
            try:
                pe = calculate_ttm_pe(stock, context)
                if not pe:
                    df_v = get_fundamentals(query(valuation.pe_ratio).filter(valuation.code == stock), date=context.current_dt)
                    pe = df_v['pe_ratio'][0] if not df_v.empty else None
                if pe and pe > 0:
                    w = fp['pe_ratio']['weight']
                    if pe <= fp['pe_ratio']['optimal_range'][0]:
                        scores['pe_ratio_score'] = w
                    elif pe <= fp['pe_ratio']['optimal_range'][1]:
                        scores['pe_ratio_score'] = w
                    elif pe <= 25:
                        scores['pe_ratio_score'] = w * 0.8
                    elif pe <= 30:
                        scores['pe_ratio_score'] = w * 0.6
                    elif pe <= 40:
                        scores['pe_ratio_score'] = w * 0.3
                    else:
                        scores['pe_ratio_score'] = 0
                else:
                    scores['pe_ratio_score'] = 0
            except:
                scores['pe_ratio_score'] = 0

        # Expected growth
        def growth_score(metric_key, growth_val):
            w = fp[metric_key]['weight']
            min_t = fp[metric_key]['min_threshold']
            opt = fp[metric_key]['optimal_range']
            if growth_val < min_t:
                if growth_val < 0:
                    return max(w * (growth_val / min_t), -5)
                else:
                    return w * 0.5 * (growth_val / min_t)
            elif growth_val >= opt[0]:
                return w
            elif growth_val >= 0.10:
                ratio = (growth_val - 0.10) / (0.30 - 0.10)
                return w * (0.5 + 0.5 * ratio)
            elif growth_val >= 0.05:
                ratio = (growth_val - 0.05) / (0.10 - 0.05)
                return w * 0.5 * ratio
            return 0

        if 'expected_growth' in fp:
            try:
                g_val = calculate_expected_growth(stock, context)
                if g_val is not None:
                    scores['expected_growth_score'] = growth_score('expected_growth', g_val)
                else:
                    scores['expected_growth_score'] = 0
            except:
                scores['expected_growth_score'] = 0

        if 'net_profit_expected_growth' in fp:
            try:
                npg = calculate_expected_growth(stock, context)
                if npg is not None:
                    scores['net_profit_expected_growth_score'] = growth_score('net_profit_expected_growth', npg)
                else:
                    scores['net_profit_expected_growth_score'] = 0
            except:
                scores['net_profit_expected_growth_score'] = 0

        fin_data = get_enhanced_financial_data(stock, context)
        if not fin_data:
            return scores if scores else None

        # Gross margin
        if 'gross_margin' in fp:
            try:
                gm = fin_data.get('gross_margin')
                if gm is not None:
                    w = fp['gross_margin']['weight']
                    min_t = fp['gross_margin']['min_threshold']
                    opt = fp['gross_margin']['optimal_range']
                    if gm < min_t:
                        scores['gross_margin_score'] = 0
                    elif gm >= opt[0]:
                        scores['gross_margin_score'] = w
                    elif gm >= 0.20:
                        ratio = (gm - 0.20) / (0.30 - 0.20)
                        scores['gross_margin_score'] = w * (0.5 + 0.5 * ratio)
                    elif gm >= 0.10:
                        ratio = (gm - 0.10) / (0.20 - 0.10)
                        scores['gross_margin_score'] = w * 0.5 * ratio
                    else:
                        scores['gross_margin_score'] = 0
                else:
                    scores['gross_margin_score'] = 0
            except:
                scores['gross_margin_score'] = 0

        # Debt ratio
        if 'debt_ratio' in fp:
            try:
                dr = fin_data.get('debt_ratio')
                if dr is not None:
                    w = fp['debt_ratio']['weight']
                    opt = fp['debt_ratio']['optimal_range']
                    if dr <= opt[1]:
                        scores['debt_ratio_score'] = w
                    elif dr <= 0.60:
                        ratio = 1 - (dr - opt[1]) / (0.60 - opt[1])
                        scores['debt_ratio_score'] = w * (0.5 + 0.5 * ratio)
                    elif dr <= 0.70:
                        ratio = 1 - (dr - 0.60) / (0.70 - 0.60)
                        scores['debt_ratio_score'] = w * 0.5 * ratio
                    else:
                        scores['debt_ratio_score'] = 0
                else:
                    scores['debt_ratio_score'] = 0
            except:
                scores['debt_ratio_score'] = 0

        # Market cap
        if 'market_cap' in fp:
            try:
                mcap = fin_data.get('market_cap')
                if mcap is not None:
                    w = fp['market_cap']['weight']
                    opt = fp['market_cap']['optimal_range']
                    acc = fp['market_cap']['acceptable_range']
                    if opt[0] <= mcap <= opt[1]:
                        scores['market_cap_score'] = w
                    elif (acc[0] <= mcap < opt[0]) or (opt[1] < mcap <= acc[1]):
                        scores['market_cap_score'] = w * 0.5
                    else:
                        scores['market_cap_score'] = 0
                else:
                    scores['market_cap_score'] = 0
            except:
                scores['market_cap_score'] = 0

        return scores
    except Exception as e:
        log.warn(f"Fundamental score error {stock}: {str(e)}")
        return None

def calculate_range_score(value, optimal_range, max_score, reverse=False):
    try:
        low, high = optimal_range
        if reverse:
            if value <= low:
                return max_score
            if value >= high:
                return max_score * 0.1
            return max_score * (1 - (value - low) / (high - low))
        else:
            if low <= value <= high:
                return max_score
            if value < low:
                return max_score * (value / low) if low > 0 else max_score * 0.3
            return max_score * (high / value) if value > 0 else max_score * 0.3
    except:
        return max_score * 0.5

def calculate_enhanced_industry_score(stock, context):
    try:
        if stock not in g.industry_cache:
            g.industry_cache[stock] = get_industry(stock, date=context.current_dt)
        industry_data = g.industry_cache[stock]
        if not industry_data:
            return 0

        industry_name = ""
        for info in industry_data.values():
            if isinstance(info, dict) and 'industry_name' in info:
                industry_name = info['industry_name']
                break
        if not industry_name:
            return 0

        for avoid in g.industry_system['avoid_industries']:
            if avoid in industry_name:
                return -5

        mkt = g.dynamic_weight['market_status']
        for ind in g.industry_system['growth_industries']:
            if ind in industry_name:
                bonus = g.industry_system['bonus_scores']['growth']
                if mkt == 'bull':
                    bonus *= 1.2
                elif mkt == 'bear':
                    bonus *= 0.8
                return bonus
        for ind in g.industry_system['value_industries']:
            if ind in industry_name:
                bonus = g.industry_system['bonus_scores']['value']
                if mkt == 'bear':
                    bonus *= 1.2
                elif mkt == 'bull':
                    bonus *= 0.9
                return bonus
        for ind in g.industry_system['cyclical_industries']:
            if ind in industry_name:
                return g.industry_system['bonus_scores']['cyclical']
        return 0
    except:
        return 0

def calculate_region_score(stock, context):
    try:
        if stock not in g.region_cache:
            info = get_security_info(stock)
            g.region_cache[stock] = info.name if info and hasattr(info, 'name') else ""
        name = g.region_cache[stock]
        for region, bonus in g.industry_system['region_bonus'].items():
            if region in name:
                return bonus
        return 0
    except:
        return 0

def get_enhanced_financial_data(stock, context):
    try:
        qv = query(valuation.code, valuation.market_cap).filter(valuation.code == stock)
        dfv = get_fundamentals(qv, date=context.current_dt)
        if dfv.empty:
            return None
        mcap = dfv['market_cap'][0] / 100000000

        yr = context.current_dt.year - 1 if context.current_dt.month < 5 else context.current_dt.year
        qi = query(income.code, income.operating_revenue, income.operating_cost, income.net_profit).filter(income.code == stock)
        dfi = get_fundamentals(qi, statDate=str(yr))
        if dfi.empty:
            dfi = get_fundamentals(qi)
            if dfi.empty:
                return None

        rev = dfi['operating_revenue'][0]
        cost = dfi['operating_cost'][0]
        gm = (rev - cost) / rev if rev > 0 else 0

        qb = query(balance.code, balance.total_liability, balance.total_assets).filter(balance.code == stock)
        dfb = get_fundamentals(qb, statDate=str(yr))
        if dfb.empty:
            dr = 0.5
        else:
            ta = dfb['total_assets'][0]
            tl = dfb['total_liability'][0]
            dr = tl / ta if ta > 0 else 0.5

        return {'gross_margin': gm, 'debt_ratio': dr, 'market_cap': mcap}
    except Exception as e:
        log.warn(f"Financial data error {stock}: {str(e)}")
        return None

def adjust_positions(context, selected_stocks):
    if not selected_stocks:
        return

    current_pos = context.portfolio.positions
    to_sell = [s for s in current_pos if s not in selected_stocks]
    for s in to_sell:
        order_target_value(s, 0)
        send_trade_signal(s, False, current_pos[s].total_amount, get_current_data()[s].last_price)

    total_val = context.portfolio.total_value
    target_val = min(total_val / len(selected_stocks), total_val * g.max_position_per_stock)

    for s in selected_stocks:
        try:
            if not check_stock_eligibility(s, context):
                continue
            px = get_current_data()[s].last_price
            if px is None or px == 0:
                continue

            min_buy = px * 100
            if target_val < min_buy:
                log.warn(f"Insufficient target value for {s}: {target_val:.2f} < {min_buy:.2f}")
                continue

            cur_val = current_pos[s].value if s in current_pos else 0
            diff = target_val - cur_val

            threshold_mul = 1.5 if g.dynamic_weight['market_status'] == 'bear' else 1.0
            if abs(diff) > min_buy * 0.1 * threshold_mul:
                if diff > 0 and diff >= min_buy:
                    order_target_value(s, target_val)
                    buy_amt = int(diff / px)
                    if buy_amt >= 100:
                        send_trade_signal(s, True, buy_amt, px)
                elif diff < 0:
                    order_target_value(s, target_val)
                    sell_amt = int(-diff / px)
                    if sell_amt >= 100:
                        send_trade_signal(s, False, sell_amt, px)
        except Exception as e:
            log.warn(f"Adjust error {s}: {str(e)}")

def is_st_stock(stock):
    try:
        name = get_security_info(stock).display_name
        return 'ST' in name or '*ST' in name or 'PT' in name
    except:
        return False

def calculate_profit_ttm_growth(stock, context):
    try:
        q_cur = query(income.code, income.net_profit, income.statDate).filter(
            income.code == stock).order_by(income.statDate.desc()).limit(4)
        df_cur = get_fundamentals(q_cur, date=context.current_dt)
        if len(df_cur) < 4:
            return 0
        cur_ttm = df_cur['net_profit'].sum()

        last_yr = context.current_dt - timedelta(days=365)
        q_last = query(income.code, income.net_profit, income.statDate).filter(
            income.code == stock).order_by(income.statDate.desc()).limit(4)
        df_last = get_fundamentals(q_last, date=last_yr)
        if len(df_last) < 4:
            return 0
        last_ttm = df_last['net_profit'].sum()

        if last_ttm <= 0:
            return -1.0
        return (cur_ttm - last_ttm) / abs(last_ttm)
    except:
        return 0

def calculate_stock_rise(stock, context, period):
    try:
        end_date = context.current_dt
        start_date = end_date - timedelta(days=period + 10)
        df = get_price(stock, start_date=start_date, end_date=end_date,
                       frequency='daily', fields=['close'], skip_paused=True, fq='pre')
        if len(df) < period:
            return 0
        return (df['close'].iloc[-1] - df['close'].iloc[-period]) / df['close'].iloc[-period]
    except:
        return 0