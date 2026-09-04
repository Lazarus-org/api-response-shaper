import json
from typing import Awaitable, Callable, Optional, Union, cast

from asgiref.sync import (
    async_to_sync,
    iscoroutinefunction,
    markcoroutinefunction,
    sync_to_async,
)
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse, HttpResponseBase, JsonResponse
from django.utils.module_loading import import_string
from rest_framework.response import Response as DRFResponse

from response_shaper.exceptions import ExceptionHandler
from response_shaper.responses import RESPONSE_SHAPER_PROCESSED_ATTR
from response_shaper.settings.conf import response_shaper_config


class BaseMiddleware:
    """Base middleware class supporting synchronous and asynchronous modes."""

    sync_capable: bool = True
    async_capable: bool = True

    def __init__(
        self,
        get_response: Callable[
            [HttpRequest], Union[HttpResponseBase, Awaitable[HttpResponseBase]]
        ],
    ) -> None:
        self.get_response = get_response
        self.async_mode = iscoroutinefunction(self.get_response)
        if self.async_mode:
            markcoroutinefunction(self)

    def __repr__(self) -> str:
        get_response = getattr(
            self.get_response,
            "__qualname__",
            self.get_response.__class__.__name__,
        )
        return f"<{self.__class__.__qualname__} get_response={get_response}>"

    def __call__(
        self, request: HttpRequest
    ) -> Union[HttpResponseBase, Awaitable[HttpResponseBase]]:
        if self.async_mode:
            return self.__acall__(request)
        return self.__sync_call__(request)

    def __sync_call__(self, request: HttpRequest) -> HttpResponseBase:
        raise NotImplementedError("__sync_call__ must be implemented by subclass")

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        raise NotImplementedError("__acall__ must be implemented by subclass")


