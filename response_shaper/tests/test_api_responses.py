import sys

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from response_shaper.responses import (
    api_response,
    auth_api_response,
    batch_api_response,
    error_api_response,
    hateoas_api_response,
    metadata_api_response,
    minimal_success_response,
    multi_resource_response,
    paginated_api_response,
    rate_limited_response,
    redirect_response,
    service_availability_response,
    upload_progress_response,
)
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.api_responses,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestAPIResponses:
    """
    Class to test different types of API response functions.
    """

    def test_hateoas_api_response(self, api_client: APIClient) -> None:
        """
        Test the hateoas_api_response function.

        :param api_client: Fixture for APIClient.
        """
        links = {
            "self": "https://api.example.com/resource/1",
            "related": "https://api.example.com/resource/1/related",
        }
        response = hateoas_api_response(
            success=True, message="Operation successful", data={"id": 1}, links=links
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert response.data["message"] == "Operation successful"
        assert response.data["links"]["self"] == "https://api.example.com/resource/1"
        assert (
            response.data["links"]["related"]
            == "https://api.example.com/resource/1/related"
        )

    def test_multi_resource_response(self, api_client: APIClient) -> None:
        """
        Test the multi_resource_response function.

        :param api_client: Fixture for APIClient.
        """
        resources = [{"id": 1, "name": "Resource 1"}, {"id": 2, "name": "Resource 2"}]
        response = multi_resource_response(
            success=True, message="Multiple resources fetched", resources=resources
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert response.data["resources"] == resources
        assert response.data["message"] == "Multiple resources fetched"

    def test_api_response(self, api_client: APIClient) -> None:
        """
        Test the basic api_response function.

        :param api_client: Fixture for APIClient.
        """
        response = api_response(
            success=True,
            message="Operation successful",
            data={"key": "value"},
            errors=None,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert response.data["message"] == "Operation successful"
        assert response.data["data"] == {"key": "value"}

    def test_paginated_api_response(self, api_client: APIClient) -> None:
        """
        Test the paginated_api_response function.

        :param api_client: Fixture for APIClient.
        """
        response = paginated_api_response(
            success=True,
            message="Fetched successfully",
            data=[{"id": 1}, {"id": 2}],
            page=1,
            total_pages=5,
            total_items=50,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert response.data["pagination"]["page"] == 1
        assert response.data["pagination"]["total_pages"] == 5

    def test_error_api_response(self, api_client: APIClient) -> None:
        """
        Test the error_api_response function.

        :param api_client: Fixture for APIClient.
        """
        response = error_api_response(
            message="Validation error",
            errors={"field": "This field is required"},
            error_code="ERR01",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"
        assert response.data["message"] == "Validation error"
        assert response.data["errors"]["field"] == "This field is required"
        assert response.data["error_code"] == "ERR01"

    def test_minimal_success_response(self, api_client: APIClient) -> None:
        """
        Test the minimal_success_response function.

        :param api_client: Fixture for APIClient.
        """
        response = minimal_success_response(message="Request successful")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert response.data["message"] == "Request successful"

    def test_metadata_api_response(self, api_client: APIClient) -> None:
        """
        Test the metadata_api_response function.

        :param api_client: Fixture for APIClient.
        """
        response = metadata_api_response(
            success=True,
            message="Operation completed",
            data={"key": "value"},
            processing_time="50ms",
            api_version="2.0",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["meta"]["processing_time"] == "50ms"
        assert response.data["meta"]["api_version"] == "2.0"

    def test_batch_api_response(self, api_client: APIClient) -> None:
        """
        Test the batch_api_response function.

        :param api_client: Fixture for APIClient.
        """
        results = [{"id": 1, "status": "success"}, {"id": 2, "status": "failed"}]
        response = batch_api_response(
            success=True, message="Batch processed", results=results
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert response.data["batch_results"] == results

    def test_auth_api_response(self, api_client: APIClient) -> None:
        """
        Test the auth_api_response function.

        :param api_client: Fixture for APIClient.
        """
        response = auth_api_response(
            success=True,
            message="Login successful",
            token="example-token",
            user={"id": 1, "username": "user1"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["token"] == "example-token"
        assert response.data["user"]["username"] == "user1"

    def test_rate_limited_response(self, api_client: APIClient) -> None:
        """
        Test the rate_limited_response function.

        :param api_client: Fixture for APIClient.
        """
        response = rate_limited_response(message="Too many requests", retry_after=60)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.data["message"] == "Too many requests"
        assert response.data["retry_after"] == 60

    def test_upload_progress_response(self, api_client: APIClient) -> None:
        """
        Test the upload_progress_response function.

        :param api_client: Fixture for APIClient.
        """
        response = upload_progress_response(
            success=True, message="Upload in progress", progress=50
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["progress"] == 50

    def test_service_availability_response(self, api_client: APIClient) -> None:
        """
        Test the service_availability_response function.

        :param api_client: Fixture for APIClient.
        """
        response = service_availability_response(
            available=True, message="Service is running", service_name="Database"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "available"
        assert response.data["service_name"] == "Database"

    def test_redirect_response(self, api_client: APIClient) -> None:
        """
        Test the redirect_response function.

        :param api_client: Fixture for APIClient.
        """
        response = redirect_response(
            message="Resource moved", redirect_url="https://new-url.com"
        )
        assert response.status_code == status.HTTP_302_FOUND
        assert response.data["redirect_url"] == "https://new-url.com"
