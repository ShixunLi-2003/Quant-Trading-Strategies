# ALGOGENE 纳斯达克100分钟深度学习框架

本包用于在 ALGOGENE Jupyter 训练分钟特征模型，并在 ALGOGENE Backtest 加载冻结模型。训练层、因子层和交易执行层分离；更换模型时不需要修改订单逻辑。

## 已固定的研究与回测设置

- 平台股票池：100只纳斯达克100公司代表股，见 `nasdaq100_symbols.txt`。
- Alphabet 同时有 `GOOGL/GOOG` 两类证券。为满足账户单次100标的限制，本框架保留 `GOOGL`，排除同公司的 `GOOG`。
- 股票池快照日期：2026-09-29。把当前成分股用于2020年以来历史会产生幸存者偏差，运行清单会明确记录此风险。
- 分钟数据：`interval=M`，仅使用美股常规交易时段。
- 滚动训练：训练窗口最多42个交易日，不超过约三分之二季度；验证、隔离期和测试窗口按 `config.json` 执行。
- 初始资金：10,000美元。
- 模型选择目标：首先最大化扣除交易成本后的总收益；收益差在容忍范围内时，再选择最大回撤更小的模型。
- 默认持仓：每天选择预测分数最高的5只股票。

平台已实测对当前账户执行100标的硬限制，因此默认平台配置不订阅额外指数或板块ETF。原有大盘、利率、商品和板块数据仍保留在本地研究数据中，可用于离线扩展；若加入最终平台模型，就必须减少股票数量，或者先获得更高的平台额度，否则训练与回测特征会不一致。

## Jupyter财务数据总表（不占100个行情名额）

财务数据以 point-in-time 总表加载，不加入 `subscribeList`，因此100个订阅名额仍全部用于股票分钟行情。框架不计算滚动PE、动态PE、增长率或其他财务因子，也不默认把任何财务列加入模型。队友在 Jupyter 中查看总表后，自行决定使用哪些原始数值列。

默认路径是：

```text
/lib/nasdaq100_dl_data/fundamentals_pti.csv.gz
```

字段模板见 `fundamentals_schema.csv`。总表可以包含任意数量的资产负债表、利润表和现金流量表数值列，但必须具备：

- `symbol`：股票代码；
- `filed_at`：财报真正公开的时间，即 SEC `filingDate`/发布时间；
- `report_date`：财务报告截止日，只作审计信息，绝不能用它决定数据何时可见；
- `filing_id`：建议保留，用来识别同一报告的版本或修订；
- 其余列：平台或数据源返回的原始财务数值。

### 未来函数硬限制

这部分不能关闭：

1. 没有 `filed_at` 的总表拒绝加载；只有 `report_date` 也会直接报错。
2. 框架从 `filed_at` 加默认24小时安全延迟，形成内部 `effective_at`。
3. 训练样本只能执行 backward as-of join，即 `effective_at <= prediction_time`。
4. 合并后再次运行审计；发现任何来源时间晚于预测时间，训练立即失败并打印违规样本。
5. 正式训练使用的总表会冻结进模型目录并写入 SHA256，Backtest 不能悄悄换成后来修订的数据。

不能把今天查询到的“最新财务总表”向过去回填。若数据源只能给当前值而没有历史 `filed_at` 快照，该字段不能进入历史训练。

`config.json` 中：

```json
"fundamentals": {
  "enabled": true,
  "required": false,
  "path": "/lib/nasdaq100_dl_data/fundamentals_pti.csv.gz",
  "strict_point_in_time": true,
  "availability_lag_hours": 24,
  "feature_prefix": "fin_",
  "minimum_coverage": 0.75
}
```

财务连接配置不负责选择模型字段。队友统一在顶层 `dataset_columns` 里选择，例如：

```json
"dataset_columns": ["*", "fin_revenue_ttm", "fin_net_income_ttm", "fin_eps_ttm"]
```

框架会按原值生成 `fin_revenue_ttm` 等模型列，不做额外财务计算。也可以在 Jupyter 中安全查看某个历史时点：

```python
from fundamentals import load_point_in_time_fundamentals, safe_financial_snapshot

financials = load_point_in_time_fundamentals(
    "/lib/nasdaq100_dl_data/fundamentals_pti.csv.gz",
    availability_lag_hours=24,
)
available_columns = financials.columns.tolist()
snapshot = safe_financial_snapshot(financials, "2024-06-30T23:59:59Z")
```

首次调试允许 `required=false`：文件不存在时会明确打印 `FUNDAMENTALS_DISABLED`。正式使用任何 `fin_` 财务列时，必须上传总表并设置 `required=true`；所选列有效覆盖率不足75%时训练直接终止。实验目录由 `job_name=auto` 自动生成。

## 需要上传什么

在本地运行：

```powershell
python .\build_training_bundle.py
```

生成：