class DynamicResponseMiddleware(BaseMiddleware):
    """Shape JSON API responses according to the configured response
    contract."""

    # Four cached handler adapters avoid rebuilding them on each request.
    # pylint: disable=too-many-instance-attributes

    _BODY_DERIVED_HEADERS = (
        "Content-Length",
        "Content-MD5",
        "Content-Digest",
        "Content-Range",
        "Digest",
        "ETag",
        "Repr-Digest",
    )
    _LEGACY_DEFAULT_HANDLERS = {
        "default_success_handler",
        "default_error_handler",
    }

    def __init__(
        self,
        get_response: Callable[
            [HttpRequest], Union[HttpResponseBase, Awaitable[HttpResponseBase]]
        ],
    ) -> None:
        super().__init__(get_response)
        self.excluded_paths = tuple(response_shaper_config.excluded_paths)
        self.debug = response_shaper_config.debug
        self.success_handler = self.get_dynamic_handler(
            response_shaper_config.success_handler, self._default_success_handler
        )
        self.error_handler = self.get_dynamic_handler(
            response_shaper_config.error_handler, self._default_error_handler
        )

        self._sync_success_handler = self._to_sync_handler(self.success_handler)
        self._sync_error_handler = self._to_sync_handler(self.error_handler)
        self._async_success_handler = self._to_async_handler(self.success_handler)
        self._async_error_handler = self._to_async_handler(self.error_handler)

    def __sync_call__(self, request: HttpRequest) -> HttpResponseBase:
        response = cast(HttpResponseBase, self.get_response(request))
        return self.process_response(request, response)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        response = await cast(Awaitable[HttpResponseBase], self.get_response(request))
        return await self.process_response_async(request, response)

    def process_response(
        self, request: HttpRequest, response: HttpResponseBase
    ) -> HttpResponseBase:
        if not self._response_can_be_shaped(request, response):
            return response

        handler = (
            self._sync_success_handler
            if 200 <= response.status_code < 300
            else self._sync_error_handler
        )
        return handler(response)

    async def process_response_async(
        self, request: HttpRequest, response: HttpResponseBase
    ) -> HttpResponseBase:
        if not self._response_can_be_shaped(request, response):
            return response

        handler = (
            self._async_success_handler
            if 200 <= response.status_code < 300
            else self._async_error_handler
        )
        return await handler(response)

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> Optional[HttpResponseBase]:
        if self.shape_is_not_allowed(request):
            return None
        return ExceptionHandler.handle(exception)

    def _default_success_handler(self, response: HttpResponse) -> HttpResponseBase:
        if self._is_drf_response(response):
            drf_response = cast(DRFResponse, response)
            data = drf_response.data
            payload = {
                "status": True,
                "status_code": response.status_code,
                "error": None,
                "data": data,
            }
            return self._replace_response_payload(response, payload)

        # Preserve the package's historical contract for custom response types
        # that expose a ``data`` attribute, while keeping DRF renderer handling
        # isolated above and the plain JsonResponse fast path below.
        if hasattr(response, "data"):
            data = response.data
            payload = {
                "status": True,
                "status_code": response.status_code,
                "error": None,
                "data": data,
            }
            return self._replace_response_payload(response, payload)

        # Custom subclasses may forbid replacing their existing content.
        if (  # pylint: disable=unidiomatic-typecheck
            type(response) is JsonResponse and response.charset.lower() == "utf-8"
        ):
            return self._wrap_json_response_bytes(response)

        data = json.loads(response.content.decode(response.charset))
        payload = {
            "status": True,
            "status_code": response.status_code,
            "error": None,
            "data": data,
        }
        return self._replace_response_payload(response, payload)

    def _default_error_handler(self, response: HttpResponse) -> HttpResponseBase:
        if self._is_drf_response(response) or hasattr(response, "data"):
            error_message = ExceptionHandler.extract_error(getattr(response, "data"))
        else:
            payload = json.loads(response.content.decode(response.charset))
            if isinstance(payload, dict) and "error" in payload:
                # Preserve the package's historical handling for an explicit
                # top-level ``error`` key while supporting all other JSON shapes.
                error_message = payload["error"]
            else:
                error_message = ExceptionHandler.extract_error(payload)

        shaped_payload = {
            "status": False,
            "status_code": response.status_code,
            "error": error_message,
            "data": {},
        }
        return self._replace_response_payload(response, shaped_payload)

    def _replace_response_payload(
        self, response: HttpResponseBase, payload: dict
    ) -> HttpResponseBase:
        """Replace a response body while preserving valid response metadata."""
        if self._is_drf_response(response):
            drf_response = cast(DRFResponse, response)
            self._invalidate_body_headers(drf_response)
            drf_response.data = payload
            # DRF's rendered_content property invokes the already-negotiated
            # renderer and updates Content-Type according to that renderer.
            drf_response.content = drf_response.rendered_content
            return drf_response

        shaped = JsonResponse(payload, status=response.status_code)
        self._copy_response_metadata(response, shaped)
        return shaped

    @classmethod
    def _copy_response_metadata(
        cls, source: HttpResponseBase, target: HttpResponseBase
    ) -> None:
        """Copy headers/cookies that remain valid after replacing the body."""
        ignored_headers = {header.lower() for header in cls._BODY_DERIVED_HEADERS}
        ignored_headers.add("content-type")
        for header, value in source.headers.items():
            if header.lower() not in ignored_headers:
                target.headers[header] = value
        target.cookies = source.cookies

    def _wrap_json_response_bytes(self, response: JsonResponse) -> JsonResponse:
        """Envelope an already-rendered JsonResponse without parsing it
        again."""
        prefix = (
            b'{"status": true, "status_code": '
            + str(response.status_code).encode("ascii")
            + b', "error": null, "data": '
        )
        response.content = prefix + response.content + b"}"
        self._invalidate_body_headers(response)
        return response

    @classmethod
    def _invalidate_body_headers(cls, response: HttpResponseBase) -> None:
        for header in cls._BODY_DERIVED_HEADERS:
            if header in response.headers:
                del response.headers[header]

    @staticmethod
    def _is_drf_response(response: HttpResponseBase) -> bool:
        return isinstance(response, DRFResponse)

    def _response_can_be_shaped(
        self, request: HttpRequest, response: HttpResponseBase
    ) -> bool:
        if self.shape_is_not_allowed(request):
            return False

        if getattr(response, RESPONSE_SHAPER_PROCESSED_ATTR, False):
            return False

        if getattr(response, "streaming", False):
            return False

        status_code = response.status_code
        if 100 <= status_code < 200 or status_code in {204, 205, 304}:
            return False

        content_encoding = response.headers.get("Content-Encoding", "").strip().lower()
        if content_encoding and content_encoding != "identity":
            return False

        content_type = response.headers.get("Content-Type", "")
        media_type = content_type.partition(";")[0].strip().lower()
        return media_type == "application/json"

    def get_dynamic_handler(
        self, handler_path: str, default_handler: Callable
    ) -> Callable:
        if not handler_path or handler_path in self._LEGACY_DEFAULT_HANDLERS:
            return default_handler

        if not isinstance(handler_path, str):
            raise ImproperlyConfigured(
                "Response shaper handler settings must be dotted Python paths."
            )

        try:
            handler = import_string(handler_path)
        except (ImportError, AttributeError) as exc:
            raise ImproperlyConfigured(
                f"Could not import response shaper handler '{handler_path}'."
            ) from exc

        if not callable(handler):
            raise ImproperlyConfigured(
                f"Configured response shaper handler '{handler_path}' is not callable."
            )
        return handler

    @staticmethod
    def _to_sync_handler(handler: Callable) -> Callable:
        if iscoroutinefunction(handler) or iscoroutinefunction(
            getattr(handler, "__call__", None)
        ):
            return async_to_sync(handler)
        return handler

    @staticmethod
    def _to_async_handler(handler: Callable) -> Callable:
        if iscoroutinefunction(handler) or iscoroutinefunction(
            getattr(handler, "__call__", None)
        ):
            return handler
        return sync_to_async(handler)

    def shape_is_not_allowed(self, request: HttpRequest) -> bool:
        if self.debug:
            return True
        return bool(self.excluded_paths) and request.path.startswith(
            self.excluded_paths
        )
