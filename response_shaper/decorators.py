from functools import wraps
from typing import Any, Callable

from asgiref.sync import iscoroutinefunction
from rest_framework.response import Response

from .responses import (
    api_response,
    auth_api_response,
    batch_api_response,
    error_api_response,
    minimal_success_response,
    paginated_api_response,
)
from .types import ResponseFuncType


def _format_response(response: Any, response_func: ResponseFuncType) -> Any:
    if not isinstance(response, Response):
        return response

    if response_func == minimal_success_response:
        return response_func(status_code=response.status_code)

    if response_func == error_api_response:
        return response_func(
            message=response.data.get("message", "An error occurred"),
            errors=response.data.get("errors", None),
            error_code=response.data.get("error_code", None),
            status_code=response.status_code,
        )

    if response_func == paginated_api_response:
        return response_func(
            data=response.data.get("data", None),
            page=response.data.get("page", None),
            total_pages=response.data.get("total_pages", None),
            total_items=response.data.get("total_items", None),
            status_code=response.status_code,
        )

    if response_func == auth_api_response:
        return response_func(
            token=response.data.get("token", None),
            user=response.data.get("user", None),
            errors=response.data.get("errors", None),
            status_code=response.status_code,
        )

    if response_func == batch_api_response:
        return response_func(
            results=response.data.get("batch_results", []),
            errors=response.data.get("errors", None),
            status_code=response.status_code,
        )

    return response_func(data=response.data, status_code=response.status_code)


# Base decorator for formatting responses
def response_decorator(response_func: ResponseFuncType) -> Callable:
    """Wrap a view and apply the selected response formatter.

    Both synchronous and asynchronous views retain their original
    execution model; async views are awaited before their responses are
    formatted.

    """

    def decorator(func: Callable) -> Callable:
        if iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                response = await func(*args, **kwargs)
                return _format_response(response, response_func)

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            response = func(*args, **kwargs)
            return _format_response(response, response_func)

        return sync_wrapper

    return decorator


# Decorator for general API response
def format_api_response(func: Callable) -> Callable:
    """Apply the general API response format using ``api_response``."""
    return response_decorator(api_response)(func)


# Decorator for paginated API response
def format_paginated_response(func: Callable) -> Callable:
    """Apply the paginated API response format."""
    return response_decorator(paginated_api_response)(func)


# Decorator for error API response
def format_error_response(func: Callable) -> Callable:
    """Apply the error API response format."""
    return response_decorator(error_api_response)(func)


# Decorator for minimal success response
def format_minimal_success_response(func: Callable) -> Callable:
    """Apply the minimal success API response format."""
    return response_decorator(minimal_success_response)(func)


# Decorator for batch operation response
def format_batch_response(func: Callable) -> Callable:
    """Apply the batch operation response format."""
    return response_decorator(batch_api_response)(func)


# Decorator for auth response (authentication)
def format_auth_response(func: Callable) -> Callable:
    """Apply the authentication response format."""
    return response_decorator(auth_api_response)(func)