- `dist/algogene_nasdaq100_dl/nasdaq100_dl/`：上传到 ALGOGENE `/lib/nasdaq100_dl`。
- `dist/algogene_nasdaq100_dl/algogene_submission.py`：复制到 Backtest 代码编辑器。
- `dist/algogene_nasdaq100_dl.zip`：供队友通过 Git 下载或解压。

财务增强训练还要上传 `fundamentals_pti.csv.gz` 到 `/lib/nasdaq100_dl_data/`。正式训练完成后，框架会把实际使用的财务快照复制进冻结模型目录并写入 SHA256；Backtest 只读该冻结副本，不会临时联网调用财务接口。

不要上传 API Key、Jupyter 临时链接、日志中的 token 或本地数据目录。

## Jupyter训练步骤

打开 [ALGOGENE Data Studio/Jupyter](https://algogene.com/annotation)，依次运行：

```python
import sys
sys.path.insert(0, "/lib/nasdaq100_dl")
%run /lib/nasdaq100_dl/platform_probe.py
```

先运行小范围调试：

```python
%run /lib/nasdaq100_dl/run_jupyter.py --config /lib/nasdaq100_dl/config.json --mode debug
```

调试通过后直接正式训练：

```python
%run /lib/nasdaq100_dl/run_jupyter.py --config /lib/nasdaq100_dl/config.json --mode train
```

`job_name=auto` 会根据模型、参数和输入列生成稳定且唯一的实验目录名，不需要队友手动命名。缓存目录 `/lib/nasdaq100_dl_cache` 支持按股票断点续跑；冻结模型输出到 `/lib/nasdaq100_dl_runs/<自动生成的job_name>`。

`debug` 只验证数据、特征和模型接口是否能跑通，不代表正式测试结果；只有 `train` 产生的完整滚动样本外预测和冻结模型才可以进入最终 Backtest。

## Jupyter平台式回测口径

Jupyter 的模型选择和样本外评估使用与平台交易脚本接近的执行顺序：

1. 交易日 D 的常规时段分钟数据结束后生成特征和排名；
2. D+1 的第一个可用分钟价格建仓；
3. D+2 的第一个可用分钟价格平仓，并切换到新组合；
4. 每次选择 `selection_top_n` 只股票、等资金分配、只买整股；
5. 未能买入整股的资金保留为现金；
6. 买卖分别计入配置中的滑点和佣金；买单滑点不会超过平台限价缓冲；
7. 初始资金固定为10,000美元。

因此训练目标也使用下一交易日开盘到再下一交易日开盘的收益，与平台实际持有区间对齐，不再用收盘到收盘收益代替。

配置中的共同执行参数为：

```json
"selection_top_n": 5,
"initial_capital_usd": 10000,
"entry_slippage_bps": 2,
"exit_slippage_bps": 2,
"commission_bps": 1,
"minimum_commission_usd": 0,
"limit_buffer": 0.002
```

正式训练会额外输出：

- `jupyter_platform_like_metrics.json`：净收益、最大回撤、期末权益和交易数；
- `jupyter_platform_like_equity.csv`：逐交易日权益曲线；
- `jupyter_platform_like_trades.csv`：整股成交、价格、佣金和净盈亏明细。

这仍是对平台撮合的近似，不承诺数值完全相同。平台订单排队、网络/回调延迟、真实点差、停牌、拒单和平台内部费率只能以最终 ALGOGENE Backtest 结果为准；Jupyter 用于模型筛选和快速排错，最终成绩仍以平台回测为准。

## 队友开箱即用：只选择模型和数据列

先查看可用模型：

```python
%run /lib/nasdaq100_dl/list_models.py
```

内置模型：

- `sklearn_mlp`：依赖最少的神经网络基线；
- `torch_mlp`：可配置多层 PyTorch 网络，平台探针显示 PyTorch 可用时选择。

队友日常只改 `config.json` 的两个位置：

```json
"model_name": "torch_mlp",
"dataset_columns": [
  "*",
  "fin_revenue_ttm",
  "fin_net_income_ttm",
  "fin_eps_ttm",
  "fin_total_equity"
]
```

列选择规则：

- `"*"`：使用框架全部分钟特征；
- 指定 `ret_1d`、`realized_vol` 等名称：只使用列出的分钟特征；
- `fin_字段名`：使用财务总表中的该原始字段；
- `"fin_*"`：使用财务总表全部可转换为数值的字段。

滚动窗口、隔离期、未来函数审计、训练/验证划分、模型选择、保存、SHA256和黄金样本校验全部由框架执行。

若队友要接入自己的模型，只需复制 `models/model_template.py` 为 `models/队友模型名.py`，实现：

```python
fit(x_train, y_train, x_validation, y_validation) -> dict
predict(features) -> 每行一个预测分数
save(path) -> None
```

然后只选择文件名：

```json
"model_name": "队友模型名"
```

### 论文模型和非深度学习模型

框架不限制模型类型。只要最终能为每一行“股票×信号日”样本返回一个可排序分数，就可以参与相同的滚动训练和平台式回测。

可以直接按当前二维表格契约接入：

- Ridge、Lasso、ElasticNet；
- 随机森林、ExtraTrees、Gradient Boosting、HistGradientBoosting；
- SVM、KNN；
- XGBoost、LightGBM、CatBoost（ALGOGENE 环境必须存在对应依赖）；
- sklearn MLP、PyTorch/TensorFlow 全连接网络；
- 论文中的普通表格回归、分类或横截面打分模型。

分类模型应在 `predict()` 返回上涨概率或其他连续分数，而不是类别0/1。回归模型可以直接输出未来收益或残差收益预测。

以下论文结构也可以使用，但需要在单个模型插件内完成对应的数据适配：

- LSTM、GRU、TCN、Transformer：把二维行整理成按股票连续的三维序列，并保证序列只含预测时点以前的数据；
- Learning-to-Rank：按交易日构造 group 信息，并输出横截面排序分数；
- GNN：另外准备股票关系图，而且每条边也必须满足 point-in-time；
- 强化学习：另外实现状态、动作、奖励和环境，不能直接套用普通 `fit/predict`；
- 使用原始390分钟序列的论文模型：需要序列数据适配器，因为默认输入是由分钟行情形成的日级特征表。

无论论文原代码如何组织，接入后不得绕过框架的数据时间审计、滚动切分、embargo、样本外评估和冻结模型校验。论文使用的第三方库版本、随机种子、论文链接、关键超参数和与原论文不一致的修改，都应写进模型文件注释和实验清单。

如果论文模型依赖特殊包或 CUDA，先运行 `platform_probe.py` 和 `list_models.py`。平台缺少依赖时，应改用平台现有库、上传兼容的纯 Python 代码，或选择等价模型；不能假设本地可以运行就代表 ALGOGENE 可以运行。

如果要比较财务数据是否有效，保持模型和窗口相同，只改变 `dataset_columns`：先跑 `['*']`，再跑加入 `fin_...` 的版本。不要只比较训练集损失，应比较滚动样本外净收益、最大回撤、日度IC、换手和分年度稳定性。

不要为了更换模型修改 `core.py`、`online.py` 或交易订单代码，除非特征契约也确实改变；否则 Jupyter 与 Backtest 会发生预测不一致。

## 另一台设备和队友需要上传什么

完整逐项清单见 `TEAMMATE_UPLOAD_CHECKLIST_CN.md`。最简流程是：

1. 从 Git 拉取本项目目录；
2. 将 `dist/algogene_nasdaq100_dl/nasdaq100_dl/` 整个目录上传为 ALGOGENE `/lib/nasdaq100_dl/`；
3. 如使用财务列，再将合规的 `fundamentals_pti.csv.gz` 上传到 `/lib/nasdaq100_dl_data/`；
4. 自定义论文模型文件上传到 `/lib/nasdaq100_dl/models/`，然后只修改 `model_name` 和 `dataset_columns`；
5. 在 Jupyter 依次运行平台探针、模型清单、debug 和 train；
6. 在 Backtest 页面粘贴 `algogene_submission.py`，保持 `MODEL_BUNDLE="auto"`；
7. 队友训练后应回传完整冻结模型目录、`latest.json`、环境报告、manifest、样本外预测和Jupyter平台式回测结果。

不得上传或提交到 Git：API Key、User Token、Jupyter临时URL、带token日志、原始分钟大数据和未经授权再分发的财务数据。大型模型或获准共享的数据只能使用 Git LFS，并且仍需遵守数据许可。

## 平台回测步骤

打开 [ALGOGENE Backtest](https://algogene.com/backtest)：

1. 上传训练包和冻结模型目录；
2. 在设置中严格选择 `nasdaq100_symbols.txt` 的100只证券，不添加指数或ETF；
3. 初始资金设为 `10000 USD`；
4. 数据频率选择 `1m`；
5. 将 `algogene_submission.py` 复制到编辑器；
6. 保持 `MODEL_BUNDLE="auto"`，脚本会读取 `/lib/nasdaq100_dl_runs/latest.json` 并加载最近一次成功训练；需要复现旧实验时才填写明确目录；
7. 运行并记录 Backtest ID。

启动时脚本会校验：订阅不得超过100只、订阅集合必须与冻结模型股票池完全一致、模型及特征文件SHA256正确、黄金样本预测一致。任一条件不满足就停止，避免静默产生失真结果。

最终提交前必须保留：ALGOGENE User ID、Backtest ID、完整策略脚本、收益与最大回撤、资金管理、风险控制、真实交易预期。最终回测只加载冻结模型，不在 Backtest 中重新训练。
