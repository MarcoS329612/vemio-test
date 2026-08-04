# Source material — provenance manifest

Files delivered by VEMIO for the technical case. **Preserved verbatim: never edit, rename,
reformat, or "fix" anything in [`original/`](original/).** Every derived document links back
to the original it came from.

## Originals

| File | SHA-256 | Size | Content |
|---|---|---|---|
| [`original/prueba_tecnica_ai_product_engineer (2).docx`](original/) | `0BE437C74D636CABF22C184819B8F280846D73B81583C759F47D77EE024F8ADA` | 12,829 B | Case statement: context, dataset description, the three challenges, deliverables, evaluation criteria, logistics |
| [`original/README.md`](original/README.md) | `F77B1973FD22C36777D889C0C0AC73713D3E2022C59370FEA76625C8346B68C0` | 1,587 B | Data grain and column dictionary, as provided |
| `data/raw/20260701_Prueba_tecnica_AI Engineer.csv` | `A8A9B8A3D5C91955719D755C3D1E2778980088831A9E49AF07EF838BBF12EF86` | 80,513,309 B | Sell-in transactions (git-ignored — see DR-0002) |

Received: 2026-07-31. Original delivery folder: `~/Downloads/Prueba Tecnica`.
The dataset keeps its **original filename** in `data/raw/` so provenance is self-evident;
code resolves it through `src/analysis/config.py`, never by hardcoding the path.

Verify integrity at any time:

```powershell
Get-FileHash -Algorithm SHA256 "data\raw\20260701_Prueba_tecnica_AI Engineer.csv"
```

## Derived documents (ours, not VEMIO's)

| File | What it is | Derived from |
|---|---|---|
| [case-summary.md](case-summary.md) | English working summary of requirements, deliverables and evaluation weights | the `.docx` above |

Where a derived document and an original disagree, **the original prevails**.

## Discrepancies found between the originals and the delivered data

Recorded here because they change how the case must be answered; tracked as findings in
[../FINDINGS.md](../FINDINGS.md) and as open questions in [../ROADMAP.md](../ROADMAP.md).

- **`product_margin` is described in the dictionary and required by Challenge B, but the
  CSV does not contain it** (21 columns delivered). See finding F-001 / question Q1.
