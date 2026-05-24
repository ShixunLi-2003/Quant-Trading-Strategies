"""Compatibility package for the package-local source tree.

The original project imported modules from the ``hk_quant`` namespace.
This package keeps those imports working inside the standalone research
package without requiring an external installation step.
"""

__all__ = [
    "analysis",
    "backtests",
    "config",
    "data",
    "factors",
    "signals",
    "strategy",
    "visualization",
]
