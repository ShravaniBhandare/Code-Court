"""Exceptions raised by repository ingestion."""


class CodeCourtError(Exception):
    """Base exception for expected CodeCourt errors."""


class InvalidRepoURL(CodeCourtError):
    """Raised when a repository URL cannot be parsed."""


class RepoNotFound(CodeCourtError):
    """Raised when a repository is missing or private."""


class RepoTooLarge(CodeCourtError):
    """Raised when a repository exceeds the configured size limit."""


class RateLimited(CodeCourtError):
    """Raised when GitHub API rate limiting prevents a request."""


class GitHubAPIError(CodeCourtError):
    """Raised when GitHub returns an unusable API response."""


class CloneFailed(CodeCourtError):
    """Raised when cloning or updating a repository fails."""


class AnalysisTimeout(CodeCourtError):
    """Raised when an analysis exceeds its time limit."""


class AnalysisCancelled(CodeCourtError):
    """Raised when an analysis is cancelled."""


class AnalysisNotFound(CodeCourtError):
    """Raised when an analysis id does not exist."""


class AnalysisNotReady(CodeCourtError):
    """Raised when results are requested before completion."""


class TooManyRequests(CodeCourtError):
    """Raised when a client exceeds the analysis request limit."""


class QueueFull(CodeCourtError):
    """Raised when the analysis queue is full."""
