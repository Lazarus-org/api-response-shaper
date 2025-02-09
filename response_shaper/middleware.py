import json
from typing import Awaitable, Callable, Optional, Union

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse

from response_shaper.exceptions import ExceptionHandler
from response_shaper.settings.conf import response_shaper_config


class BaseMiddleware:
    """Base middleware class that supports both synchronous and asynchronous
    modes.

    This class provides a foundation for creating middleware that can handle both
    synchronous and asynchronous requests. Subclasses must implement the `__sync_call__`
    and `__acall__` methods to define their behavior.

    Attributes:
        sync_capable (bool): Indicates whether the middleware can handle synchronous requests.
        async_capable (bool): Indicates whether the middleware can handle asynchronous requests.

    """

    sync_capable: bool = True
    async_capable: bool = True

    def __init__(
        self,
        get_response: Callable[
            [HttpRequest], Union[HttpResponseBase, Awaitable[HttpResponseBase]]
        ],
    ) -> None:
        """Initialize the middleware.

        Args:
            get_response: The next middleware or view to call. This can be either
                synchronous or asynchronous.

        """
        self.get_response = get_response
        self.async_mode = iscoroutinefunction(self.get_response)
        if self.async_mode:
            markcoroutinefunction(self)

    def __repr__(self) -> str:
        """Provides a string representation of the middleware.

        Returns:
            str: A string representation of the middleware, including the name of the
                `get_response` function or class.

        """
        ger_response = getattr(
            self.get_response,
            "__qualname__",
            self.get_response.__class__.__name__,
        )
        return f"<{self.__class__.__qualname__} get_response={ger_response}>"

    def __call__(
        self, request: HttpRequest
    ) -> Union[HttpResponseBase, Awaitable[HttpResponseBase]]:
        """Handles the incoming request, determining whether it's synchronous
        or asynchronous.

        Args:
            request (HttpRequest): The incoming HTTP request.

        Returns:
            Union[HttpResponseBase, Awaitable[HttpResponseBase]]: The HTTP response, either
                synchronous or asynchronous.

        """
        if self.async_mode:
            return self.__acall__(request)
        return self.__sync_call__(request)

    def __sync_call__(self, request: HttpRequest) -> HttpResponseBase:
        """Processes synchronous requests.

        Subclasses must implement this method to define how synchronous requests are handled.

        Args:
            request (HttpRequest): The incoming HTTP request.

        Returns:
            HttpResponseBase: The HTTP response.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.

        """
        raise NotImplementedError("__sync_call__ must be implemented by subclass")

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        """Processes asynchronous requests.

        Subclasses must implement this method to define how asynchronous requests are handled.

        Args:
            request (HttpRequest): The incoming HTTP request.

        Returns:
            HttpResponseBase: The HTTP response.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.

        """
        raise NotImplementedError("__acall__ must be implemented by subclass")


class DynamicResponseMiddleware(BaseMiddleware):
    """A middleware to structure API responses in a consistent format based on
    dynamic settings.

    This middleware modifies API responses to follow a consistent JSON structure for both
    success and error cases. It can be configured to exclude certain paths and supports
    custom success and error handlers.

    Attributes:
        excluded_paths (list): Paths for which response shaping should be skipped.
        debug (bool): Whether debug mode is enabled.
        success_handler (Callable): The handler for successful responses.
        error_handler (Callable): The handler for error responses.

    """

    def __init__(
        self,
        get_response: Callable[
            [HttpRequest], Union[HttpResponseBase, Awaitable[HttpResponseBase]]
        ],
    ):
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

    def __sync_call__(self, request: HttpRequest) -> HttpResponseBase:
        """Process the request and response.

        Args:
            request: The incoming HTTP request.

        Returns:
            HttpResponseBase: The structured HTTP response.

        """
        response = self.get_response(request)
        return self.process_response(request, response)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        """Process the request and response asynchronously.

        Args:
            request: The incoming HTTP request.

        Returns:
            HttpResponseBase: The structured HTTP response.

        """
        response = await self.get_response(request)
        return await self.process_response_async(request, response)

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

    async def process_response_async(
        self, request: HttpRequest, response: HttpResponseBase
    ) -> HttpResponseBase:
        """Processes async responses, structuring JSON responses.

        Args:
            request: The incoming HTTP request.
            response: The original HTTP response.

        Returns:
            HttpResponseBase: The processed HTTP response, with structured JSON if applicable.

        """
        if self.shape_is_not_allowed(request):
            return response

        content_type = response.headers.get("Content-Type", "")

        if not content_type.startswith("application/json"):
            return response

        return await sync_to_async(
            self.success_handler
            if 200 <= response.status_code < 300
            else self.error_handler
        )(response)

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
        if self.shape_is_not_allowed(request):
            return None  # pass to let Django handle the exception

        return ExceptionHandler.handle(exception)

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
            error_message = ExceptionHandler.extract_first_error(response.data)
        else:
            # Decode content if 'data' is not available
            error_message = json.loads(response.content.decode("utf-8")).get("error")

        return ExceptionHandler.build_error_response(
            response.status_code, error_message
        )

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
        based on the `debug` mode or if the request path starts with any of the
        excluded paths.

        Args:
            request (HttpRequest): The incoming HTTP request object.

        Returns:
            bool: True if response shaping is not allowed (i.e., should be skipped), False otherwise.

        """
        if self.debug:
            return True

        for excluded_path in self.excluded_paths:
            if request.path.startswith(excluded_path):
                return True

        return False
