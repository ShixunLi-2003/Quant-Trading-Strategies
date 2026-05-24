# Reliability And Reusability Memo

This note documents why the current crypto strategy framework is credible as a research platform, what controls are already implemented, and how the same engine can be reused for new factor, timing, and portfolio-construction ideas.

It is written as a research reliability memo, not as a marketing promise. The right standard is not "can any backtest look good," but "does the process reduce common sources of false discovery and make the strategy easier to audit, extend, and challenge."

## Executive Summary

The framework is reliable for research use because it combines:

- point-in-time market data processing from exchange-native raw files
- modular factor definitions separated from portfolio construction
- explicit liquidity and tradeability filters
- cross-sectional ranking with transparent long/short selection rules
- execution-aware simulation with fees, funding, lot-size constraints, and liquidation checks
- independent evidence layers through factor analysis, backtest performance, and attribution analysis

The framework is reusable because:

- new factors can be added as standalone modules
- selection and filter rules are configuration-driven
- the pipeline structure remains stable across strategies
- the same engine can support pure long, long/short, and timing-overlay experiments

## 1. Data Reliability

### 1.1 Source integrity

The current research package is based on directly collected cryptocurrency market data. In practice, this means the strategy is built from exchange-originated time series rather than from manually edited spreadsheets or opaque derived datasets.

In the current codebase:

- spot and perpetual datasets are loaded independently
- the engine supports funding-rate-aware perpetual simulation
- minimum tradable quantity metadata is refreshed from the exchange interface

This matters because crypto strategies are unusually sensitive to market-structure details, especially when perpetual contracts and spot instruments are mixed.

### 1.2 Standardized preprocessing

The data-preparation layer improves reliability by enforcing a standard bar structure before factors are computed:

- duplicate timestamps are removed
- missing hourly bars are reintroduced through a full hourly timestamp range
- `close` is forward-filled when gaps occur
- `open` is imputed from `close` when required
- volume-related fields are zero-filled when no trading occurs
- funding rates are aligned at the bar level

This reduces accidental distortions caused by irregular symbol histories or inconsistent raw exports.

### 1.3 Symbol-level eligibility control

The framework does not blindly treat every symbol as tradable research input. Reliability is improved through:

- stable-symbol exclusion
- blacklist support
- minimum history requirement through `min_kline_num`
- `is_trading` flags to avoid ranking inactive assets

These controls reduce false positives caused by newly listed, illiquid, or inactive pairs.

## 2. Point-In-Time Discipline And Look-Ahead Control

### 2.1 Feature generation uses contemporaneous or lagged information

The factor layer is computed from each symbol's own historical candle path before cross-sectional ranking is performed. This is the core requirement for preventing blatant future leakage.

### 2.2 Forward return fields are separated from signal creation

The framework builds next-step price references for evaluation, but these are not used as factor inputs. Their role is to support return measurement and sample-end trimming rather than feature construction.

This distinction is important: a strategy can only claim research integrity if forward returns are used for evaluation after signals are formed, not during signal generation.

### 2.3 Warm-up and end-sample trimming

The engine avoids using factors before sufficient history exists:

- factors are not used until the minimum warm-up window is satisfied
- incomplete ending windows are removed when the future holding horizon is not fully observable

These controls reduce distortions near the start and end of the sample.

## 3. Factor Reliability

### 3.1 Modular factor design

Each factor is implemented independently and then loaded dynamically into the research pipeline. This creates several benefits:

- new factors can be inserted without rewriting the backtest engine
- factor logic can be audited in isolation
- failed signals do not need to be hidden or merged into a monolithic notebook

This modularity is a strong reusability signal in a quant-research setting.

### 3.2 Multiple evidence layers

The factor framework does not rely on a single metric. Reliability is assessed across:

- Pearson IC
- Spearman rank IC
- IC dispersion and IC information ratio
- Newey-West adjusted t-statistics
- monotonicity across sorted groups
- realized long/short portfolio performance
- turnover diagnostics

Using both statistical and realized-portfolio evidence is important because many apparent signals disappear once ranking, holding periods, and turnover are introduced.

### 3.3 Transparent treatment of weak factors

The factor summary retains both strong and weak candidates. This is a positive reliability feature. A research pack is more credible when it shows:

- which factors add value
- which factors are mainly useful as filters
- which candidates fail to survive portfolio testing

The current outputs do this. For example:

- `W42_(0.01, 0.99, True)` is visibly strong
- `QuoteVolumeMean_13` is more useful as a filter or conditioning variable
- some candidate factors remain weak in realized portfolio form

That transparency reduces the risk of narrative cherry-picking.

## 4. Reliability Of Long/Short Selection

### 4.1 Cross-sectional selection is explicit

The strategy does not make hidden discretionary choices at rebalance time. The selection process is explicit:

