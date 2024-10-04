import sys
import pytest
from rest_framework.response import Response
from rest_framework import status
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from typing import Dict, Callable
from response_shaper.decorators import (
    format_api_response,
    format_paginated_response,
    format_error_response,
    format_minimal_success_response,
    format_batch_response,
    format_auth_response,
    response_decorator,
)
from response_shaper.responses import api_response

pytestmark = [
    pytest.mark.decorators,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestResponseDecorators:
    """
    Class to test response decorators and ensure they properly modify view function responses.
    """

    def test_return_original_response(self, non_response_view: Callable) -> None:
        """
        Test that the decorator returns the original non-Response object as-is.

        :param non_response_view: Fixture for a mock view function that returns a non-Response object.
        """
        decorated_view = response_decorator(api_response)(non_response_view)
        response = decorated_view()

        # Ensure that the original response (which is not a DRF Response) is returned unchanged
        assert isinstance(response, dict)
        assert response["message"] == "This is not a Response object"

    def test_format_api_response(self, mock_view: Callable) -> None:
        """
        Test that the format_api_response decorator applies the correct formatting.

        :param mock_view: Fixture for a mock view function.
        """
        decorated_view = format_api_response(mock_view)
        response = decorated_view()

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert response.data["data"]["key"] == "value"

    def test_format_paginated_response(self, mock_paginated_view: Callable) -> None:
        """
        Test that the format_paginated_response decorator applies the correct formatting for paginated data.

        :param mock_paginated_view: Fixture for a mock paginated view function.
        """
        decorated_view = format_paginated_response(mock_paginated_view)
        response = decorated_view()

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert response.data["pagination"]["page"] == 1
        assert response.data["pagination"]["total_pages"] == 5
        assert response.data["pagination"]["total_items"] == 50

    def test_format_error_response(self, error_view: Callable) -> None:
        """
        Test that the format_error_response decorator applies error formatting correctly.
        """

        decorated_view = format_error_response(error_view)
        response = decorated_view()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"
        assert response.data["message"] == "Validation error"
        assert response.data["errors"]["field"] == "required"

    def test_format_minimal_success_response(self, success_view: Callable) -> None:
        """
        Test that the format_minimal_success_response decorator applies the minimal success formatting.
        """

        decorated_view = format_minimal_success_response(success_view)
        response = decorated_view()

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert "data" not in response.data

    def test_format_batch_response(self, batch_view: Callable) -> None:
        """
        Test that the format_batch_response decorator applies the correct formatting for batch operations.

        :param batch_view: Fixture for a mock batch view function.
        """
        decorated_view = format_batch_response(batch_view)
        response = decorated_view()

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert len(response.data["batch_results"]) == 2
        assert response.data["batch_results"][1]["status"] == "failed"

    def test_format_auth_response(self, auth_view: Callable) -> None:
        """
        Test that the format_auth_response decorator applies the correct formatting for auth-related responses.

        :param auth_view: Fixture for a mock auth view function.
        """
        decorated_view = format_auth_response(auth_view)
        response = decorated_view()

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert response.data["token"] == "example-token"
        assert response.data["user"]["username"] == "testuser"
