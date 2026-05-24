# Core

The `core` package contains the framework internals that make the strategy portable: market-data alignment, financial-data joins, strategy configuration models, simulation logic, and plotting helpers.

- `market_essentials.py`: trading-calendar alignment, adjusted-price construction, and selection diagnostics.
- `equity.py`: account-path simulation and benchmark-overlay chart rendering.
- `fin_essentials.py`: rolling financial-field construction used by valuation-style factors.
- `model/`: strongly typed configuration objects for strategy and timing modules.
- `utils/`: path helpers and lazy module resolvers.
