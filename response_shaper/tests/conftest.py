import pytest
from response_shaper.tests.setup import configure_django_settings
from rest_framework.test import APIClient
from rest_framework.response import Response
from rest_framework import status
from typing import Callable

@pytest.fixture
def api_client() -> APIClient:
    """
    Fixture to initialize the Django REST Framework APIClient for testing.
    
    :return: An instance of APIClient to make HTTP requests in tests.
    """
    return APIClient()



@pytest.fixture
def mock_view() -> Callable:
    """
    Fixture to return a mock view function for testing.
    
    :return: A mock view function that returns a Response object.
    """
    def view_func(*args, **kwargs) -> Response:
        return Response({"key": "value"}, status=status.HTTP_200_OK)
    return view_func


@pytest.fixture
def mock_paginated_view() -> Callable:
    """
    Fixture to return a mock view function that simulates a paginated response.
    
    :return: A mock view function that returns a paginated Response object.
    """
    def view_func(*args, **kwargs) -> Response:
        return Response(
            {
                "data": [{"id": 1}, {"id": 2}], 
                "page": 1, 
                "total_pages": 5, 
                "total_items": 50
            },
            status=status.HTTP_200_OK
        )
    return view_func


@pytest.fixture
def success_view() -> Callable:
    """
    Fixture that returns a mock view for testing successful responses.
    
    :return: A mock view function that returns a minimal success Response.
    """
    def view_func(*args, **kwargs) -> Response:
        return Response({}, status=status.HTTP_200_OK)
    return view_func


@pytest.fixture
def batch_view() -> Callable:
    """
    Fixture that returns a mock view for testing batch response formatting.
    
    :return: A mock view function that returns a batch Response.
    """
    def view_func(*args, **kwargs) -> Response:
        return Response(
            {"batch_results": [{"id": 1, "status": "success"}, {"id": 2, "status": "failed"}]},
            status=status.HTTP_200_OK
        )
    return view_func


@pytest.fixture
def auth_view() -> Callable:
    """
    Fixture that returns a mock view for testing authentication responses.
    
    :return: A mock view function that returns a token and user in the Response.
    """
    def view_func(*args, **kwargs) -> Response:
        return Response(
            {"token": "example-token", "user": {"id": 1, "username": "testuser"}},
            status=status.HTTP_200_OK
        )
    return view_func

@pytest.fixture
def error_view() -> Callable:
    """
    Fixture that returns a mock view for testing error responses.
    
    :return: A mock view function that returns a validation error Response.
    """
    def view_func(*args, **kwargs) -> Response:
        return Response(
            {"message": "Validation error", "errors": {"field": "required"}},
            status=status.HTTP_400_BAD_REQUEST
        )
    return view_func

@pytest.fixture
def non_response_view() -> Callable:
    """
    Fixture that returns a mock view function that returns something other than a DRF Response.
    
    :return: A mock view function that returns a non-Response object.
    """
    def view_func(*args, **kwargs):
        return {"message": "This is not a Response object"}
    return view_func
