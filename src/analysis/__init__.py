"""Reusable analysis library for the VEMIO CPG case.

Layer separation (see docs/decisions/DR-0003-scripts-over-notebooks.md):
this package holds all logic; ``scripts/NN_*.py`` are thin stage entry points
that run a lifecycle stage end-to-end and emit its report into ``reports/``.
"""

__all__ = ["config", "io", "quality", "reporting"]
