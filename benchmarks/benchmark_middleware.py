"""Compare the legacy JSON shaping path with the optimized middleware path.

Run from the repository root:

    python benchmarks/benchmark_middleware.py

The benchmark uses only project dependencies and Python's standard library.

"""

import argparse
import json
import statistics
import timeit
from typing import Callable

from django.conf import settings

if not settings.configured:
    settings.configure(
        DEFAULT_CHARSET="utf-8",
        INSTALLED_APPS=[],
        REST_FRAMEWORK={},
    )

import django  # noqa: E402  pylint: disable=wrong-import-position
from django.http import (  # noqa: E402  pylint: disable=wrong-import-position
    JsonResponse,
)
from rest_framework.renderers import JSONRenderer  # noqa: E402
from rest_framework.response import Response  # noqa: E402

django.setup()

from response_shaper.middleware import DynamicResponseMiddleware  # noqa: E402


def legacy_json_response_handler(response: JsonResponse) -> JsonResponse:
    """Reproduce the previous parse-and-reserialize success path."""
    data = json.loads(response.content.decode(response.charset))
    return JsonResponse(
        {
            "status": True,
            "status_code": response.status_code,
            "error": None,
            "data": data,
        },
        status=response.status_code,
    )


class CountingJSONRenderer(JSONRenderer):
    """Record how often DRF renders a response body."""

    calls = 0

    def render(self, data, accepted_media_type=None, renderer_context=None):
        self.calls += 1
        return super().render(data, accepted_media_type, renderer_context)


def make_drf_response(payload: dict) -> tuple[Response, CountingJSONRenderer]:
    """Create a finalized-enough DRF response for middleware rendering."""
    renderer = CountingJSONRenderer()
    response = Response(payload, status=200)
    response.accepted_renderer = renderer
    response.accepted_media_type = "application/json"
    response.renderer_context = {}
    return response, renderer


def best_time(operation: Callable[[], None], number: int, repeat: int) -> float:
    """Return the median elapsed time to reduce one-off scheduling noise."""
    samples = timeit.repeat(operation, number=number, repeat=repeat)
    return statistics.median(samples)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=int, default=1_000)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()

    payload = {
        "items": [
            {"id": index, "name": f"item-{index}", "active": index % 2 == 0}
            for index in range(args.items)
        ]
    }
    middleware = DynamicResponseMiddleware(lambda request: JsonResponse({}))

    def legacy_operation() -> None:
        legacy_json_response_handler(JsonResponse(payload))

    def optimized_operation() -> None:
        middleware._default_success_handler(JsonResponse(payload))

    legacy_result = legacy_json_response_handler(JsonResponse(payload))
    optimized_result = middleware._default_success_handler(JsonResponse(payload))
    if json.loads(legacy_result.content) != json.loads(optimized_result.content):
        raise RuntimeError("Legacy and optimized JSON results differ")

    legacy_seconds = best_time(legacy_operation, args.iterations, args.repeat)
    optimized_seconds = best_time(optimized_operation, args.iterations, args.repeat)

    drf_response, renderer = make_drf_response(payload)
    shaped_drf_response = middleware._default_success_handler(drf_response)
    if shaped_drf_response is not drf_response:
        raise RuntimeError("DRF response object was replaced")
    if renderer.calls != 1:
        raise RuntimeError(f"DRF renderer ran {renderer.calls} times instead of once")
    if not shaped_drf_response.is_rendered:
        raise RuntimeError("DRF response was not marked as rendered")
    if json.loads(shaped_drf_response.content)["data"] != payload:
        raise RuntimeError("DRF renderer output does not contain the original payload")

    print(f"Payload items: {args.items:,}")
    print(f"Iterations per sample: {args.iterations:,}; samples: {args.repeat}")
    print(f"Legacy parse + reserialize: {legacy_seconds:.4f}s")
    print(f"Optimized byte envelope:   {optimized_seconds:.4f}s")
    print(f"Speedup:                   {legacy_seconds / optimized_seconds:.2f}x")
    print("DRF renderer verification: one render, original Response preserved")


if __name__ == "__main__":
    main()
