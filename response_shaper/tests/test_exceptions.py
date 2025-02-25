import sys
import json

import pytest
from django.core.exceptions import (
    ObjectDoesNotExist,
    FieldDoesNotExist,
    MultipleObjectsReturned,
    SuspiciousOperation,
    DisallowedHost,
    DisallowedRedirect,
    EmptyResultSet,
    FieldError,
    BadRequest,
    PermissionDenied,
    MiddlewareNotUsed,
    ImproperlyConfigured,
    ValidationError,
)
from django.db import (
    IntegrityError,
    ProgrammingError,
    OperationalError,
    DataError,
    InternalError,
    DatabaseError,
)
from django.conf import settings
from django.http import JsonResponse

from response_shaper.exceptions import ExceptionHandler
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.exceptions,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestExceptionHandler:
    """Test suite for the ExceptionHandler class."""

    def parse_json_response(self, response: JsonResponse) -> dict:
        """
        Helper method to parse the content of a JsonResponse.

        :param response: The response object to parse.
        :return: The parsed content as a Python dictionary.
        """
        return json.loads(response.content.decode("utf-8"))

    @pytest.mark.parametrize(
        "exception, expected_status_code, expected_error_message",
        [
            # Not Found Exceptions
            (ObjectDoesNotExist("Object not found"), 404, "Object not found"),
            (FieldDoesNotExist("Field does not exist"), 404, "Field does not exist"),
            (EmptyResultSet("No results found"), 404, "No results found"),
            # Bad Request Exceptions
            (
                MultipleObjectsReturned("Multiple objects returned"),
                400,
                "Multiple objects returned",
            ),
            (
                SuspiciousOperation("Suspicious operation detected"),
                400,
                "Suspicious operation detected",
            ),
            (DisallowedHost("Invalid host header"), 400, "Invalid host header"),
            (DisallowedRedirect("Disallowed redirect"), 400, "Disallowed redirect"),
            (BadRequest("Bad request"), 400, "Bad request"),
            # Permission Issues
            (PermissionDenied("Permission denied"), 403, "Permission denied"),
            # Configuration & Middleware Errors
            (
                MiddlewareNotUsed("Middleware not used"),
                500,
                "Internal Server Error",
            ),
            (
                ImproperlyConfigured("Improperly configured"),
                500,
                "Internal Server Error",
            ),
            # Field & Validation Errors
            (FieldError("Field error"), 400, "Field error"),
            # Database Errors
            (IntegrityError("Integrity error"), 400, "A Database Error Occurred"),
            (ProgrammingError("Programming error"), 500, "A Database Error Occurred"),
            (OperationalError("Operational error"), 503, "A Database Error Occurred"),
            (DataError("Data error"), 400, "A Database Error Occurred"),
            (InternalError("Internal error"), 500, "A Database Error Occurred"),
            (DatabaseError("Database error"), 500, "A Database Error Occurred"),
        ],
    )
    def test_handle_exceptions(
        self, exception, expected_status_code, expected_error_message
    ):
        """Test that the ExceptionHandler correctly handles various exceptions.

        Args:
            exception (Exception): The exception to handle.
            expected_status_code (int): The expected HTTP status code.
            expected_error_message (str or dict): The expected error message.
        """
        response = ExceptionHandler.handle(exception)
        response_data = self.parse_json_response(response)

        assert response.status_code == expected_status_code
        assert response_data["status"] is False
        assert response_data["status_code"] == expected_status_code
        assert response_data["error"] == expected_error_message
        assert response_data["data"] == {}

    def test_extract_first_error(self):
        """Test the extract_first_error method with various data structures."""
        # Test with a string
        assert ExceptionHandler.extract_first_error("Error message") == "Error message"

        # Test with a list
        assert (
            ExceptionHandler.extract_first_error(["First error", "Second error"])
            == "First error"
        )

        # Test with a dictionary
        assert ExceptionHandler.extract_first_error({"field": ["Invalid value"]}) == "Invalid value"

        # Test with nested structures
        assert ExceptionHandler.extract_first_error(
            {"field": [{"nested": "Invalid value"}]}
        ) == "Invalid value"

    def test_get_detailed_error_info(self):
        """Test the _get_detailed_error_info method in debug mode."""
        settings.DEBUG = True
        exception = ValueError("Test error")
        error_detail = ExceptionHandler._get_detailed_error_info(exception)

        assert error_detail["message"] == "Internal Server Error: Test error"
        assert error_detail["type"] == "ValueError"

    def test_get_detailed_error_info_no_debug(self):
        """Test the _get_detailed_error_info method when debug mode is off."""
        settings.DEBUG = False
        exception = ValueError("Test error")
        error_detail = ExceptionHandler._get_detailed_error_info(exception)

        assert error_detail["message"] == "Internal Server Error: Test error"
        assert error_detail["type"] == "ValueError"
        assert error_detail["traceback"] is None

    def test_build_error_response(self):
        """Test the build_error_response method."""
        response = ExceptionHandler.build_error_response(400, "Bad request")
        response_data = self.parse_json_response(response)

        assert response.status_code == 400
        assert response_data == {
            "status": False,
            "status_code": 400,
            "error": "Bad request",
            "data": {},
        }

    def test_unexpected_exception(self):
        """Test that unexpected exceptions are handled with a 500 status code."""
        exception = Exception("Unexpected error")
        response = ExceptionHandler.handle(exception)
        response_data = self.parse_json_response(response)

        assert response.status_code == 500
        assert response_data["status"] is False
        assert response_data["status_code"] == 500
        assert response_data["error"] == "Internal Server Error"
        assert response_data["data"] == {}

    def test_subclass_based_exceptions(self):
        """Test that subclass-based exceptions are handled correctly by the fallback logic."""

        # Create a custom exception that inherits from a handled exception
        class CustomDatabaseError(DatabaseError):
            pass

        class CustomValidationError(ValidationError):
            pass

        # Test with a custom database error
        custom_db_error = CustomDatabaseError("Custom database error")
        response = ExceptionHandler.handle(custom_db_error)
        response_data = self.parse_json_response(response)

        assert response.status_code == 500
        assert response_data["status"] is False
        assert response_data["status_code"] == 500
        assert response_data["error"] == "A Database Error Occurred"
        assert response_data["data"] == {}

        # Test with a custom validation error
        custom_validation_error = CustomValidationError({"field": ["Invalid value"]})
        response = ExceptionHandler.handle(custom_validation_error)
        response_data = self.parse_json_response(response)

        assert response.status_code == 400
        assert response_data["status"] is False
        assert response_data["status_code"] == 400
        assert response_data["error"] is not None
        assert response_data["data"] == {}
