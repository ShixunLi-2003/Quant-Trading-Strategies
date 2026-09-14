# 研究結果

[English version](README.md)

`figures/`包含完整研究流程圖、因子IC、HAC穩健性、非重疊五分位分箱、嚴格回測資金曲線、滾動窗口、分鐘賣出時間敏感度、模型留出樣本比較、ETF連續樣本外結果同基準比較。

## 核心表格

| 文件 | 用途 |
|---|---|
| `public_headline_metrics.csv` | 首頁核心結果摘要 |
| `factor_ic_robustness.csv` | 全樣本、開發期同留出期IC及HAC推斷 |
| `composite_nonoverlap_quantiles.csv` | 最終分數三組獨立日曆分箱 |
| `strict_stress_current_vs_tuned.csv` | 基線同調優策略嚴格成本比較 |
| `strict_tuned_rolling_20periods.csv` | 最終60/40混合分數滾動穩定性 |
| `scheduled_exit_minute_comparison.csv` | 分鐘賣出時間同成交可用率 |
| `etf_regime_nested_summary.csv` | 六折nested ETF選參摘要 |
| `etf_regime_continuous_oos.csv` | 自適應、固定同無風控連續樣本外比較 |
| `matched_period_benchmark_comparison.csv` | 策略同五個市場基準共同區間比較 |
| `public_model_holdout_comparison.csv` | 三類機器學習模型留出期比較 |

## 擴展研究記錄

其他表格保留調參網格、逐期NAV、模型輸出、ETF敏感度、nested selections、持倉分布同歷史比較，用嚟追蹤研究決策，但唔影響閱讀主要結論。`example_trade_schema.csv`係匿名交易輸出格式樣例。

`public_headline_metrics.csv`係根目錄README使用嘅摘要。公開目錄冇原始行情、個股級回測記錄、賬戶資料、實盤持倉或者登入資料。

重新生成圖表：

```bash
python scripts/generate_report_assets.py
```
