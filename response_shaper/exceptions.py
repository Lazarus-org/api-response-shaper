from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any, Callable, Dict, Type, Union

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
from django.utils.module_loading import import_string

from response_shaper.settings.conf import response_shaper_config


class ExceptionHandler:
    """Handles exception responses consistently across the application.

    This class provides a centralized way to handle exceptions and
    return consistent JSON error responses. It maps specific exceptions
    to appropriate HTTP status codes and messages, and includes detailed
    error information in debug mode.

    """

    @staticmethod
    def build_error_response(status_code: int, message: Any) -> JsonResponse:
        """Helper method to build error responses consistently.

        Args:
            status_code (int): The HTTP status code for the error response.
            message (Any): The error message or data to be included in the response.

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
        def bad_request(msg: Any = "Bad request") -> JsonResponse:
            """Handles 400 Bad Request errors, including detailed messages in
            debug mode."""
            error_message = (
                cls._get_detailed_error_info(exception) if settings.DEBUG else msg
            )
            return cls.build_error_response(400, error_message)

        def not_found(msg: str = "Resource not found") -> JsonResponse:
            """Handles 404 Not Found errors."""
            return cls.build_error_response(404, msg)

        def server_error(exc: Exception) -> JsonResponse:
            """Handles 500 Internal Server Errors, including detailed messages
            in debug mode."""
            error_message = (
                cls._get_detailed_error_info(exc)
                if settings.DEBUG
                else "Internal Server Error"
            )
            return cls.build_error_response(500, error_message)

        def db_error(exc: Exception, status: int = 500) -> JsonResponse:
            """Handles database errors, including detailed messages in debug
            mode."""
            error_message = (
                cls._get_detailed_error_info(exc)
                if settings.DEBUG
                else "A Database Error Occurred"
            )
            return cls.build_error_response(status, error_message)

        # Exception mapping dictionary
        exception_handlers: Dict[Type[Exception], Callable[[Any], JsonResponse]] = {
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
            ValidationError: lambda e: bad_request(
                cls.extract_error(cls._validation_error_data(e))
            ),
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

        # Fallback for subclass-based exceptions. Follow the exception MRO so
        # the nearest configured base class wins regardless of mapping order.
        for exc_class in type(exception).__mro__[1:]:
            handler = exception_handlers.get(exc_class)
            if handler:
                return handler(exception)

        # Catch-all for unexpected exceptions
        message = (
            cls._get_detailed_error_info(exception)
            if settings.DEBUG
            else "Internal Server Error"
        )
        return cls.build_error_response(500, message)

    @classmethod
    def extract_error(cls, error_data: Any) -> Any:
        """Extract error data using the configured extraction strategy.

        Built-in strategies:

        - ``first``: preserves the package's legacy first-error behavior.
        - ``smart``: traverses error containers while preserving flat mappings
          as atomic structured error payloads.
        - ``full``: preserves the complete error payload.

        Any other value is treated as a dotted Python path to a custom callable
        accepting the error data and returning the shaped error value.

        """
        strategy = response_shaper_config.error_extraction

        if strategy == "first":
            return cls.extract_first_error(error_data)
        if strategy == "smart":
            return cls.extract_smart_error(error_data)
        if strategy == "full":
            return error_data

        extractor = cls._load_custom_extractor(strategy)
        return extractor(error_data)

    @classmethod
    def _validation_error_data(cls, exception: ValidationError) -> Any:
        """Return structured Django ValidationError data for non-legacy modes.

        The legacy ``first`` strategy historically stringified the
        exception object itself. Preserve that exact behavior for
        compatibility, while newer strategies receive Django's
        serializable message structures.

        """
        if response_shaper_config.error_extraction == "first":
            return exception
        if hasattr(exception, "error_dict"):
            return exception.message_dict
        return exception.messages

    @staticmethod
    @lru_cache(maxsize=128)
    def _load_custom_extractor(strategy: str) -> Callable[[Any], Any]:
        try:
            extractor = import_string(strategy)
        except (ImportError, AttributeError) as exc:
            raise ImproperlyConfigured(
                "RESPONSE_SHAPER_ERROR_EXTRACTION must be 'first', 'smart', "
                "'full', or a dotted path to a callable."
            ) from exc

        if not callable(extractor):
            raise ImproperlyConfigured(
                f"Configured error extractor '{strategy}' is not callable."
            )
        return extractor

    @classmethod
    def extract_smart_error(cls, error_data: Any) -> Any:
        """Extract the first error without destroying structured payloads.

        A mapping whose values are all terminal values is treated as one
        atomic error payload and is returned intact. Mappings or
        sequences containing nested containers are treated as error
        trees and traversed until the first error is found.

        This intentionally uses structure rather than key names, so
        consumers can use arbitrary machine-readable fields such as
        ``code``, ``detail``, ``parameter``, ``meta``, or domain-
        specific equivalents.

        """
        if isinstance(error_data, str):
            return error_data

        if cls._is_sequence(error_data):
            if not error_data:
                return error_data
            return cls.extract_smart_error(error_data[0])

        if isinstance(error_data, Mapping):
            if not error_data:
                return error_data

            if cls._is_atomic_mapping(error_data):
                return error_data

            first_key = next(iter(error_data))
            first_value = error_data[first_key]
            extracted = cls.extract_smart_error(first_value)

            if response_shaper_config.return_dict_error:
                if not cls._is_container(extracted):
                    return {first_key: extracted}
                return extracted
            return extracted

        return error_data

    @classmethod
    def _is_atomic_mapping(cls, error_data: Mapping) -> bool:
        """Return whether a mapping represents one terminal error payload."""
        return bool(error_data) and all(
            not cls._is_container(value) for value in error_data.values()
        )

    @classmethod
    def _is_container(cls, value: Any) -> bool:
        """Return whether a value can contain nested error data."""
        return isinstance(value, Mapping) or cls._is_sequence(value)

    @staticmethod
    def _is_sequence(value: Any) -> bool:
        """Return whether a value is a non-string sequence."""
        return isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        )

    @staticmethod
    def extract_first_error(error_data: Any) -> Union[Any, Dict]:
        """Extract the first error message from various data structures (dict,
        list, string). Stops at the first error encountered.

        Behavior is controlled by settings.EXTRACT_ERROR_AS_DICT:
        - If True: Returns the innermost dict with a string value
        - If False: Returns the first string value

        Args:
            error_data (Any): The error data structure, which can be a string,
                list, or dictionary.

        Returns:
            Union[str, dict]: The extracted error message or structure based on settings.

        """
        if isinstance(error_data, str):
            return error_data
        if isinstance(error_data, list) and error_data:
            return ExceptionHandler.extract_first_error(error_data[0])
        if isinstance(error_data, dict):
            if not error_data:
                return str(error_data)
            first_key = next(iter(error_data))
            first_value = error_data[first_key]

            # Recursively process the value
            extracted = ExceptionHandler.extract_first_error(first_value)

            if response_shaper_config.return_dict_error:
                # If the extracted result is a string, return it as a single key-value dict
                if isinstance(extracted, str):
                    return {first_key: extracted}
                # If it's already a dict (from deeper recursion), return it as-is
                return extracted
            return extracted
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
