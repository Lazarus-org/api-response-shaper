import json
import sys

import pytest
from asgiref.sync import iscoroutinefunction
from django.core.exceptions import DisallowedHost, ImproperlyConfigured, ValidationError
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.test import RequestFactory, override_settings
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response

from response_shaper.decorators import format_api_response
from response_shaper.exceptions import ExceptionHandler
from response_shaper.middleware import DynamicResponseMiddleware
from response_shaper.responses import (
    RESPONSE_SHAPER_PROCESSED_ATTR,
    api_response,
    rate_limited_response,
    redirect_response,
)
from response_shaper.settings.conf import response_shaper_config
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


def parse_json(response):
    return json.loads(response.content.decode("utf-8"))


class CountingJSONRenderer(BaseRenderer):
    media_type = "application/json"
    format = "json"
    charset = None

    def __init__(self):
        self.calls = 0

    def render(self, data, accepted_media_type=None, renderer_context=None):
        self.calls += 1
        return json.dumps(data).encode("utf-8")


class CustomDisallowedHost(DisallowedHost):
    pass


def custom_validation_extractor(error_data):
    return {"received": error_data}


@pytest.mark.exceptions
class TestErrorExtractionRegressions:
    def test_smart_atomic_mapping_preserves_identity(self, monkeypatch):
        monkeypatch.setattr(response_shaper_config, "error_extraction", "smart")
        payload = {
            "code": "map_bbox_required",
            "detail": "geometry_bbox is required.",
            "parameter": "geometry_bbox",
        }

        assert ExceptionHandler.extract_error(payload) is payload

    def test_smart_dict_mode_preserves_non_string_leaf_key(self, monkeypatch):
        monkeypatch.setattr(response_shaper_config, "error_extraction", "smart")
        monkeypatch.setattr(response_shaper_config, "return_dict_error", True)

        assert ExceptionHandler.extract_error({"age": [42]}) == {"age": 42}

    @override_settings(DEBUG=False)
    def test_django_validation_error_smart_uses_structured_messages(self, monkeypatch):
        monkeypatch.setattr(response_shaper_config, "error_extraction", "smart")
        monkeypatch.setattr(response_shaper_config, "return_dict_error", True)

        response = ExceptionHandler.handle(
            ValidationError({"field": ["Invalid value"]})
        )

        assert parse_json(response)["error"] == {"field": "Invalid value"}

    @override_settings(DEBUG=False)
    def test_django_validation_error_full_preserves_all_messages(self, monkeypatch):
        monkeypatch.setattr(response_shaper_config, "error_extraction", "full")

        response = ExceptionHandler.handle(
            ValidationError({"field": ["Invalid value", "Second error"]})
        )

        assert parse_json(response)["error"] == {
            "field": ["Invalid value", "Second error"]
        }

    @override_settings(DEBUG=False)
    def test_django_validation_error_custom_extractor_receives_messages(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            response_shaper_config,
            "error_extraction",
            "response_shaper.tests.test_regressions.custom_validation_extractor",
        )

        response = ExceptionHandler.handle(
            ValidationError({"field": ["Invalid value"]})
        )

        assert parse_json(response)["error"] == {
            "received": {"field": ["Invalid value"]}
        }

    @override_settings(DEBUG=False)
    def test_legacy_first_validation_error_behavior_is_unchanged(self, monkeypatch):
        monkeypatch.setattr(response_shaper_config, "error_extraction", "first")

        error = ValidationError({"field": ["Invalid value"]})
        response = ExceptionHandler.handle(error)

        assert parse_json(response)["error"] == str(error)

    @override_settings(DEBUG=False)
    def test_exception_subclass_uses_nearest_mro_handler(self):
        response = ExceptionHandler.handle(CustomDisallowedHost("bad host"))

        assert response.status_code == 400
        assert parse_json(response)["error"] == "Invalid host header"


