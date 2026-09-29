"""Run this first in ALGOGENE Jupyter before a debug training job."""

import json
from AlgoAPI.AlgoAPIUtil import getHistoricalBar
from core import environment_probe

print(json.dumps(environment_probe(getHistoricalBar), ensure_ascii=False, indent=2))
