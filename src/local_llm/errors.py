"""Errors shared by all model backends."""

import httpx

_BODY_LIMIT = 200


class BackendError(RuntimeError):
    """A model backend request failed."""


def error_detail(exc: httpx.HTTPError) -> str:
    """Describe a failed request, including the server's own reason for an HTTP error.

    Servers explain 4xx failures in the body (for example "request exceeds the available
    context size"); without it the caller only sees "400 Bad Request". Some httpx errors
    (e.g. ReadTimeout) have an empty message, so the type is always named.
    """
    detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
    if isinstance(exc, httpx.HTTPStatusError):
        body = exc.response.text.strip()[:_BODY_LIMIT]
        if body:
            detail += f" - server said: {body}"
        if "context" in body.lower() and "exceed" in body.lower():
            detail += " (raise LOCAL_LLM_CONTEXT_TOKENS to match the server, or analyze less)"
    return detail
