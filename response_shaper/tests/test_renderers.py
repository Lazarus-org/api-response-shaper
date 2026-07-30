import json
import sys
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from response_shaper.renderers import ShapedJSONRenderer
from response_shaper.settings.conf import response_shaper_config
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.renderers,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class _FakeResponse:
    """Minimal stand-in for a DRF Response carrying only a status code."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class TestShapedJSONRenderer:
    """Test suite for the ShapedJSONRenderer."""

    def render(
        self,
        data: Any,
        status_code: Optional[int] = 200,
        path: str = "/api/test/",
        with_context: bool = True,
    ) -> Dict[str, Any]:
        """Render ``data`` through the shaped renderer and return the parsed JSON.

        :param data: The payload to render.
        :param status_code: Status code exposed on the fake response.
        :param path: The request path used for the renderer context.
        :param with_context: When False, render without a renderer_context.
        :return: The decoded JSON body as a Python dict.
        """
        renderer = ShapedJSONRenderer()
        renderer_context: Optional[Dict[str, Any]] = None
        if with_context:
            renderer_context = {
                "response": _FakeResponse(status_code),
                "request": RequestFactory().get(path),
            }
        content = renderer.render(data, renderer_context=renderer_context)
        return json.loads(content.decode("utf-8"))

    def test_success_shaping(self) -> None:
        """A 2xx response is wrapped in the default success envelope."""
        result = self.render({"key": "value"}, status_code=200)
        assert result == {
            "status": True,
            "status_code": 200,
            "error": None,
            "data": {"key": "value"},
        }

    def test_error_shaping(self) -> None:
        """A non-2xx response is wrapped in the default error envelope."""
        response_shaper_config.return_dict_error = False
        result = self.render({"detail": "Some error occurred"}, status_code=400)
        assert result == {
            "status": False,
            "status_code": 400,
            "error": "Some error occurred",
            "data": {},
        }

    def test_no_renderer_context(self) -> None:
        """Rendering without a context defaults to a 200 success envelope."""
        result = self.render({"key": "value"}, with_context=False)
        assert result == {
            "status": True,
            "status_code": 200,
            "error": None,
            "data": {"key": "value"},
        }

    def test_excluded_path_is_not_shaped(self) -> None:
        """Requests to excluded paths are rendered without shaping."""
        with patch.object(
            response_shaper_config, "excluded_paths", new=["/api/excluded/"]
        ):
            result = self.render({"key": "value"}, path="/api/excluded/")
            assert result == {"key": "value"}

    def test_debug_mode_skips_shaping(self) -> None:
        """Debug mode disables shaping entirely."""
        with patch.object(response_shaper_config, "debug", new=True):
            result = self.render({"key": "value"})
            assert result == {"key": "value"}

    def test_custom_success_handler(self) -> None:
        """A custom success handler from settings overrides the default envelope."""

        def custom_success_handler(
            data: Any, status_code: int, renderer_context: Dict[str, Any]
        ) -> Dict[str, Any]:
            return {"custom": "success", "code": status_code, "payload": data}

        with patch(
            "django.utils.module_loading.import_string",
            return_value=custom_success_handler,
        ):
            result = self.render({"key": "value"}, status_code=200)
            assert result == {
                "custom": "success",
                "code": 200,
                "payload": {"key": "value"},
            }

    def test_custom_error_handler(self) -> None:
        """A custom error handler from settings overrides the default envelope."""

        def custom_error_handler(
            data: Any, status_code: int, renderer_context: Dict[str, Any]
        ) -> Dict[str, Any]:
            return {"custom": "error", "code": status_code}

        with patch(
            "django.utils.module_loading.import_string",
            return_value=custom_error_handler,
        ):
            result = self.render({"detail": "bad"}, status_code=400)
            assert result == {"custom": "error", "code": 400}
