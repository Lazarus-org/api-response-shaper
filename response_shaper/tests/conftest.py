import pytest
from response_shaper.tests.setup import configure_django_settings
from rest_framework.test import APIClient
from rest_framework.response import Response
from rest_framework import status
from typing import Callable, Any
from unittest.mock import MagicMock
from django.http import JsonResponse
from response_shaper.middleware import DynamicResponseMiddleware
from django.test import RequestFactory


@pytest.fixture
def api_client() -> APIClient:
    """
    Fixture to initialize the Django REST Framework APIClient for testing.

    :return: An instance of APIClient to make HTTP requests in tests.
    """
    return APIClient()


@pytest.fixture
def mock_view() -> Callable[..., Response]:
    """
    Fixture to return a mock view function for testing.

    :return: A mock view function that returns a Response object.
    """

    def view_func(*args: Any, **kwargs: Any) -> Response:
        return Response({"key": "value"}, status=status.HTTP_200_OK)

    return view_func


@pytest.fixture
def mock_paginated_view() -> Callable[..., Response]:
    """
    Fixture to return a mock view function that simulates a paginated response.

    :return: A mock view function that returns a paginated Response object.
    """

    def view_func(*args: Any, **kwargs: Any) -> Response:
        return Response(
            {
                "data": [{"id": 1}, {"id": 2}],
                "page": 1,
                "total_pages": 5,
                "total_items": 50,
            },
            status=status.HTTP_200_OK,
        )

    return view_func


@pytest.fixture
def success_view() -> Callable[..., Response]:
    """
    Fixture that returns a mock view for testing successful responses.

    :return: A mock view function that returns a minimal success Response.
    """

    def view_func(*args: Any, **kwargs: Any) -> Response:
        return Response({}, status=status.HTTP_200_OK)

    return view_func


@pytest.fixture
def batch_view() -> Callable[..., Response]:
    """
    Fixture that returns a mock view for testing batch response formatting.

    :return: A mock view function that returns a batch Response.
    """

    def view_func(*args: Any, **kwargs: Any) -> Response:
        return Response(
            {
                "batch_results": [
                    {"id": 1, "status": "success"},
                    {"id": 2, "status": "failed"},
                ]
            },
            status=status.HTTP_200_OK,
        )

    return view_func


@pytest.fixture
def auth_view() -> Callable[..., Response]:
    """
    Fixture that returns a mock view for testing authentication responses.

    :return: A mock view function that returns a token and user in the Response.
    """

    def view_func(*args: Any, **kwargs: Any) -> Response:
        return Response(
            {"token": "example-token", "user": {"id": 1, "username": "testuser"}},
            status=status.HTTP_200_OK,
        )

    return view_func


@pytest.fixture
def error_view() -> Callable[..., Response]:
    """
    Fixture that returns a mock view for testing error responses.

    :return: A mock view function that returns a validation error Response.
    """

    def view_func(*args: Any, **kwargs: Any) -> Response:
        return Response(
            {"message": "Validation error", "errors": {"field": "required"}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return view_func


@pytest.fixture
def non_response_view() -> Callable[..., Any]:
    """
    Fixture that returns a mock view function that returns something other than a DRF Response.

    :return: A mock view function that returns a non-Response object.
    """

    def view_func(*args: Any, **kwargs: Any) -> Any:
        return {"message": "This is not a Response object"}

    return view_func


@pytest.fixture
def json_response() -> JsonResponse:
    """
    Fixture to simulate a successful JSON response.

    :return: A JsonResponse object with a success status.
    """
    return JsonResponse({"key": "value"}, status=200)


@pytest.fixture
def error_response() -> JsonResponse:
    """
    Fixture to simulate an error JSON response.

    :return: A JsonResponse object with an error status.
    """
    return JsonResponse({"detail": "Some error occurred"}, status=400)


@pytest.fixture
def middleware() -> DynamicResponseMiddleware:
    """
    Fixture to initialize the DynamicResponseMiddleware for testing.

    :return: An instance of DynamicResponseMiddleware.
    """
    return DynamicResponseMiddleware(get_response=MagicMock())


@pytest.fixture
def request_factory() -> RequestFactory:
    """
    Fixture for Django RequestFactory to simulate requests.

    :return: An instance of RequestFactory for creating mock requests.
    """
    return RequestFactory()


@pytest.fixture
def get_response() -> Callable[[Any], JsonResponse]:
    """
    A mock for the get_response callable passed to middleware.

    :return: A callable that returns a JsonResponse object.
    """

    def mock_response(request: Any) -> JsonResponse:
        return JsonResponse({"key": "value"}, status=200)

    return mock_response