@pytest.mark.middleware
class TestMiddlewareRegressions:
    def test_plain_detail_json_error_is_not_dropped(self):
        middleware = DynamicResponseMiddleware(lambda request: None)
        response = JsonResponse({"detail": "bad"}, status=400)

        shaped = middleware._default_error_handler(response)

        assert parse_json(shaped)["error"] == {"detail": "bad"}

    @pytest.mark.parametrize(
        ("payload", "expected"),
        [(["bad", "second"], "bad"), ("bad", "bad")],
    )
    def test_plain_non_mapping_json_error_does_not_crash(self, payload, expected):
        middleware = DynamicResponseMiddleware(lambda request: None)
        response = JsonResponse(payload, safe=False, status=400)

        shaped = middleware._default_error_handler(response)

        assert parse_json(shaped)["error"] == expected

    def test_explicit_error_key_keeps_legacy_behavior(self):
        middleware = DynamicResponseMiddleware(lambda request: None)
        response = JsonResponse({"error": "bad", "detail": "ignored"}, status=400)

        shaped = middleware._default_error_handler(response)

        assert parse_json(shaped)["error"] == "bad"

    def test_non_drf_response_data_attribute_keeps_legacy_success_contract(self):
        middleware = DynamicResponseMiddleware(lambda request: None)
        response = JsonResponse({"content": "body"})
        response.data = {"from": "data-attribute"}

        shaped = middleware._default_success_handler(response)

        assert parse_json(shaped)["data"] == {"from": "data-attribute"}

    def test_non_drf_response_data_attribute_keeps_legacy_error_contract(self):
        middleware = DynamicResponseMiddleware(lambda request: None)
        response = JsonResponse({"error": "body-error"}, status=400)
        response.data = {"field": ["data-error"]}

        shaped = middleware._default_error_handler(response)

        assert parse_json(shaped)["error"] == {"field": "data-error"}

    def test_streaming_json_response_is_bypassed(self):
        request = RequestFactory().get("/api/test/")
        response = StreamingHttpResponse(
            [b'{"key":"value"}'], content_type="application/json"
        )
        middleware = DynamicResponseMiddleware(lambda request: response)

        assert middleware.process_response(request, response) is response

    @pytest.mark.parametrize("status_code", [103, 204, 205, 304])
    def test_body_disallowed_status_is_bypassed(self, status_code):
        request = RequestFactory().get("/api/test/")
        response = HttpResponse(status=status_code, content_type="application/json")
        middleware = DynamicResponseMiddleware(lambda request: response)

        assert middleware.process_response(request, response) is response

    def test_json_sequence_media_type_is_not_treated_as_single_json(self):
        request = RequestFactory().get("/api/test/")
        response = HttpResponse(
            b'{"id":1}\n{"id":2}\n', content_type="application/json-seq"
        )
        middleware = DynamicResponseMiddleware(lambda request: response)

        assert middleware.process_response(request, response) is response

    def test_problem_json_is_not_rewritten_by_generic_json_contract(self):
        request = RequestFactory().get("/api/test/")
        response = HttpResponse(
            b'{"type":"about:blank","title":"Bad Request"}',
            status=400,
            content_type="application/problem+json",
        )
        middleware = DynamicResponseMiddleware(lambda request: response)

        assert middleware.process_response(request, response) is response

    def test_content_encoded_json_is_bypassed(self):
        request = RequestFactory().get("/api/test/")
        response = HttpResponse(b"\x1f\x8bcompressed", content_type="application/json")
        response.headers["Content-Encoding"] = "gzip"
        middleware = DynamicResponseMiddleware(lambda request: response)

        assert middleware.process_response(request, response) is response

    def test_success_shaping_preserves_safe_metadata_and_invalidates_body_metadata(
        self,
    ):
        request = RequestFactory().get("/api/test/")
        response = JsonResponse({"key": "value"})
        response.headers["X-Request-ID"] = "request-123"
        response.headers["ETag"] = '"old"'
        response.headers["Content-Length"] = str(len(response.content))
        response.set_cookie("session", "cookie-value")
        middleware = DynamicResponseMiddleware(lambda request: response)

        shaped = middleware.process_response(request, response)

        assert shaped is response
        assert shaped.headers["X-Request-ID"] == "request-123"
        assert shaped.cookies["session"].value == "cookie-value"
        assert "ETag" not in shaped.headers
        assert "Content-Length" not in shaped.headers
        assert parse_json(shaped)["data"] == {"key": "value"}

    def test_drf_response_keeps_negotiated_renderer_and_response_identity(self):
        renderer = CountingJSONRenderer()
        response = Response({"key": "value"}, status=200)
        response.accepted_renderer = renderer
        response.accepted_media_type = "application/json"
        response.renderer_context = {}
        response.headers["X-Request-ID"] = "request-123"
        response.headers["ETag"] = '"old"'
        middleware = DynamicResponseMiddleware(lambda request: response)

        shaped = middleware._default_success_handler(response)

        assert shaped is response
        assert renderer.calls == 1
        assert shaped.data == {
            "status": True,
            "status_code": 200,
            "error": None,
            "data": {"key": "value"},
        }
        assert shaped.headers["X-Request-ID"] == "request-123"
        assert "ETag" not in shaped.headers

    def test_package_owned_response_is_not_double_shaped(self):
        request = RequestFactory().get("/api/test/")
        response = api_response(data={"key": "value"})
        middleware = DynamicResponseMiddleware(lambda request: response)

        assert getattr(response, RESPONSE_SHAPER_PROCESSED_ATTR) is True
        assert middleware.process_response(request, response) is response

    def test_lookalike_user_payload_is_still_shaped(self):
        request = RequestFactory().get("/api/test/")
        response = JsonResponse(
            {"status": "success", "message": "custom", "data": {"key": "value"}}
        )
        middleware = DynamicResponseMiddleware(lambda request: response)

        shaped = middleware.process_response(request, response)

        assert shaped is response
        assert parse_json(shaped)["data"] == {
            "status": "success",
            "message": "custom",
            "data": {"key": "value"},
        }

    def test_invalid_explicit_handler_path_fails_fast(self, monkeypatch):
        monkeypatch.setattr(
            response_shaper_config,
            "success_handler",
            "response_shaper.missing.success_handler",
        )

        with pytest.raises(ImproperlyConfigured):
            DynamicResponseMiddleware(lambda request: JsonResponse({"key": "value"}))

    def test_legacy_default_handler_sentinel_still_uses_builtin(self, monkeypatch):
        monkeypatch.setattr(
            response_shaper_config, "success_handler", "default_success_handler"
        )
        middleware = DynamicResponseMiddleware(
            lambda request: JsonResponse({"key": "value"})
        )

        response = middleware(RequestFactory().get("/api/test/"))

        assert parse_json(response)["data"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_async_custom_handler_is_awaited(self, monkeypatch):
        async def get_response(request):
            return JsonResponse({"key": "value"})

        async def custom_handler(response):
            return JsonResponse({"custom": response.status_code})

        monkeypatch.setattr(
            response_shaper_config, "success_handler", "tests.custom_handler"
        )
        monkeypatch.setattr(
            "response_shaper.middleware.import_string",
            lambda path: custom_handler,
        )
        middleware = DynamicResponseMiddleware(get_response)

        response = await middleware(RequestFactory().get("/api/test/"))

        assert parse_json(response) == {"custom": 200}

    @pytest.mark.asyncio
    async def test_async_custom_error_handler_is_awaited(self, monkeypatch):
        async def get_response(request):
            return JsonResponse({"error": "bad"}, status=400)

        async def custom_handler(response):
            return JsonResponse({"custom_error": response.status_code}, status=400)

        monkeypatch.setattr(
            response_shaper_config, "error_handler", "tests.custom_error_handler"
        )
        monkeypatch.setattr(
            "response_shaper.middleware.import_string",
            lambda path: custom_handler,
        )
        middleware = DynamicResponseMiddleware(get_response)

        response = await middleware(RequestFactory().get("/api/test/"))

        assert parse_json(response) == {"custom_error": 400}

    def test_async_custom_handler_can_run_from_sync_middleware(self, monkeypatch):
        def get_response(request):
            return JsonResponse({"key": "value"})

        async def custom_handler(response):
            return JsonResponse({"custom": response.status_code})

        monkeypatch.setattr(
            response_shaper_config, "success_handler", "tests.custom_handler"
        )
        monkeypatch.setattr(
            "response_shaper.middleware.import_string",
            lambda path: custom_handler,
        )
        middleware = DynamicResponseMiddleware(get_response)

        response = middleware(RequestFactory().get("/api/test/"))

        assert parse_json(response) == {"custom": 200}


@pytest.mark.decorators
class TestDecoratorAndHelperRegressions:
    @pytest.mark.asyncio
    async def test_async_decorator_preserves_async_execution_and_formats_response(self):
        async def view():
            return Response({"key": "value"}, status=200)

        decorated = format_api_response(view)

        assert iscoroutinefunction(decorated)
        response = await decorated()
        assert response.data["status"] == "success"
        assert response.data["data"] == {"key": "value"}

    def test_redirect_response_sets_location_header_when_url_is_supplied(self):
        response = redirect_response(redirect_url="https://example.com/new")

        assert response.headers["Location"] == "https://example.com/new"

    def test_redirect_response_does_not_invent_location_header(self):
        response = redirect_response(redirect_url=None)

        assert "Location" not in response.headers

    def test_rate_limited_response_sets_retry_after_header_when_supplied(self):
        response = rate_limited_response(retry_after=60)

        assert response.headers["Retry-After"] == "60"

    def test_rate_limited_response_does_not_invent_retry_after_header(self):
        response = rate_limited_response(retry_after=None)

        assert "Retry-After" not in response.headers
