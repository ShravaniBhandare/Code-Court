# Contribution scoring

The contribution score is a transparent 0-to-100 relative score for human
authors in one repository. Work is the amount of meaningful credited code,
adjusted by the bounded Stage 4 quality modifier. Survival and ownership come
from the Stage 5 blame analysis. Review, issues, and consistency are reserved
for later stages and can be supplied through the `extra_signals` hook.

The default weights are:

| Signal | Weight |
| --- | ---: |
| work | 0.45 |
| survival | 0.25 |
| ownership | 0.05 |
| review | 0.12 |
| issues | 0.06 |
| consistency | 0.07 |

Unavailable signals are removed and the remaining configured weights are
renormalized. Scores support logarithmic, square-root, and linear scaling.
Optional penalties are a hook for future anomaly detection and are clamped to
the configured minimum multiplier.

Quality is deliberately a bounded `0.7` to `1.2` modifier rather than a
separate signal. Scores are relative to other contributors in the same
repository, not absolute grades. The weights are provisional until validated
against hand-labelled data during the tuning stage.
