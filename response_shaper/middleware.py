from typing import Awaitable, Callable, Optional, Union

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.http import HttpRequest, HttpResponseBase

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
    """A middleware that structures raw Django exceptions into a consistent JSON
    error format.

    Response shaping for regular (successful and error) DRF responses is handled by
    :class:`response_shaper.renderers.ShapedJSONRenderer`, which wraps the payload
    before it is serialized and therefore avoids the extra decode/re-encode cycle
    that middleware-based shaping incurred. This middleware now focuses solely on
    catching unhandled Django exceptions and returning structured error responses,
    for both synchronous and asynchronous workflows.

    Attributes:
        excluded_paths (list): Paths for which exception shaping should be skipped.
        debug (bool): Whether debug mode is enabled.

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

    def __sync_call__(self, request: HttpRequest) -> HttpResponseBase:
        """Process the request synchronously, passing the response through
        untouched (shaping happens in the renderer).

        Args:
            request: The incoming HTTP request.

        Returns:
            HttpResponseBase: The response returned by the next handler.

        """
        return self.get_response(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        """Process the request asynchronously, passing the response through
        untouched (shaping happens in the renderer).

        Args:
            request: The incoming HTTP request.

        Returns:
            HttpResponseBase: The response returned by the next handler.

        """
        return await self.get_response(request)

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

    def shape_is_not_allowed(self, request: HttpRequest) -> bool:
        """Determine if exception shaping should be skipped for the current
        request.

        This method checks whether the middleware should skip exception shaping
        based on the `debug` mode or if the request path starts with any of the
        excluded paths.

        Args:
            request (HttpRequest): The incoming HTTP request object.

        Returns:
            bool: True if shaping is not allowed (i.e., should be skipped), False otherwise.

        """
        if self.debug:
            return True

        for excluded_path in self.excluded_paths:
            if request.path.startswith(excluded_path):
                return True

        return False
