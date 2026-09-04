"""Behavioral release checks using real Django and DRF response objects."""

import json
from unittest.mock import patch

import pytest
from django.core.exceptions import (
    DisallowedHost,
    DisallowedRedirect,
    ImproperlyConfigured,
    SuspiciousOperation,
    ValidationError,
)
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.test import RequestFactory, override_settings
from rest_framework import serializers
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response

from response_shaper.decorators import format_api_response
from response_shaper.exceptions import ExceptionHandler
from response_shaper.middleware import DynamicResponseMiddleware
from response_shaper.settings.conf import response_shaper_config


def sync_handler(response):
    return JsonResponse({"handled": response.status_code}, status=response.status_code)


async def async_handler(response):
    return sync_handler(response)


class AsyncHandlerObject:
    async def __call__(self, response):
        return sync_handler(response)


async_handler_object = AsyncHandlerObject()


def extract_messages(data):
    assert not isinstance(data, Exception)
    return {"received": data}


@pytest.fixture
def api_request():
    return RequestFactory().get("/api/validation/")


@pytest.mark.parametrize("strategy", ["first", "smart", "full", "custom"])
@pytest.mark.parametrize("messages", [["bad", "second"], "bad"])
def test_django_message_validation_forms(monkeypatch, strategy, messages):
    configured = __name__ + ".extract_messages" if strategy == "custom" else strategy
    monkeypatch.setattr(response_shaper_config, "error_extraction", configured)
    error = ValidationError(messages)
    result = json.loads(ExceptionHandler.handle(error).content)["error"]
    expected = {
        "first": str(error),
        "smart": "bad",
        "full": error.messages,
        "custom": {"received": error.messages},
    }
    assert result == expected[strategy]


@pytest.mark.parametrize("strategy", ["first", "smart", "full"])
def test_real_serializer_structured_error(monkeypatch, api_request, strategy):
    monkeypatch.setattr(response_shaper_config, "error_extraction", strategy)
    payload = {
        "code": "map_bbox_required",
        "detail": "geometry_bbox is required for map requests.",
        "parameter": "geometry_bbox",
    }
    response = rendered_response(serializers.ValidationError(payload).detail, 400)
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    assert json.loads(result.content)["renderer_payload"]["error"] == (
        {"code": "map_bbox_required"} if strategy == "first" else payload
    )


@pytest.mark.parametrize("status", [200, 400])
@pytest.mark.parametrize(
    "handler", ["sync_handler", "async_handler", "async_handler_object"]
)
@pytest.mark.asyncio
async def test_async_handlers_and_adapter_reuse(
    monkeypatch, api_request, status, handler
):
    monkeypatch.setattr(
        response_shaper_config,
        "success_handler" if status == 200 else "error_handler",
        __name__ + "." + handler,
    )

    async def view(api_request):
        return JsonResponse({"detail": "payload"}, status=status)

    middleware = DynamicResponseMiddleware(view)
    # Construction may adapt handlers; subsequent requests must reuse adapters.
    with patch("response_shaper.middleware.sync_to_async", side_effect=AssertionError):
        for _ in range(2):
            assert json.loads((await middleware(api_request)).content) == {
                "handled": status
            }


@pytest.mark.parametrize("status", [200, 400])
def test_async_callable_object_in_sync_middleware(monkeypatch, api_request, status):
    monkeypatch.setattr(
        response_shaper_config,
        "success_handler" if status == 200 else "error_handler",
        __name__ + ".async_handler_object",
    )
    response = JsonResponse({}, status=status)
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    assert json.loads(result.content) == {"handled": status}


