from typing import Any, Callable, Dict, Optional

from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request

from response_shaper.exceptions import ExceptionHandler
from response_shaper.settings.conf import response_shaper_config


class ShapedJSONRenderer(JSONRenderer):
    """A DRF JSON renderer that shapes API responses into a consistent envelope
    at render time.

    Unlike middleware-based shaping, this renderer wraps ``response.data`` into
    the final structure *before* it is serialized to JSON. That means the payload
    is serialized only once, avoiding the extra ``decode`` -> re-``encode`` cycle
    that a middleware incurs when it reads an already-rendered response and builds
    a brand new one. The result is a noticeable performance improvement for large
    payloads while keeping the exact same output structure.

    Successful responses (2xx) are shaped as::

        {"status": True, "status_code": <code>, "error": None, "data": <data>}

    Non-2xx responses are shaped as::

        {"status": False, "status_code": <code>, "error": <first error>, "data": {}}

    Both shapes can be overridden with custom handlers via the
    ``RESPONSE_SHAPER_SUCCESS_HANDLER`` and ``RESPONSE_SHAPER_ERROR_HANDLER``
    settings. A custom handler is a callable with the signature
    ``(data, status_code, renderer_context) -> dict`` that returns the envelope
    to serialize.

    """

    def render(
        self,
        data: Any,
        accepted_media_type: Optional[str] = None,
        renderer_context: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Shape ``data`` into the consistent envelope and serialize it once.

        Args:
            data: The response data provided by the view/serializer.
            accepted_media_type: The negotiated media type (unused, passed through).
            renderer_context: DRF-provided context, expected to contain the
                ``response`` and ``request`` objects.

        Returns:
            bytes: The JSON-encoded, shaped response body.

        """
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        request = renderer_context.get("request")
        status_code = getattr(response, "status_code", 200)

        # Skip shaping entirely when disabled or for excluded paths.
        if self._shape_is_not_allowed(request):
            return super().render(data, accepted_media_type, renderer_context)

        if 200 <= status_code < 300:
            handler = self._get_handler(
                response_shaper_config.success_handler,
                self._default_success_handler,
            )
        else:
            handler = self._get_handler(
                response_shaper_config.error_handler,
                self._default_error_handler,
            )

        shaped = handler(data, status_code, renderer_context)
        return super().render(shaped, accepted_media_type, renderer_context)

    def _default_success_handler(
        self, data: Any, status_code: int, renderer_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the default success envelope.

        Args:
            data: The response data to wrap.
            status_code: The HTTP status code of the response.
            renderer_context: DRF-provided context (unused by the default).

        Returns:
            Dict[str, Any]: The shaped success response.

        """
        return {
            "status": True,
            "status_code": status_code,
            "error": None,
            "data": data,
        }

    def _default_error_handler(
        self, data: Any, status_code: int, renderer_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the default error envelope.

        Args:
            data: The response data to extract the error message from.
            status_code: The HTTP status code of the response.
            renderer_context: DRF-provided context (unused by the default).

        Returns:
            Dict[str, Any]: The shaped error response.

        """
        return {
            "status": False,
            "status_code": status_code,
            "error": ExceptionHandler.extract_first_error(data),
            "data": {},
        }

    def _get_handler(self, handler_path: str, default_handler: Callable) -> Callable:
        """Resolve a custom handler from its dotted path, falling back to the
        default when it cannot be imported.

        Args:
            handler_path: The dotted import path to the custom handler.
            default_handler: The handler to fall back to on ImportError.

        Returns:
            Callable: The resolved handler (custom or default).

        """
        try:
            from django.utils.module_loading import import_string

            return import_string(handler_path)
        except ImportError:
            return default_handler

    def _shape_is_not_allowed(self, request: Optional[Request]) -> bool:
        """Determine whether shaping should be skipped for this request.

        Shaping is skipped when debug mode is enabled or when the request path
        starts with one of the configured excluded paths.

        Args:
            request: The incoming DRF request (may be ``None`` in some contexts).

        Returns:
            bool: True if shaping should be skipped, False otherwise.

        """
        if response_shaper_config.debug:
            return True

        if request is None:
            return False

        path = getattr(request, "path", "")
        for excluded_path in response_shaper_config.excluded_paths:
            if path.startswith(excluded_path):
                return True

        return False
