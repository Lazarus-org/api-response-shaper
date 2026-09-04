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
from response_shaper.settings.conf import response_shaper_config
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.exceptions,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


def custom_error_extractor(error_data):
    """Test extractor used to verify dotted-path custom extraction."""
    return {"custom": error_data}


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
        assert ExceptionHandler.extract_first_error({"field": ["Invalid value"]}) == {"field": "Invalid value"}

        # Test with nested structures
        assert ExceptionHandler.extract_first_error(
            {"field": [{"nested": "Invalid value"}]}
        ) == {"nested": "Invalid value"}

    def test_extract_error_uses_legacy_first_strategy(self, monkeypatch):
        """The default strategy must preserve the existing package contract."""
        monkeypatch.setattr(response_shaper_config, "error_extraction", "first")
        monkeypatch.setattr(response_shaper_config, "return_dict_error", True)

        errors = {"field1": "Field1 error", "field2": "Field2 error"}

        assert ExceptionHandler.extract_error(errors) == {"field1": "Field1 error"}

    def test_smart_strategy_preserves_flat_structured_error(self, monkeypatch):
        """Smart extraction preserves arbitrary flat machine-readable payloads."""
        monkeypatch.setattr(response_shaper_config, "error_extraction", "smart")
        monkeypatch.setattr(response_shaper_config, "return_dict_error", True)
        error = {
            "kind": "map_bbox_required",
            "message": "geometry_bbox is required for map requests.",
            "parameter": "geometry_bbox",
        }

        assert ExceptionHandler.extract_error(error) == error

    def test_smart_strategy_still_extracts_first_field_error(self, monkeypatch):
        """Smart extraction continues to traverse normal serializer error trees."""
        monkeypatch.setattr(response_shaper_config, "error_extraction", "smart")
        monkeypatch.setattr(response_shaper_config, "return_dict_error", True)
        errors = {
            "geometry_bbox": ["This field is required."],
            "zoom": ["Invalid zoom."],
        }

        assert ExceptionHandler.extract_error(errors) == {
            "geometry_bbox": "This field is required."
        }

    def test_smart_strategy_preserves_nested_structured_error(self, monkeypatch):
        """Structured payloads remain atomic even when nested in an error tree."""
        monkeypatch.setattr(response_shaper_config, "error_extraction", "smart")
        monkeypatch.setattr(response_shaper_config, "return_dict_error", True)
        structured_error = {
            "error_id": "map_bbox_required",
            "text": "geometry_bbox is required for map requests.",
            "parameter": "geometry_bbox",
        }
        errors = {"map": [structured_error]}

        assert ExceptionHandler.extract_error(errors) == structured_error

    def test_full_strategy_preserves_complete_error_payload(self, monkeypatch):
        """Full extraction returns the original error payload without traversal."""
        monkeypatch.setattr(response_shaper_config, "error_extraction", "full")
        errors = {
            "geometry_bbox": ["This field is required."],
            "zoom": ["Invalid zoom."],
        }

        assert ExceptionHandler.extract_error(errors) is errors

    def test_custom_error_extractor_from_dotted_path(self, monkeypatch):
        """Consumers can replace extraction with their own callable."""
        monkeypatch.setattr(
            response_shaper_config,
            "error_extraction",
            "response_shaper.tests.test_exceptions.custom_error_extractor",
        )
        errors = {"field": ["Invalid value"]}

        assert ExceptionHandler.extract_error(errors) == {"custom": errors}

    def test_invalid_custom_error_extractor_path(self, monkeypatch):
        """Invalid dotted paths fail with a Django configuration error."""
        monkeypatch.setattr(
            response_shaper_config,
            "error_extraction",
            "response_shaper.tests.constants.missing_extractor",
        )

        with pytest.raises(ImproperlyConfigured):
            ExceptionHandler.extract_error({"field": ["Invalid value"]})

    def test_custom_error_extractor_must_be_callable(self, monkeypatch):
        """A dotted path must resolve to a callable, not just any object."""
        monkeypatch.setattr(
            response_shaper_config,
            "error_extraction",
            "response_shaper.tests.constants.PYTHON_VERSION",
        )

        with pytest.raises(ImproperlyConfigured):
            ExceptionHandler.extract_error({"field": ["Invalid value"]})

    @pytest.mark.parametrize(
        "error",
        [[], {}, 42, 3.14, True, None],
    )
    def test_smart_strategy_preserves_empty_and_scalar_values(self, monkeypatch, error):
        """Smart extraction preserves terminal values instead of coercing them."""
        monkeypatch.setattr(response_shaper_config, "error_extraction", "smart")

        assert ExceptionHandler.extract_error(error) is error

    def test_smart_strategy_preserves_non_string_value_inside_error_tree(
        self, monkeypatch
    ):
        """Smart traversal selects the first leaf without changing its type."""
        monkeypatch.setattr(response_shaper_config, "error_extraction", "smart")
        monkeypatch.setattr(response_shaper_config, "return_dict_error", False)

        assert ExceptionHandler.extract_error({"field": [42]}) == 42

    def test_legacy_first_strategy_still_coerces_terminal_values(self, monkeypatch):
        """The compatibility strategy keeps the pre-existing string coercion."""
        monkeypatch.setattr(response_shaper_config, "error_extraction", "first")

        assert ExceptionHandler.extract_error(42) == "42"
        assert ExceptionHandler.extract_error({}) == "{}"

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