1. compute factor values
2. apply pre-selection filters
3. rank the eligible universe cross-sectionally
4. choose the top long basket and bottom short basket
5. assign equal target weights inside each side

This transparency makes the portfolio-construction logic auditable.

### 4.2 Long/short symmetry improves interpretability

In the current strategy snapshot:

- the short side count is matched to the long side count
- long and short gross allocations are scaled symmetrically
- the attribution output shows near-zero average net exposure

That design makes it easier to interpret whether the portfolio earns returns from cross-sectional dispersion rather than from an uncontrolled market beta bet.

### 4.3 Liquidity-aware filtering

The use of `QuoteVolumeMean` and `VolumeMeanRatio` as filters is an important reliability control. It reduces the chance that the strategy's edge is only coming from names that are:

- difficult to trade at scale
- sporadically quoted
- overly sensitive to isolated prints

## 5. Simulation Reliability

### 5.1 Execution is not modeled as frictionless close-to-close magic

The engine separates several phases of the rebalance path:

- open valuation
- execution pricing through the prepared execution field
- close valuation
- funding fee application for perpetuals

This is more credible than simplified backtests that assume all positions can be opened and closed at the same frictionless mark.

### 5.2 Fees and funding are explicit

The framework directly models:

- spot trading fees
- perpetual trading fees
- perpetual funding

This is essential in crypto because funding and transaction costs can materially change realized returns, especially in long/short strategies.

### 5.3 Minimum tradable quantity handling

The strategy does not assume infinitely divisible trades. Position sizing is discretized through exchange minimum quantity information. This improves implementability realism and prevents overstating performance in small or low-priced instruments.

### 5.4 Liquidation and leverage controls

The simulator includes:

- leverage handling
- margin-ratio tracking
- liquidation-threshold checks

These controls matter because many apparently attractive crypto strategies fail once realistic leverage and margin conditions are enforced.

## 6. Attribution Reliability

Attribution analysis improves reliability because it asks whether the portfolio behaves coherently after construction.

The current framework decomposes results across:

- long side vs short side
- symbol-level contribution
- month and year buckets
- rebalance offsets
- market regimes
- official vs shadow NAV reconciliation

This makes the strategy easier to audit for hidden concentration, unstable sleeves, or reporting inconsistencies.

## 7. Reusability

### 7.1 Reusable factor framework

The factor engine is reusable because a new signal only needs:

- a standalone factor definition
- parameter registration
- optional inclusion in `factor_list` or `filter_list`

The rest of the research workflow remains unchanged.

### 7.2 Reusable portfolio layer

The current engine already supports reuse across different portfolio styles:

- pure long variants
- long/short variants
- different holding periods
- different selection basket sizes
- different filter combinations
- offset-enabled or offset-disabled constructions

### 7.3 Reusable timing overlay structure

The current showcased strategy is primarily cross-sectional rather than a top-down timing strategy. That said, the framework is compatible with timing overlays because:

- filters can act as market-state gates
- offset logic can smooth entry timing
- the same backtest engine can incorporate external regime or directional exposure rules

The important point is truthfulness: the current exported strategy is mainly a selection engine, not a standalone macro timing system. Any future timing layer should be validated under the same reliability standards described here.

## 8. Why This Is Credible For An Interview

This framework is stronger than a typical "good-looking backtest" because it demonstrates:

- research decomposition instead of monolithic notebooks
- explicit factor validation rather than intuition-only claims
- implementation awareness specific to crypto market structure
- post-trade attribution rather than headline returns only
- visible weak signals alongside strong ones, which lowers selection bias risk

In other words, the research process itself is inspectable.

## 9. Current Limitations

No research framework is perfect. The current package still has limitations that should be stated clearly:

- it depends on local raw data paths rather than a fully bundled sample dataset
- it does not yet package dependencies into a formal public environment file
- survivorship control depends on the completeness of the local symbol archive
- slippage and market impact are simplified relative to full production execution
- borrow constraints, venue fragmentation, and latency effects are not the main focus of this version

These limitations do not invalidate the framework, but they define where future strengthening should happen.

## 10. Practical Reuse Checklist

When reusing this framework for a new factor or strategy idea, the minimum professional checklist should be:

1. verify the raw exchange archive is complete enough for the target sample
2. confirm factor logic uses only point-in-time available information
3. evaluate the signal with IC, monotonicity, and realized portfolio metrics
4. test turnover, fee drag, and funding sensitivity
5. inspect long-side and short-side attribution separately
6. inspect whether the edge survives multiple offsets and subperiods
7. document negative findings, not only the winning configuration

## Conclusion

The strongest claim supported by this repository is not "this strategy must work live forever." The stronger and more defensible claim is:

> this is a disciplined, modular, execution-aware crypto research framework with enough statistical, construction, and attribution controls to make its findings meaningful and reusable.

That is exactly the kind of claim that tends to hold up better in a serious quant interview.
