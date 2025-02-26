from asyncio import iscoroutinefunction

import pytest
import json
import sys
from unittest.mock import patch, Mock
from django.http import JsonResponse, HttpResponse, HttpRequest, HttpResponseBase
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.test import RequestFactory

from response_shaper.exceptions import ExceptionHandler
from response_shaper.middleware import DynamicResponseMiddleware, BaseMiddleware
from response_shaper.settings.conf import response_shaper_config
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from typing import Dict, Callable, List

pytestmark = [
    pytest.mark.middleware,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestBaseMiddleware:
    """
    Test suite for the BaseMiddleware class.
    """

    def test_sync_mode(self) -> None:
        """
        Test that the middleware correctly identifies and handles synchronous requests.
        This test verifies that when the `get_response` function is synchronous,
        the middleware calls the `__sync_call__` method.
        """
        # Mock synchronous get_response
        mock_get_response = Mock(spec=Callable[[HttpRequest], HttpResponseBase])

        # Create an instance of the middleware
        middleware = BaseMiddleware(mock_get_response)

        # Ensure that it is in synchronous mode
        assert not iscoroutinefunction(middleware.get_response)
        assert not middleware.async_mode

        # Test that calling the middleware raises NotImplementedError (since __sync_call__ is not implemented)
        with pytest.raises(
            NotImplementedError, match="__sync_call__ must be implemented by subclass"
        ):
            request = HttpRequest()
            middleware(request)

    @pytest.mark.asyncio
    async def test_async_mode(self) -> None:
        """
        Test that the middleware correctly identifies and handles asynchronous requests.
        This test verifies that when the `get_response` function is asynchronous,
        the middleware calls the `__acall__` method.
        """

        # Mock asynchronous get_response
        async def mock_get_response(request: HttpRequest) -> HttpResponseBase:
            return Mock(spec=HttpResponseBase)

        # Create an instance of the middleware
        middleware = BaseMiddleware(mock_get_response)

        # Ensure that it is in asynchronous mode
        assert iscoroutinefunction(middleware.get_response)
        assert middleware.async_mode

        # Test that calling the middleware raises NotImplementedError (since __acall__ is not implemented)
        with pytest.raises(
            NotImplementedError, match="__acall__ must be implemented by subclass"
        ):
            request = HttpRequest()
            await middleware(request)


@pytest.mark.django_db
class TestDynamicResponseMiddleware:
    """
    Test cases for the DynamicResponseMiddleware.
    """

    def parse_json_response(self, response: HttpResponse) -> dict:
        """
        Helper method to parse the content of a JsonResponse.

        :param response: The response object to parse.
        :return: The parsed content as a Python dictionary.
        """
        return json.loads(response.content.decode("utf-8"))

    def test_success_response(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that the middleware correctly processes a successful response.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """
        request = request_factory.get("/api/test/")
        middleware = DynamicResponseMiddleware(get_response)

        # Call the middleware
        response = middleware(request)
        response_data = self.parse_json_response(response)

        # Ensure the response is structured correctly
        assert response.status_code == 200
        assert response_data == {
            "status": True,
            "status_code": 200,
            "error": None,
            "data": {"key": "value"},
        }

    def test_error_response(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that the middleware correctly processes an error response.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """

        def error_response(request):
            return JsonResponse({"error": "Some error occurred"}, status=400)

        request = request_factory.get("/api/test/")
        middleware = DynamicResponseMiddleware(error_response)

        # Call the middleware
        response = middleware(request)
        response_data = self.parse_json_response(response)

        # Ensure the response is structured correctly
        assert response.status_code == 400
        assert response_data == {
            "status": False,
            "status_code": 400,
            "error": "Some error occurred",
            "data": {},
        }

    def test_excluded_paths(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that excluded paths are skipped by the middleware.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """
        # Mock the config to include an excluded path
        with patch.object(
            response_shaper_config, "excluded_paths", new=["/api/excluded/"]
        ):
            request = request_factory.get("/api/excluded/")
            middleware = DynamicResponseMiddleware(get_response)

            # Call the middleware for an excluded path
            response = middleware(request)
            response_data = self.parse_json_response(response)

            # Ensure that the middleware does not alter the response
            assert response.status_code == 200
            assert response_data == {"key": "value"}

    def test_process_exception(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that the middleware processes exceptions correctly.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """
        request = request_factory.get("/api/test/")
        middleware = DynamicResponseMiddleware(get_response)

        # Simulate an IntegrityError exception
        with patch.object(ExceptionHandler, "build_error_response") as mock_build_error:
            mock_build_error.return_value = JsonResponse(
                {
                    "status": False,
                    "status_code": 400,
                    "error": "Integrity Error",
                    "data": {},
                },
                status=400,
            )

            # Call the process_exception method directly
            response = middleware.process_exception(
                request, IntegrityError("Integrity Error")
            )
            response_data = self.parse_json_response(response)
            assert response.status_code == 400
            assert response_data == {
                "status": False,
                "status_code": 400,
                "error": "Integrity Error",
                "data": {},
            }

            # test skip shaping when debug mode is true
            middleware.debug = True
            response = middleware.process_exception(
                request, IntegrityError("Integrity Error")
            )
            response is None

    def test_custom_success_handler(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that a custom success handler is used.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """

        # Define a custom success handler that returns a different structure
        def custom_success_handler(response):
            return JsonResponse(
                {"custom": "success", "status_code": response.status_code},
                status=response.status_code,
            )

        # Patch the import_string function to return the custom success handler
        with patch(
            "django.utils.module_loading.import_string",
            return_value=custom_success_handler,
        ):
            request = request_factory.get("/api/test/")
            middleware = DynamicResponseMiddleware(get_response)

            # Call the middleware with a successful response
            response = middleware(request)
            response_data = self.parse_json_response(response)

            # Check that the custom handler's response is returned
            assert response.status_code == 200
            assert response_data == {"custom": "success", "status_code": 200}

            response.data = {"key": "value"}
            response = middleware._default_success_handler(response)
            response_data = self.parse_json_response(response)
            assert response_data["data"] == {"key": "value"}

    def test_custom_error_handler(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that a custom error handler is used.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """

        def error_response(request):
            return JsonResponse({"error": "Some error occurred"}, status=400)

        # Define a custom error handler that returns a different structure
        def custom_error_handler(response):
            return JsonResponse(
                {"custom": "error", "status_code": response.status_code},
                status=response.status_code,
            )

        # Patch the import_string function to return the custom error handler
        with patch(
            "django.utils.module_loading.import_string",
            return_value=custom_error_handler,
        ):
            request = request_factory.get("/api/test/")
            middleware = DynamicResponseMiddleware(error_response)

            # Call the middleware with an error response
            response = middleware(request)
            response_data = self.parse_json_response(response)

            # Check that the custom handler's response is returned
            assert response.status_code == 400
            assert response_data == {"custom": "error", "status_code": 400}

            response.data = {"key": "value"}
            response = middleware._default_error_handler(response)
            response_data = self.parse_json_response(response)
            assert response_data["error"] == {'key': 'value'}

    def test_process_object_does_not_exist_exception(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that ObjectDoesNotExist exception returns a 404 response.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """
        request = request_factory.get("/api/test/")
        middleware = DynamicResponseMiddleware(get_response)

        # Simulate ObjectDoesNotExist exception
        with patch.object(ExceptionHandler, "build_error_response") as mock_build_error:
            mock_build_error.return_value = JsonResponse(
                {
                    "status": False,
                    "status_code": 404,
                    "error": "Object not found",
                    "data": {},
                },
                status=404,
            )

            response = middleware.process_exception(
                request, ObjectDoesNotExist("Object not found")
            )
            response_data = self.parse_json_response(response)
            assert response.status_code == 404
            assert response_data == {
                "status": False,
                "status_code": 404,
                "error": "Object not found",
                "data": {},
            }

    def test_extract_string_error(self) -> None:
        """
        Test that the middleware correctly extracts a string error message.
        """
        error = "This is an error message"
        result = ExceptionHandler.extract_first_error(error)
        assert result == "This is an error message"

    def test_extract_list_of_errors(self) -> None:
        """
        Test that the middleware correctly extracts the first error from a list of errors.
        """
        errors = ["First error", "Second error"]
        result = ExceptionHandler.extract_first_error(errors)
        assert result == "First error"

    def test_extract_nested_list_of_errors(self) -> None:
        """
        Test that the middleware correctly extracts the first error from a nested list of errors.
        """
        errors = [["Nested error", "Another error"], "Second error"]
        result = ExceptionHandler.extract_first_error(errors)
        assert result == "Nested error"

    def test_extract_dict_of_errors(self) -> None:
        """
        Test that the middleware correctly extracts the first error from a dictionary of errors.
        """
        response_shaper_config.return_dict_error = False
        errors = {"field1": "Field1 error", "field2": "Field2 error"}
        result = ExceptionHandler.extract_first_error(errors)
        assert result == "Field1 error"

    def test_extract_nested_dict_of_errors(self) -> None:
        """
        Test that the middleware correctly extracts the first error from a nested dictionary of errors.
        """
        response_shaper_config.return_dict_error = True
        errors = {"field1": {"subfield": "Subfield error"}, "field2": "Field2 error"}
        result = ExceptionHandler.extract_first_error(errors)
        assert result == {"subfield": "Subfield error"}

    def test_extract_empty_list(self) -> None:
        """
        Test that the middleware correctly handles an empty list of errors.
        """
        errors: List = []
        result = ExceptionHandler.extract_first_error(errors)
        assert result == "[]"

    def test_extract_empty_dict(self) -> None:
        """
        Test that the middleware correctly handles an empty dictionary of errors.
        """
        errors: Dict = {}
        result = ExceptionHandler.extract_first_error(errors)
        assert result == "{}"

    def test_extract_complex_structure(self) -> None:
        """
        Test that the middleware correctly extracts errors from a complex nested structure.
        """
        errors = {
            "field1": [
                {"subfield": ["Subfield error", "Another error"]},
                "Other error",
            ],
            "field2": "Field2 error",
        }
        result = ExceptionHandler.extract_first_error(errors)
        assert result == {"subfield": "Subfield error"}

    def test_skip_non_json_content_type(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that non-JSON responses are skipped by the middleware.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """
        request = request_factory.get("/api/test/")
        response = HttpResponse("<html></html>", content_type="text/html")
        middleware = DynamicResponseMiddleware(get_response)

        processed_response = middleware.process_response(request, response)

        # Ensure the middleware returns the original response for non-JSON content
        assert processed_response.content == response.content
        assert processed_response.status_code == 200

    def test_process_json_response(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that JSON responses are processed correctly by the middleware.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """
        request = request_factory.get("/api/test/")
        response = JsonResponse({"key": "value"})
        middleware = DynamicResponseMiddleware(get_response)

        processed_response = middleware.process_response(request, response)

        # Ensure the middleware processes JSON responses and structures them
        response_data = json.loads(processed_response.content)
        assert response_data["status"] is True
        assert response_data["status_code"] == 200
        assert response_data["data"] == {"key": "value"}
        assert response_data["error"] is None

    def test_process_exception_handling(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that exceptions are handled correctly with a 500 error.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """
        request = request_factory.get("/api/test/")
        exception = Exception("Test exception")
        middleware = DynamicResponseMiddleware(get_response)

        processed_response = middleware.process_exception(request, exception)

        # Ensure a generic 500 error is returned
        response_data = json.loads(processed_response.content)
        assert response_data["status"] is False
        assert response_data["status_code"] == 500
        assert "Internal Server Error" in response_data["error"]

    def test_process_validation_error(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that ValidationError is handled correctly by the middleware.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """
        request = request_factory.get("/api/test/")
        exception = ValidationError({"field": "Field error"})
        middleware = DynamicResponseMiddleware(get_response)

        processed_response = middleware.process_exception(request, exception)

        # Ensure a structured error response for ValidationError
        response_data = json.loads(processed_response.content)
        assert processed_response.status_code == 400
        assert response_data["status"] is False
        assert response_data["status_code"] == 400
        assert response_data["error"] == "{'field': ['Field error']}"

    def test_process_django_errors(
        self, request_factory: RequestFactory, get_response: Callable
    ) -> None:
        """
        Test that Django-specific exceptions (e.g., IntegrityError, ObjectDoesNotExist) are handled correctly.

        :param request_factory: Fixture to generate mock requests.
        :param get_response: Mocked response for testing.
        """
        request = request_factory.get("/api/test/")
        middleware = DynamicResponseMiddleware(get_response)

        # Test IntegrityError handling
        integrity_error = IntegrityError("Integrity error occurred")
        processed_response = middleware.process_exception(request, integrity_error)
        response_data = json.loads(processed_response.content)
        assert processed_response.status_code == 400
        assert response_data["error"] == "A Database Error Occurred"

        # Test ObjectDoesNotExist handling
        object_not_found = ObjectDoesNotExist()
        processed_response = middleware.process_exception(request, object_not_found)
        response_data = json.loads(processed_response.content)
        assert processed_response.status_code == 404
        assert response_data["error"] == "Object not found"

    @pytest.mark.asyncio
    async def test_async_success_response(
        self, request_factory: RequestFactory
    ) -> None:
        """
        Test that the middleware correctly processes an asynchronous successful response.

        :param request_factory: Fixture to generate mock requests.
        """

        # Mock asynchronous get_response
        async def mock_get_response(request: HttpRequest) -> HttpResponseBase:
            return JsonResponse({"key": "value"}, status=200)

        request = request_factory.get("/api/test/")
        middleware = DynamicResponseMiddleware(mock_get_response)

        # Call the middleware
        response = await middleware(request)
        response_data = self.parse_json_response(response)

        # Ensure the response is structured correctly
        assert response.status_code == 200
        assert response_data == {
            "status": True,
            "status_code": 200,
            "error": None,
            "data": {"key": "value"},
        }

    @pytest.mark.asyncio
    async def test_async_error_response(self, request_factory: RequestFactory) -> None:
        """
        Test that the middleware correctly processes an asynchronous error response.

        :param request_factory: Fixture to generate mock requests.
        """

        # Mock asynchronous get_response
        async def mock_get_response(request: HttpRequest) -> HttpResponseBase:
            return JsonResponse({"error": "Some error occurred"}, status=400)

        request = request_factory.get("/api/test/")
        middleware = DynamicResponseMiddleware(mock_get_response)

        # Call the middleware
        response = await middleware(request)
        response_data = self.parse_json_response(response)

        # Ensure the response is structured correctly
        assert response.status_code == 400
        assert response_data == {
            "status": False,
            "status_code": 400,
            "error": "Some error occurred",
            "data": {},
        }

    @pytest.mark.asyncio
    async def test_async_skip_non_json_content_type(
        self, request_factory: RequestFactory
    ) -> None:
        """
        Test that non-JSON responses are skipped by the middleware in async mode.

        :param request_factory: Fixture to generate mock requests.
        """

        # Mock asynchronous get_response
        async def mock_get_response(request: HttpRequest) -> HttpResponseBase:
            return HttpResponse("<html></html>", content_type="text/html")

        request = request_factory.get("/api/test/")
        middleware = DynamicResponseMiddleware(mock_get_response)

        # Call the middleware
        response = await middleware(request)

        # Ensure the middleware returns the original response for non-JSON content
        assert response.content == b"<html></html>"
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html"

    @pytest.mark.asyncio
    async def test_async_excluded_paths(self, request_factory: RequestFactory) -> None:
        """
        Test that excluded paths are skipped by the middleware in async mode.

        :param request_factory: Fixture to generate mock requests.
        """
        # Mock the config to include an excluded path
        with patch.object(
            response_shaper_config, "excluded_paths", new=["/api/excluded/"]
        ):
            # Mock asynchronous get_response
            async def mock_get_response(request: HttpRequest) -> HttpResponseBase:
                return JsonResponse({"key": "value"}, status=200)

            request = request_factory.get("/api/excluded/")
            middleware = DynamicResponseMiddleware(mock_get_response)

            # Call the middleware for an excluded path
            response = await middleware(request)
            response_data = self.parse_json_response(response)

            # Ensure that the middleware does not alter the response
            assert response.status_code == 200
            assert response_data == {"key": "value"}
