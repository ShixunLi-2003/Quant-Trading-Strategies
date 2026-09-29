# Git上传目录完整性清单

目录：`US-Stock-Strategies/Nasdaq100-ALGOGENE-ML-Framework`

## 必须提交的源码

- `training_framework/core.py`
- `training_framework/contracts.py`
- `training_framework/fundamentals.py`
- `training_framework/online.py`
- `training_framework/inference.py`
- `training_framework/run_jupyter.py`
- `training_framework/platform_probe.py`
- `training_framework/list_models.py`
- `training_framework/algogene_submission.py`
- `training_framework/models/model_template.py`
- `training_framework/models/sklearn_mlp.py`
- `training_framework/models/torch_mlp.py`
- `training_framework/tests/test_framework.py`

## 必须提交的配置、股票池和文档

- `training_framework/config.example.json`
- `training_framework/fundamentals_schema.csv`
- `training_framework/requirements.txt`
- `nasdaq100_symbols.txt`
- `nasdaq100_metadata.json`
- `nasdaq100_missing_local_data.txt`
- `README.md`
- `TEAMMATE_UPLOAD_CHECKLIST_CN.md`
- `build_training_bundle.py`

## 必须提交的平台便捷包

- `dist/algogene_nasdaq100_dl.zip`
- `dist/algogene_nasdaq100_dl/algogene_submission.py`
- `dist/algogene_nasdaq100_dl/nasdaq100_dl/`

仓库根 `.gitignore` 原本会忽略所有 `dist/`。本目录的局部 `.gitignore` 已通过 `!dist/` 与 `!dist/**` 显式恢复该平台包。

## 明确不提交

- API Key、User Token、Jupyter临时URL；
- 本地或 `/lib` 日志；
- 原始分钟行情数据；
- `/lib/nasdaq100_dl_cache`；
- `/lib/nasdaq100_dl_runs`（除非是经过审查、需要协作的冻结实验，并使用Git LFS）；
- 无再分发许可的财务总表；
- `__pycache__`、`.pyc`、临时输出。

## 提交前验证命令

```powershell
python -m unittest discover -s .\training_framework\tests -v
python .\build_training_bundle.py
Get-FileHash .\dist\algogene_nasdaq100_dl.zip -Algorithm SHA256
git status --short -- .
```

正常结果应包含本项目目录下的源码、文档和 `dist` 平台包，且不包含任何凭据或原始大数据。
