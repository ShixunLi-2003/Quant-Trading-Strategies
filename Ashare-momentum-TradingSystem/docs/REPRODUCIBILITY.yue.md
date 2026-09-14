# 重現說明

[English version](REPRODUCIBILITY.md)

## 重現層級

### 第一級：驗證公開倉庫

呢一級唔需要行情數據，用嚟驗證套件安裝、測試、公開結果完整性同圖表生成。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pytest
python scripts/generate_report_assets.py
python scripts/build_results_manifest.py
```

預期輸出包括`results/figures/`全部圖片、首頁摘要表、最終策略滾動表，同埋公開文件SHA256 manifest。

### 第二級：使用授權行情重建因子研究

準備符合`DATA_CONTRACT.md`嘅標準化日線同一分鐘行情。

```bash
python scripts/run_factor_research.py \
  --daily data/raw/daily.parquet \
  --minute data/raw/minute.parquet \
  --output results/reproduced/factors \
  --horizon 3 \
  --low-volatility-weight 0.6
```

呢一步會重建16因子面板、IC表、最終複合分數、分箱回報同診斷NAV。

### 第三級：Walk-Forward模型比較

使用第二級生成嘅因子面板。

```bash
python scripts/run_model_comparison.py \
  --panel results/reproduced/factors/factor_panel.parquet \
  --output results/reproduced/models \
  --target fwd_ret_3d \
  --train-days 120 \
  --embargo-days 3
```

腳本會生成Ridge、Random Forest同多層神經網絡嘅embargoed predictions。

### 第四級：通用交易成本回測

候選表需要包含`signal_date`、`stock_code`、`score`、`entry_price`同`exit_price`。

```bash
python scripts/run_portfolio_backtest.py \
  --candidates data/derived/candidates.parquet \
  --output results/reproduced/backtest \
  --initial-capital 30000 \
  --top-n 3
```

回測會處理有限資金、整手、最低佣金、佣金、印花稅同不利滑點。候選生成同授權分鐘價格抽取取決於數據供應商，所以冇包裝成假裝通用嘅操作。

### 第五級：ETF倉位安排

ETF表需要包含`stock_code`、`trade_date`同`close`。

```bash
python scripts/run_etf_regime_research.py \
  --prices data/raw/etf_daily.parquet \
  --output results/reproduced/etf_exposure.csv \
  --breadth-threshold 0.5 \
  --confirmation-days 2 \
  --half-after 2 \
  --cash-after 3
```

生成倉位會滯後到下一交易日。公開腳本可以重現風控機制，但唔代表可以重建所有歷史nested ETF選參結果。

## 首頁結果精確重現界線

單靠公開倉庫無法由原始輸入重新生成首頁全部回報序列。精確重現仍然需要：

- 受授權限制嘅日線、分鐘同ETF歷史行情；
- 各個歷史實驗使用嘅日期化股票池；
- 原本供應商特定嘅分鐘數據抽取同復權設定；
- 歷史候選生成同nested selection輸入狀態。

倉庫內聚合表係用嚟重新生成公開圖表嘅研究證據快照，全部記錄喺`results/manifest.csv`。呢個界線係刻意設計：方法同公開產物可以重現，但唔會重新分發受授權數據或者私人執行狀態。

## 數據來源核對表

比較重建結果之前，需要記錄：

1. 數據供應商同抽取時間；
2. 公司行動同復權方式；
3. 交易所時區同分鐘bar時間定義；
4. 交易日曆版本；
5. point-in-time股票池來源同生效日期；
6. 停牌、漲跌停同缺失分鐘處理；
7. 費用、稅項、滑點同整手假設；
8. 代碼版本同設定檔hash。

以上任何項目唔同，都可能令重建結果同公開數字有合理差異。
