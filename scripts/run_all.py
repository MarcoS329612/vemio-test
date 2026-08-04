"""Run every lifecycle stage in order, from raw data to reports.

This is the reproducibility test in the definition of done (standard 06): on a
clean environment with the raw file in place, this reproduces every number in
the deliverables.

    uv run scripts/run_all.py

Stages are discovered by filename (``NN_*.py``) and run in numeric order, so a
new stage needs no registration here. A failing stage stops the run — a
half-regenerated ``reports/`` directory is worse than none.
"""

from __future__ import annotations

import runpy
import sys
import time
from pathlib import Path

STAGES_DIR = Path(__file__).resolve().parent


def discover_stages() -> list[Path]:
    return sorted(
        p for p in STAGES_DIR.glob("[0-9][0-9]_*.py") if p.name != Path(__file__).name
    )


def main() -> int:
    stages = discover_stages()
    if not stages:
        print("No stage scripts found.")
        return 1

    print(f"Running {len(stages)} stage(s)\n")
    for stage in stages:
        print(f"{'=' * 70}\n▶ {stage.name}\n{'=' * 70}")
        started = time.perf_counter()
        try:
            runpy.run_path(str(stage), run_name="__main__")
        except Exception as exc:  # noqa: BLE001 — surface the failing stage clearly
            print(f"\n✗ {stage.name} failed: {type(exc).__name__}: {exc}")
            return 1
        print(f"✓ {stage.name} ({time.perf_counter() - started:.1f}s)\n")

    print("All stages completed. Artifacts are in reports/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
