from functools import wraps
from typing import Any, Callable

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


# Base decorator for formatting responses
def response_decorator(response_func: ResponseFuncType) -> Callable:
    """A base decorator that wraps a given view function and modifies its
    response based on the specified response function (e.g., api_response,
    paginated_api_response, etc.).

    Args:
        response_func: A response function (e.g., api_response) that returns a DRF Response object.

    Returns:
        A wrapped function that applies the response function to the view's response.

    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Response:
            # Call the original view function
            response = func(*args, **kwargs)

            # If the response is a DRF Response, process it with the correct response function
            if isinstance(response, Response):
                # Handle minimal_success_response separately as it does not take `data`
                if response_func == minimal_success_response:
                    return response_func(status_code=response.status_code)

                # Handle error_api_response (no `data`, only errors)
                if response_func == error_api_response:
                    return response_func(
                        message=response.data.get("message", "An error occurred"),
                        errors=response.data.get("errors", None),
                        error_code=response.data.get("error_code", None),
                        status_code=response.status_code,
                    )

                # Handle paginated_api_response with pagination info
                if response_func == paginated_api_response:
                    return response_func(
                        data=response.data.get("data", None),
                        page=response.data.get("page", None),
                        total_pages=response.data.get("total_pages", None),
                        total_items=response.data.get("total_items", None),
                        status_code=response.status_code,
                    )

                # Handle auth_api_response (token and user)
                if response_func == auth_api_response:
                    return response_func(
                        token=response.data.get("token", None),
                        user=response.data.get("user", None),
                        errors=response.data.get("errors", None),
                        status_code=response.status_code,
                    )

                # Handle batch_api_response (with batch results)
                if response_func == batch_api_response:
                    return response_func(
                        results=response.data.get("batch_results", []),
                        errors=response.data.get("errors", None),
                        status_code=response.status_code,
                    )

                # Default handler for other cases (uses `data` and `status_code`)
                return response_func(
                    data=response.data, status_code=response.status_code
                )

            # Return the original response if it's not a DRF Response object
            return response

        return wrapper

    return decorator


# Decorator for general API response
def format_api_response(func: Callable) -> Callable:
    """A decorator that applies the general API response format using
    `api_response`.

    Args:
        func: The view function to be wrapped.

    Returns:
        The wrapped function with the API response format applied.

    """
    return response_decorator(api_response)(func)


# Decorator for paginated API response
def format_paginated_response(func: Callable) -> Callable:
    """A decorator that applies the paginated API response format using
    `paginated_api_response`.

    Args:
        func: The view function to be wrapped.

    Returns:
        The wrapped function with the paginated response format applied.

    """
    return response_decorator(paginated_api_response)(func)


# Decorator for error API response
def format_error_response(func: Callable) -> Callable:
    """A decorator that applies the error API response format using
    `error_api_response`.

    Args:
        func: The view function to be wrapped.

    Returns:
        The wrapped function with the error response format applied.

    """
    return response_decorator(error_api_response)(func)


# Decorator for minimal success response
def format_minimal_success_response(func: Callable) -> Callable:
    """A decorator that applies the minimal success API response format using
    `minimal_success_response`.

    Args:
        func: The view function to be wrapped.

    Returns:
        The wrapped function with the minimal success response format applied.

    """
    return response_decorator(minimal_success_response)(func)


# Decorator for batch operation response
def format_batch_response(func: Callable) -> Callable:
    """A decorator that applies the batch operation response format using
    `batch_api_response`.

    Args:
        func: The view function to be wrapped.

    Returns:
        The wrapped function with the batch operation response format applied.

    """
    return response_decorator(batch_api_response)(func)


# Decorator for auth response (authentication)
def format_auth_response(func: Callable) -> Callable:
    """A decorator that applies the authentication response format using
    `auth_api_response`.

    Args:
        func: The view function to be wrapped.

    Returns:
        The wrapped function with the auth response format applied.

    """
    return response_decorator(auth_api_response)(func)
