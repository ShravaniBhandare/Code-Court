"""API dependency accessors."""

from fastapi import Request


def get_service(request: Request):
    return request.app.state.analysis_service
