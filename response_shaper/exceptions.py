from typing import Any, Dict, Union

from django.conf import settings
from django.core.exceptions import (
    BadRequest,
    DisallowedHost,
    DisallowedRedirect,
    EmptyResultSet,
    FieldDoesNotExist,
    FieldError,
    ImproperlyConfigured,
    MiddlewareNotUsed,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    PermissionDenied,
    SuspiciousOperation,
    ValidationError,
)
from django.db import (
    DatabaseError,
    DataError,
    IntegrityError,
    InternalError,
    OperationalError,
    ProgrammingError,
)
from django.http import JsonResponse


class ExceptionHandler:
    """Handles exception responses consistently across the application.

    This class provides a centralized way to handle exceptions and
    return consistent JSON error responses. It maps specific exceptions
    to appropriate HTTP status codes and messages, and includes detailed
    error information in debug mode.

    """

    @staticmethod
    def build_error_response(status_code: int, message: str) -> JsonResponse:
        """Helper method to build error responses consistently.

        Args:
            status_code (int): The HTTP status code for the error response.
            message (str): The error message or data to be included in the response.

        Returns:
            JsonResponse: A JSON response containing the error details, structured as:
                {
                    "status": False,
                    "status_code": <status_code>,
                    "error": <message>,
                    "data": {}
                }

        """
        return JsonResponse(
            {"status": False, "status_code": status_code, "error": message, "data": {}},
            status=status_code,
        )

    @classmethod
    def handle(cls, exception: Exception) -> JsonResponse:
        """Processes exceptions and returns structured error responses.

        This method maps specific exceptions to appropriate HTTP status codes
        and messages. It uses a dictionary of exception handlers to determine
        the appropriate response. If the exception is not explicitly handled,
        it falls back to a generic 500 Internal Server Error response.

        Args:
            exception (Exception): The exception that was raised.

        Returns:
            JsonResponse: A JSON response containing the error details.

        """

        # pylint: disable=W0108
        # Helper functions for response consistency
        def bad_request(msg="Bad request"):
            """Handles 400 Bad Request errors, including detailed messages in
            debug mode."""
            error_message = (
                cls._get_detailed_error_info(exception) if settings.DEBUG else msg
            )
            return cls.build_error_response(400, error_message)

        def not_found(msg="Resource not found"):
            """Handles 404 Not Found errors."""
            return cls.build_error_response(404, msg)

        def server_error(exc):
            """Handles 500 Internal Server Errors, including detailed messages
            in debug mode."""
            error_message = (
                cls._get_detailed_error_info(exc)
                if settings.DEBUG
                else "Internal Server Error"
            )
            return cls.build_error_response(500, error_message)

        def db_error(exc, status=500):
            """Handles database errors, including detailed messages in debug
            mode."""
            error_message = (
                cls._get_detailed_error_info(exc)
                if settings.DEBUG
                else "A Database Error Occurred"
            )
            return cls.build_error_response(status, error_message)

        # Exception mapping dictionary
        exception_handlers = {
            # Not Found
            FieldDoesNotExist: lambda e: not_found("Field does not exist"),
            ObjectDoesNotExist: lambda e: not_found("Object not found"),
            EmptyResultSet: lambda e: not_found("No results found"),
            # Bad Request
            MultipleObjectsReturned: lambda e: bad_request("Multiple objects returned"),
            SuspiciousOperation: lambda e: bad_request("Suspicious operation detected"),
            DisallowedHost: lambda e: bad_request("Invalid host header"),
            DisallowedRedirect: lambda e: bad_request("Disallowed redirect"),
            BadRequest: lambda e: bad_request(),
            # Permission Issues
            PermissionDenied: lambda e: cls.build_error_response(
                403, "Permission denied"
            ),
            # Configuration & Middleware Errors
            MiddlewareNotUsed: lambda e: server_error(e),
            ImproperlyConfigured: lambda e: server_error(e),
            # Field & Validation Errors
            FieldError: lambda e: bad_request("Field error"),
            ValidationError: lambda e: bad_request(cls.extract_first_error(e)),
            # Database Errors
            IntegrityError: lambda e: db_error(e, 400),
            ProgrammingError: lambda e: db_error(e),
            OperationalError: lambda e: db_error(e, 503),
            DataError: lambda e: db_error(e, 400),
            InternalError: lambda e: db_error(e),
            DatabaseError: lambda e: db_error(e),
        }

        # Use explicit lookup first
        handler = exception_handlers.get(type(exception))
        if handler:
            return handler(exception)

        # Fallback for subclass-based exceptions
        for exc_class, handler in exception_handlers.items():
            if isinstance(exception, exc_class):
                return handler(exception)

        # Catch-all for unexpected exceptions
        message = (
            cls._get_detailed_error_info(exception)
            if settings.DEBUG
            else "Internal Server Error"
        )
        return cls.build_error_response(500, message)

    @staticmethod
    def extract_first_error(error_data: Any) -> Union[Any, Dict]:
        """Extract the first error message from various data structures (dict,
        list, string). Stops at the first error encountered.

        This method is useful for extracting the first error message from
        complex error data structures, such as those returned by Django's
        validation framework.

        Args:
            error_data (Any): The error data structure, which can be a string,
                list, or dictionary.

        Returns:
            Union[str, dict]: The extracted error message or structure. If the
                input is a list, it returns the first element. If the input is
                a dictionary, it returns the first key-value pair. If the input
                is a string, it returns the string itself.

        """
        if isinstance(error_data, str):
            return error_data
        if isinstance(error_data, list) and error_data:
            return ExceptionHandler.extract_first_error(error_data[0])
        if isinstance(error_data, dict):
            for value in error_data.values():
                return ExceptionHandler.extract_first_error(value)
        return str(error_data)

    @staticmethod
    def _get_detailed_error_info(exception: Exception) -> Dict:
        """Extract detailed error information including the exception message
        and traceback.

        This method is used to provide detailed error information in debug mode,
        including the exception type, message, and traceback.

        Args:
            exception (Exception): The exception that occurred.

        Returns:
            dict: A dictionary containing the error details, structured as:
                {
                    "message": <exception_message>,
                    "type": <exception_type>,
                    "traceback": <traceback_string> (if DEBUG is True)
                }

        """
        import traceback

        error_detail = {
            "message": f"Internal Server Error: {str(exception)}",
            "type": type(exception).__name__,
            "traceback": traceback.format_exc() if settings.DEBUG else None,
        }
        return error_detail
