# DR-0005 — Uplift unit of analysis: combo level with concurrency controls

- **Date**: 2026-08-04
- **Status**: accepted
- **Phase**: 4
- **Decided by**: Marco Saenz, this repository's author (AI-assisted: yes — Claude Code).
  DR-0001…DR-0004 name Luis Angel Almazán López because they arrived with the imported
  baseline; DR-0005, DR-0006 and DR-0007 were each decided here on 2026-08-04 and name the
  author who decided them.

## Context

This repository's own uplift work (`uplift.detect_episodes`) deliberately estimates at the
*episode* level — promotional pressure derived from observed intensity — rather than at
`id_combo` level, on the stated grounds that several combos can run on the same SKU at once
and a per-combo estimate would be contaminated by whichever other combos happen to be live
in the same weeks.

The commercial-analysis port being brought into this repo estimates uplift per `id_combo`
directly, and that choice surfaced a result the episode layer cannot see: SKU 1857
averages **+1%** uplift (not significant) at the episode level, but one combo inside it,
n.33, reads **+50%** (p ≈ 0.011) on its own. Aggregating to SKU or episode level washes out
a mechanic-level effect that, if real, is exactly the kind of finding a promotion-repeat
recommendation should be built on.

The question this decision answers: **what is the unit of analysis for the ported uplift
estimates, and does adopting combo level abandon the concurrency safeguard episodes exist
to provide?**

## Options considered

| Option | Pros | Cons |
|---|---|---|
| Episodes alone (this repo's existing approach) | Measures combined promotional pressure on a SKU, which is a real quantity a planner cares about; immune to combo-overlap contamination by construction | Masks mechanic-level heterogeneity — a SKU averaging +1% can contain a combo at +50%; a repeat/drop recommendation made at this grain would silently blend a strong mechanic with weak ones and recommend neither clearly |
| Uncontrolled combo-level (the port's original method) | Right unit for a mechanic-specific recommendation; where it lives (SKU 1857) is where the reader actually needs the answer | Contaminated whenever combos overlap in time on the same SKU, and on this dataset they demonstrably do — 31 combos across 57 promotional weeks on SKU 1283 alone; an uncontrolled combo-level number cannot be told apart from a neighbor combo's effect leaking in |
| **Combo-level estimates with concurrent combos entered as controls, episodes kept as a second layer** | Keeps the mechanic-level resolution that motivated the port, while directly addressing this repository's own objection instead of ignoring it; episodes remain available for the question they answer well (aggregate promotional pressure) | Two layers to report and explain rather than one; the combo-level model needs enough concurrent-combo variation to identify a control coefficient, which is not guaranteed on every SKU |

## Decision

Uplift is estimated at `id_combo` level, with concurrent combos on the same SKU and a
linear time trend entered as controls. Episode-level estimates (`uplift.detect_episodes`)
are retained as a second, independent layer rather than replaced. The two are reported
side by side, each labelled with what it measures: episodes answer "how much did
promotional pressure move volume on this SKU," combos answer "did this specific mechanic
work, net of what else was running."

Whether the concurrency control actually holds up for the SKU 1857 / combo n.33 result is
not assumed here — it is registered as **H-007** in `docs/HYPOTHESES.md`, with its
rejection condition written before the controlled model is run.

## Rationale

The deciding factor is that "episodes alone" and "uncontrolled combo-level" are each right
about the thing the other one gets wrong, and neither failure mode is acceptable to ignore
silently. Episodes are immune to the overlap problem only because they average it away;
uncontrolled combos see the mechanic but are exposed to exactly the contamination this
repository built episodes to avoid. Reporting only one layer would either bury a
+50%-reading mechanic inside a +1% SKU average, or publish a combo-level number this
repository's own stated concern (combo overlap) has not been checked against.

Concurrency pressure is not uniform across SKUs, which is why a blanket choice between the
two options would be wrong in different directions depending on the SKU: 31 combos across
57 promotional weeks on SKU 1283 versus 9 combos across 31 promotional weeks on SKU 1857 —
where the +50% result lives. The lower concurrency on 1857 makes the objection real but not
obviously fatal to that specific estimate, which is why the right move is to test it
(H-007) rather than to assume the control will or will not survive.

## Consequences

- The combo-level model requires enough concurrent-combo weeks to fit a control term; on
  SKUs with too few concurrent combos the control may be underpowered, and that limitation
  must be disclosed alongside any combo-level number, not just for SKU 1857.
- Any combo-level uplift figure quoted in a report must state whether it is the
  uncontrolled or the concurrency-controlled estimate — the two are not interchangeable,
  and only the controlled one may be used to justify a repeat/drop recommendation once
  H-007 reaches a verdict.
- Episodes are not deprecated: they remain the answer to "how much aggregate promotional
  lift did this SKU see," a question a repeat/drop recommendation at the mechanic level
  does not answer on its own.
- Revisit trigger: if H-007 is rejected (the +50% reading does not survive concurrency
  controls), the combo-level layer's headline claim for SKU 1857 is withdrawn and the
  episode-level +1% (not significant) becomes the only reportable number for that SKU —
  this decision to keep both layers stands regardless, since the two-layer structure is
  what made that outcome checkable in the first place.
