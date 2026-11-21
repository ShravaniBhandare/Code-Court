# Anomaly flags

Stage 7 reports neutral patterns for human review; they are not accusations.
The checks are deterministic and include their numeric evidence:

- **Commit flood:** at least 10 commits in a 60-minute rolling window. It is
  warning-level when at least half are trivial, otherwise informational.
- **Last-minute burst:** at least 60% of an author's meaningful lines in the
  final three days, at least 100 lines, and at least 20 percentage points above
  the team share. It becomes a warning at 80%.
- **Trivial inflation:** at least 10 commits and at least 60% trivial commits.
- **Single-commit dump:** one commit contains at least 70% and 500 meaningful
  lines; this is informational because imports can be legitimate.
- **Low survival:** below 30% survival for at least 100 meaningful lines.

Warning flags can apply small visible penalties of 0.95, 0.90, or 0.90,
combined with a hard minimum multiplier of 0.5. Informational flags never
receive penalties. Penalties are visible in the score breakdown and are
intended to prioritize human review.

GitHub signals use public REST activity linked through commit email-derived
GitHub logins. Per-PR reviews are capped at 100 PRs, and without a token they
are skipped to stay within the unauthenticated request limit. Data can be
partial when rate limits or API errors occur. Copied-code and re-attribution
detection are future work.

False positives are possible for legitimate deadline crunches, imported code,
and hackathon repositories.
