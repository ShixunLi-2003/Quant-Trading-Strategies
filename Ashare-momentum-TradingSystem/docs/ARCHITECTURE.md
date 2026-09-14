# System Architecture

```mermaid
flowchart LR
    A[Licensed daily and minute data] --> B[Normalization and quality checks]
    B --> C[Point-in-time universe]
    C --> D[Daily and intraday factors]
    D --> E[IC and quantile diagnostics]
    D --> F[Fixed blend and walk-forward models]
    F --> G[Cost-aware portfolio simulator]
    H[ETF market panel] --> I[Regime and breadth engine]
    I --> G
    G --> J[Strict, holdout, rolling, and minute tests]
    F --> K[Live signal plan]
    I --> K
    K --> L[Broker adapter]
    L --> M[Position ownership and order reconciliation]
```

The public repository keeps the broker adapter boundary abstract. Broker credentials, account identifiers, local terminal paths, live state, and order history are not part of the research artifact.

