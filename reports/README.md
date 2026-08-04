# Reports

Two kinds of document live here. Both are committed; only one is written by hand.

## Generated stage artifacts (do not edit)

Produced by `scripts/NN_*.py`, one per lifecycle stage ([DR-0003](../docs/decisions/DR-0003-scripts-over-notebooks.md)).
Each carries a run header recording when it ran, against which input checksum, and with
what parameters — so any number in it traces back to the run that produced it.

They are committed on purpose: a reviewer reads the results without installing anything,
and the diff between commits shows how the numbers moved.

Editing one by hand breaks that guarantee. Change the script and re-run instead.

| Artifact | Produced by |
|---|---|
| `01_data_quality.md` | `scripts/01_data_audit.py` |
| `02_eda.md` | `scripts/02_eda.py` *(pending)* |
| `03_forecast.md` | `scripts/03_forecast.py` *(pending)* |
| `04_elasticity.md` | `scripts/04_elasticity.py` *(pending)* |
| `05_uplift.md` | `scripts/05_uplift.py` *(pending)* |

`figures/` holds generated plots and **is committed**, so the embedded images resolve when
a report is read on GitHub. The scripts overwrite them on each run.

## Final deliverables (hand-written)

The case's two written deliverables, drafted from the artifacts above:

| Deliverable | File | Audience |
|---|---|---|
| Methodology, assumptions & trade-offs (1–2 pages) | [methodology-and-tradeoffs.md](methodology-and-tradeoffs.md) | Technical reviewers |
| Five business recommendations | [business-recommendations.md](business-recommendations.md) | The client's commercial team |
| Technical walkthrough — methods and vocabulary explained | [technical-walkthrough.md](technical-walkthrough.md) | Anyone wanting the full reasoning |

The walkthrough exists because the case caps the methodology document at 1–2 pages. That
one states what was assumed and decided; the walkthrough explains how each method works and
why it was chosen, defining terms like leakage, rolling origin, WAPE, Fourier terms, HAC
errors, difference-in-differences and pull-forward as they come up.

Register conventions for each are in
[standard 06 — communication](../docs/methodology/06-communication.md): lead with the
recommendation, state uncertainty as consequence rather than statistics, and keep method
names out of the business document.