@pytest.mark.parametrize("status", [200, 400])
@pytest.mark.parametrize("response_kind", ["json", "http", "data", "drf"])
def test_all_response_metadata_paths(api_request, status, response_kind):
    payload = {"error": "bad"} if status == 400 else {"value": 42}
    if response_kind == "drf":
        response = rendered_response(payload, status)
    elif response_kind == "http":
        response = HttpResponse(
            json.dumps(payload), status=status, content_type="application/json"
        )
    else:
        response = JsonResponse(payload, status=status)
        if response_kind == "data":
            response.data = payload
    retained = {
        "Vary": "Accept, Cookie",
        "Cache-Control": "private, max-age=60",
        "WWW-Authenticate": 'Basic realm="api"',
        "Location": "/destination/",
        "Retry-After": "60",
        "X-Request-ID": "release-check",
    }
    stale = [
        "Content-Length",
        "ETag",
        "Content-MD5",
        "Content-Range",
        "Digest",
        "Content-Digest",
        "Repr-Digest",
    ]
    for key, value in retained.items():
        response[key] = value
    for key in stale:
        response[key] = "123"
    response.set_cookie("session", "abc", httponly=True, samesite="Lax")
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    for key, value in retained.items():
        assert result[key] == value
    assert result.cookies.output() == response.cookies.output()
    for key in stale:
        assert key not in result, key


class DistinctRenderer(BaseRenderer):
    media_type = "application/json"
    format = "json"
    charset = None

    def __init__(self):
        self.calls = []

    def render(self, data, accepted_media_type=None, renderer_context=None):
        self.calls.append((data, accepted_media_type, renderer_context))
        return json.dumps({"renderer_payload": data}).encode()


def rendered_response(payload, status):
    response = Response(payload, status=status)
    response.accepted_renderer = DistinctRenderer()
    response.accepted_media_type = "application/json; profile=release"
    response.renderer_context = {"release": True}
    response.render()
    return response


@pytest.mark.parametrize("status", [200, 400])
def test_negotiated_renderer_actual_middleware(api_request, status):
    response = rendered_response({"field": ["value"]}, status)
    renderer = response.accepted_renderer
    context = response.renderer_context
    assert len(renderer.calls) == 1
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    assert result is response
    assert result.accepted_renderer is renderer
    assert result.renderer_context is context
    assert len(renderer.calls) == 2  # Original rendering plus the changed body.
    assert renderer.calls[-1][1:] == ("application/json; profile=release", context)
    assert json.loads(result.content) == {"renderer_payload": result.data}
    result.render()
    assert len(renderer.calls) == 2


@pytest.mark.parametrize("payload", [None, True, 42, 1.25, "bad", [], ["one", "two"]])
@pytest.mark.parametrize("strategy", ["first", "smart", "full"])
def test_plain_json_scalar_errors(monkeypatch, api_request, payload, strategy):
    monkeypatch.setattr(response_shaper_config, "error_extraction", strategy)
    response = JsonResponse(payload, safe=False, status=400)
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    expected = payload[0] if isinstance(payload, list) and payload else payload
    if strategy == "full":
        expected = payload
    elif strategy == "first":
        expected = str(expected)
    assert json.loads(result.content)["error"] == expected


@pytest.mark.parametrize(
    "base", [DisallowedHost, DisallowedRedirect, SuspiciousOperation]
)
@pytest.mark.parametrize("subclass", [False, True])
@override_settings(DEBUG=False)
def test_nearest_exception_handler(base, subclass):
    exception = type("ProjectError", (base,), {}) if subclass else base
    expected = {
        DisallowedHost: "Invalid host header",
        DisallowedRedirect: "Disallowed redirect",
        SuspiciousOperation: "Suspicious operation detected",
    }
    response = ExceptionHandler.handle(exception("private message"))
    assert response.status_code == 400
    assert json.loads(response.content)["error"] == expected[base]


@pytest.mark.parametrize(
    "media_type",
    ["application/json-seq", "application/problem+json", "application/vnd.api+json"],
)
def test_nonstandard_json_media_types(api_request, media_type):
    response = HttpResponse(
        b"deliberately not a JSON document", content_type=media_type
    )
    assert (
        DynamicResponseMiddleware(lambda api_request: response)(api_request) is response
    )


