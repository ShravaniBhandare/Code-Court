# Survival signal

The survival signal measures how much meaningful source code added by an author
is still present at `HEAD`. Git blame attributes each line to the last commit
that changed it. Blame runs with `-w` (whitespace-only changes do not take
ownership) and `-M` (moves within a file are followed); `-C` is intentionally
not used because cross-file copying is too expensive. If
`.git-blame-ignore-revs` exists, it is passed to Git when supported.

Survival rates use the uncapped meaningful-line denominator from the analyzed
commit window. Scores shrink small samples toward the repository-wide rate.
Blame is limited by file size and count; below the configured byte coverage
threshold, survival scores are unavailable.

This is a historical signal, not proof of authorship. Recently written code
has had less time to be rewritten and can look better than it is. Because
blame credits the last editor, lines changed by another author can be
mis-credited; moved code across files can also be mis-credited.
