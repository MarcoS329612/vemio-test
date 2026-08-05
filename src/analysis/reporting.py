"""Markdown report emission for lifecycle stages.

Every stage script writes an artifact into ``reports/`` (DR-0003). The header
records what ran, when, against which input checksum — so a number in a report
can always be traced back to the run that produced it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import config


def _fmt(value: Any) -> str:
    """Render a cell for markdown: readable, and never a raw NaN.

    Two rules exist because these tables are read by planners and commercial
    managers, not in a debugger. Booleans render as words — a bare ``1`` in a
    column called ``already_below_cost`` is a recommendation nobody can read.
    And magnitudes of 1,000 or more render as separated integers rather than
    the ``5.117e+04`` that a general-purpose significant-figure format
    produces: scientific notation in a units-per-quarter column is unusable.
    """
    if value is None or (isinstance(value, (float, np.floating)) and pd.isna(value)):
        return "—"
    if isinstance(value, (bool, np.bool_)):
        return "yes" if value else "no"
    if isinstance(value, (int, np.integer)):
        return f"{value:,}"
    if isinstance(value, (float, np.floating)):
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        return f"{value:,.4g}"
    return str(value).replace("|", r"\|")


@dataclass
class MarkdownReport:
    """Accumulates sections, then writes one markdown artifact."""

    title: str
    stage: str
    subtitle: str = ""
    _blocks: list[str] = field(default_factory=list)

    # ------------------------------------------------------------- content

    def heading(self, text: str, level: int = 2) -> MarkdownReport:
        self._blocks.append(f"{'#' * level} {text}")
        return self

    def text(self, body: str) -> MarkdownReport:
        self._blocks.append(body.strip())
        return self

    def bullets(self, items: Iterable[str]) -> MarkdownReport:
        self._blocks.append("\n".join(f"- {item}" for item in items))
        return self

    def table(self, frame: pd.DataFrame, index: bool = False) -> MarkdownReport:
        """Render a DataFrame as a markdown table."""
        data = frame.reset_index() if index else frame
        header = "| " + " | ".join(str(c) for c in data.columns) + " |"
        sep = "|" + "|".join(["---"] * len(data.columns)) + "|"
        rows = [
            "| " + " | ".join(_fmt(v) for v in row) + " |"
            for row in data.itertuples(index=False, name=None)
        ]
        self._blocks.append("\n".join([header, sep, *rows]))
        return self

    def key_values(self, pairs: dict[str, Any]) -> MarkdownReport:
        frame = pd.DataFrame({"Item": list(pairs), "Value": list(pairs.values())})
        return self.table(frame)

    def figure(self, path: Path, caption: str) -> MarkdownReport:
        """Embed a figure. The caption must carry the takeaway, not just a label."""
        rel = path.relative_to(config.REPORTS_DIR).as_posix()
        self._blocks.append(f"![{caption}]({rel})\n\n*{caption}*")
        return self

    def note(self, body: str) -> MarkdownReport:
        """A callout — used for caveats, assumptions and limitations."""
        quoted = "\n".join(f"> {line}" for line in body.strip().splitlines())
        self._blocks.append(quoted)
        return self

    # -------------------------------------------------------------- output

    def _header(self, params: dict[str, Any] | None) -> str:
        checksum_ok, digest = config.verify_raw_checksum()
        lines = [
            f"# {self.title}",
            "",
            "> **Generated artifact — do not edit by hand.** "
            f"Produced by `{self.stage}`; re-run the script to regenerate.",
            "",
        ]
        if self.subtitle:
            lines += [self.subtitle, ""]
        meta = {
            "Stage": f"`{self.stage}`",
            "Generated (UTC)": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "Source file": f"`{config.RAW_DATASET_FILENAME}`",
            "Source SHA-256": f"`{digest[:16]}…`"
            + ("" if checksum_ok else " ⚠️ **does not match the recorded checksum**"),
        }
        if params:
            meta |= {f"Param · {k}": v for k, v in params.items()}
        lines += [
            "| Run metadata | Value |",
            "|---|---|",
            *[f"| {k} | {_fmt(v)} |" for k, v in meta.items()],
        ]
        if not checksum_ok:
            lines += [
                "",
                "> ⚠️ The input file differs from the one recorded in "
                "`docs/case/README.md`. Results are not comparable to earlier runs.",
            ]
        return "\n".join(lines)

    def write(self, filename: str, params: dict[str, Any] | None = None) -> Path:
        config.ensure_output_dirs()
        path = config.REPORTS_DIR / filename
        body = "\n\n".join([self._header(params), *self._blocks]) + "\n"
        path.write_text(body, encoding="utf-8")
        return path


def section_findings(candidates: Sequence[tuple[str, str]]) -> str:
    """Format candidate findings for hand-off into docs/FINDINGS.md.

    Stage scripts surface what they observed; promoting an observation to a
    registered finding stays a human decision (standard 07).
    """
    if not candidates:
        return "No new candidate findings from this run."
    return "\n".join(f"- **{label}** — {detail}" for label, detail in candidates)
