import json
from typing import Any, Callable, Optional, Union

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework.views import exception_handler

from response_shaper.settings.conf import response_shaper_config


class DynamicResponseMiddleware(MiddlewareMixin):
    """A middleware to structure API responses in a consistent format based on
    dynamic settings."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        """Initialize the middleware with dynamic settings.

        Args:
            get_response: The next middleware or view to call.

        """
        super().__init__(get_response)
        self.excluded_paths = response_shaper_config.excluded_paths
        self.debug = response_shaper_config.debug
        self.success_handler = self.get_dynamic_handler(
            response_shaper_config.success_handler, self._default_success_handler
        )
        self.error_handler = self.get_dynamic_handler(
            response_shaper_config.error_handler, self._default_error_handler
        )

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        """Process the request and response.

        Args:
            request: The incoming HTTP request.

        Returns:
            HttpResponseBase: The structured HTTP response.

        """
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(
        self, request: HttpRequest, response: HttpResponseBase
    ) -> HttpResponseBase:
        """Modify API responses to follow a consistent structure, skipping HTML
        responses.

        Args:
            request: The incoming HTTP request.
            response: The original HTTP response.

        Returns:
            HttpResponse: The processed HTTP response, with structured JSON if applicable.

        """
        if self.shape_is_not_allowed(request):
            return response

        content_type = response.headers.get("Content-Type", "")

        # Skip custom processing for non-JSON content types
        if not content_type.startswith("application/json"):
            return response

        # Structure the API response for success or error cases
        if 200 <= response.status_code < 300:
            return self.success_handler(response)
        else:
            return self.error_handler(response)

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> Optional[HttpResponseBase]:
        """Handle exceptions and structure error responses consistently.

        Args:
            request: The incoming HTTP request.
            exception: The raised exception to handle.

        Returns:
            Optional[HttpResponse]: The structured error response or None.

        """
        response = exception_handler(exception, None)

        if self.shape_is_not_allowed(request):
            return response

        # Handle specific Django exceptions explicitly
        if isinstance(exception, IntegrityError):
            return self._build_error_response(400, str(exception))
        if isinstance(exception, ValidationError):
            return self._build_error_response(400, self._extract_first_error(exception))
        if isinstance(exception, ObjectDoesNotExist):
            return self._build_error_response(404, "Object not found")

        # Generic 500 Internal Server Error
        detailed_error_message = self._get_detailed_error_info(exception)
        return self._build_error_response(500, detailed_error_message)

    def _get_detailed_error_info(self, exception: Exception) -> dict:
        """Extract detailed error information including the exception message
        and traceback.

        Args:
            exception: The exception that occurred.

        Returns:
            dict: A dictionary containing the error details and traceback.

        """
        import traceback

        error_detail = {
            "message": f"Internal Server Error: {str(exception)}",
            "type": type(exception).__name__,
            "traceback": traceback.format_exc() if settings.DEBUG else None,
        }
        return error_detail

    def _default_success_handler(self, response: HttpResponse) -> JsonResponse:
        """Default handler for successful responses.

        Args:
            response: The original HTTP response.

        Returns:
            JsonResponse: The modified success response with structured data.

        """
        if hasattr(response, "data"):
            data = response.data
        else:
            # Decode the content if 'data' is not available
            data = json.loads(response.content.decode("utf-8"))

        custom_response = {
            "status": True,
            "status_code": response.status_code,
            "error": None,
            "data": data,  # Ensure that data is passed
        }

        return JsonResponse(custom_response, status=response.status_code)

    def _default_error_handler(self, response: HttpResponse) -> JsonResponse:
        """Default handler for error responses.

        Args:
            response: The original HTTP error response.

        Returns:
            JsonResponse: The modified error response with structured error data.

        """
        if hasattr(response, "data"):
            error_message = self._extract_first_error(response.data)
        else:
            # Decode content if 'data' is not available
            error_message = json.loads(response.content.decode("utf-8"))["error"]

        return self._build_error_response(response.status_code, error_message)

    def _build_error_response(
        self, status_code: int, message: Union[str, dict]
    ) -> JsonResponse:
        """Helper method to build error responses consistently.

        Args:
            status_code: The HTTP status code for the error response.
            message: The error message or data.

        Returns:
            JsonResponse: The structured error response.

        """
        return JsonResponse(
            {"status": False, "status_code": status_code, "error": message, "data": {}},
            status=status_code,
        )

    def _extract_first_error(self, error_data: Any) -> Union[str, dict]:
        """Extract the first error message from various data structures (dict,
        list, string). Stops at the first error encountered.

        Args:
            error_data: The error data structure.

        Returns:
            Union[str, dict]: The extracted error message or structure.

        """
        if isinstance(error_data, str):
            return error_data
        elif isinstance(error_data, list):
            if error_data:
                return self._extract_first_error(error_data[0])
        elif isinstance(error_data, dict):
            for key, value in error_data.items():
                first_error = self._extract_first_error(value)
                if isinstance(first_error, str):
                    return {key: first_error}  # Return as a dict with the field name

        return str(error_data)

    def get_dynamic_handler(
        self, handler_path: str, default_handler: Callable
    ) -> Callable:
        """Load the dynamic handler (success or error) based on the handler
        path in settings.

        Args:
            handler_path: The dotted path to the custom handler.
            default_handler: The default handler to fall back to.

        Returns:
            Callable: The handler function (either custom or default).

        """
        try:
            from django.utils.module_loading import import_string

            return import_string(handler_path)
        except ImportError:
            return default_handler

    def shape_is_not_allowed(self, request: HttpRequest) -> bool:
        """Determine if response shaping should be skipped for the current
        request.

        This method checks whether the middleware should skip response shaping
        based on the `debug` mode or if the request path is in the list of excluded paths.

        Args:
            request (HttpRequest): The incoming HTTP request object.

        Returns:
            bool: True if response shaping is not allowed (i.e., should be skipped), False otherwise.

        """
        return self.debug or request.path in self.excluded_paths