def test_stream_is_not_consumed(api_request):
    consumed = []

    def stream():
        consumed.append(True)
        yield b"{}"

    response = StreamingHttpResponse(stream(), content_type="application/json")
    assert (
        DynamicResponseMiddleware(lambda api_request: response)(api_request) is response
    )
    assert not consumed
    assert b"".join(response.streaming_content) == b"{}"


@pytest.mark.parametrize("status", [100, 101, 102, 103, 199, 204, 205, 304])
def test_body_disallowed_responses_keep_content(api_request, status):
    response = HttpResponse(b"", status=status, content_type="application/json")
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    assert result is response
    assert result.content == b""


@pytest.mark.parametrize(
    "payload",
    [{"text": "caf\u00e9", "nested": [1, None, True]}, [], [1, 2], "hello", 42, None],
)
@pytest.mark.parametrize(
    "dump_params",
    [{}, {"ensure_ascii": False}, {"indent": 2}, {"separators": (",", ":")}],
)
def test_json_fast_path_matches_normal_shaping(api_request, payload, dump_params):
    response = JsonResponse(payload, safe=False, json_dumps_params=dump_params)
    reference = HttpResponse(response.content, content_type="application/json")
    middleware = DynamicResponseMiddleware(lambda api_request: response)
    expected = middleware.process_response(api_request, reference)
    result = middleware(api_request)
    assert json.loads(result.content) == json.loads(expected.content)
    if not dump_params:
        assert result.content == expected.content


@pytest.mark.parametrize("charset", ["utf-16", "utf-32", "iso-8859-1"])
def test_json_non_utf8_charset_is_preserved_safely(api_request, charset):
    response = JsonResponse(
        {"text": "caf\u00e9"},
        charset=charset,
        content_type="application/json; charset=" + charset,
        json_dumps_params={"ensure_ascii": False},
    )
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    assert json.loads(result.content.decode(result.charset))["data"] == {
        "text": "caf\u00e9"
    }


@pytest.mark.parametrize("setting", ["success_handler", "error_handler"])
@pytest.mark.parametrize(
    "path", ["missing.module.handler", __name__ + ".response_shaper_config"]
)
def test_bad_handler_paths_fail_clearly(monkeypatch, setting, path):
    monkeypatch.setattr(response_shaper_config, setting, path)
    with pytest.raises(ImproperlyConfigured):
        DynamicResponseMiddleware(lambda api_request: None)


def test_decorator_response_survives_rendering_and_middleware(api_request):
    @format_api_response
    def view():
        return Response({"value": 42})

    response = view()
    response.accepted_renderer = DistinctRenderer()
    response.accepted_media_type = "application/json"
    response.renderer_context = {}
    response.render()
    original_content = response.content
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    assert result is response
    assert result.content == original_content
    assert len(response.accepted_renderer.calls) == 1


def test_custom_json_response_uses_normal_path(api_request):
    class ImmutableJSONResponse(JsonResponse):
        @property
        def content(self):
            return HttpResponse.content.fget(self)

        @content.setter
        def content(self, value):
            if getattr(self, "frozen", False):
                raise AssertionError("Custom response content must not be reassigned")
            HttpResponse.content.fset(self, value)

    response = ImmutableJSONResponse({"custom": True})
    response.frozen = True
    original = response.content
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    assert response.content == original
    assert json.loads(result.content)["data"] == {"custom": True}


@pytest.mark.parametrize("status", [200, 400])
@pytest.mark.parametrize("charset", ["utf-8", "utf-16", "iso-8859-1"])
def test_generic_json_http_response_charset(api_request, status, charset):
    response = HttpResponse(
        json.dumps({"error": "caf\u00e9"}, ensure_ascii=False),
        status=status,
        content_type="application/json; charset=" + charset,
    )
    result = DynamicResponseMiddleware(lambda api_request: response)(api_request)
    expected = {"error": "caf\u00e9"} if status == 200 else "caf\u00e9"
    assert json.loads(result.content)["data" if status == 200 else "error"] == expected
