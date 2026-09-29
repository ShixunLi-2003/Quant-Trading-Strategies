# 队友另一台设备：Git、Jupyter与Backtest上传清单

本文档用于队友在另一台电脑上从 Git 拉取框架、上传 ALGOGENE、训练模型，并把结果完整交回。

## 一、Git中应当存在的内容

- `training_framework/`：训练、时点财务访问、在线特征、推理和测试源码；
- `training_framework/models/`：内置模型、论文模型模板；
- `nasdaq100_symbols.txt`：严格100只平台证券；
- `nasdaq100_metadata.json`：股票池元数据与快照说明；
- `nasdaq100_missing_local_data.txt`：本地数据缺口审计；
- `build_training_bundle.py`：重新生成平台上传包；
- `dist/algogene_nasdaq100_dl.zip`：已经构建的便捷上传包；
- `dist/algogene_nasdaq100_dl/algogene_submission.py`：Backtest提交脚本；
- 中文 README 和本清单。

Git中不应存在 API Key、token、Jupyter临时链接、`/lib`缓存、原始分钟数据、训练输出目录或无授权财务总表。

## 二、另一台电脑从Git拉取后

可直接使用仓库附带的 ZIP，也可以重新构建：

```powershell
python .\build_training_bundle.py
```

重新构建后检查：

```powershell
Get-FileHash .\dist\algogene_nasdaq100_dl.zip -Algorithm SHA256
```

本地只做源码测试时，基础依赖为 Python、NumPy、pandas、scikit-learn、joblib；PyTorch、XGBoost、LightGBM、CatBoost 等是按所选模型决定的可选依赖。真正能否在平台运行，以 ALGOGENE Jupyter 探针为准。

## 三、上传到ALGOGENE `/lib` 的内容

必须上传：

```text
/lib/nasdaq100_dl/
```

该目录必须包含 `run_jupyter.py`、`core.py`、`contracts.py`、`fundamentals.py`、`online.py`、`inference.py`、`config.json`、`nasdaq100_symbols.txt`、`models/` 和中文文档。

如果选择任何 `fin_` 财务列，还必须上传：

```text
/lib/nasdaq100_dl_data/fundamentals_pti.csv.gz
```

财务总表必须包含 `symbol` 和真实公开时间 `filed_at`。只有 `report_date` 的表禁止使用。数据许可不允许共享时，不得通过 Git 传递，由各自账户合法取得后上传。

如果测试论文模型，把单个模型插件文件上传到：

```text
/lib/nasdaq100_dl/models/<model_name>.py
```

不需要上传本地原始分钟数据；Jupyter框架通过ALGOGENE历史数据接口构建或复用 `/lib/nasdaq100_dl_cache`。

## 四、队友只需选择的配置

```json
"model_name": "sklearn_mlp",
"dataset_columns": ["*", "fin_revenue_ttm", "fin_eps_ttm"]
```

- `*`：全部默认分钟特征；
- `fin_字段名`：财务总表指定原始列；
- `fin_*`：全部可转换为数值的财务列。

切换模型时可选修改 `model_params`，但内置模型在空参数下可以直接运行。不要关闭 `strict_point_in_time`，框架也会拒绝这种配置。

## 五、Jupyter运行顺序

```python
import sys
sys.path.insert(0, "/lib/nasdaq100_dl")

%run /lib/nasdaq100_dl/platform_probe.py
%run /lib/nasdaq100_dl/list_models.py
%run /lib/nasdaq100_dl/run_jupyter.py --config /lib/nasdaq100_dl/config.json --mode debug
%run /lib/nasdaq100_dl/run_jupyter.py --config /lib/nasdaq100_dl/config.json --mode train
```

`debug`成功只表示接口跑通；正式结果必须来自`train`。正式训练会自动生成job目录，并写入：

```text
/lib/nasdaq100_dl_runs/<job_name>/
/lib/nasdaq100_dl_runs/latest.json
```

## 六、上传到Backtest页面的内容

1. 确认训练生成的完整目录仍位于 `/lib/nasdaq100_dl_runs/`；
2. 复制 `algogene_submission.py` 到 Backtest 编辑器；
3. 保持 `MODEL_BUNDLE="auto"`；
4. 股票订阅严格选择 `nasdaq100_symbols.txt` 的100只，不增加ETF或指数；
5. 数据频率选择1分钟，初始资金设置10,000美元；
6. 运行并保存 Backtest ID、日志、收益、最大回撤和交易明细。

## 七、队友训练后必须交回的文件

交回整个 `/lib/nasdaq100_dl_runs/<job_name>/`，不要只交 `model.joblib`。至少包括：

- `model.joblib`；
- `manifest.json`；
- `feature_schema.json`；
- `golden_sample.npz`；
- `environment.json`；
- `rolling_windows.json`；
- `oos_predictions.csv.gz`；
- `jupyter_platform_like_metrics.json`；
- `jupyter_platform_like_equity.csv`；
- `jupyter_platform_like_trades.csv`；
- `nasdaq100_symbols.txt`；
- 若模型使用财务列，冻结的 `fundamentals_pti.csv.gz`；
- 上一级 `/lib/nasdaq100_dl_runs/latest.json`；
- ALGOGENE Backtest ID和最终平台结果。

模型和结果文件较大时使用 Git LFS；原始分钟数据不要提交。提交前先检查 `manifest.json` 中的模型、特征、股票池、时间范围、环境和SHA256是否完整。

## 八、禁止事项

- 禁止使用今天查询到的最新财务值回填历史；
- 禁止用`report_date`代替`filed_at`；
- 禁止修改未来函数审计后仍声称结果来自标准框架；
- 禁止把debug结果当正式结果；
- 禁止只上传模型而遗漏特征schema和黄金样本；
- 禁止把API Key、token或带鉴权参数的URL提交到Git。
