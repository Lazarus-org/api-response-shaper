
# API Response Shaper
[![License](https://img.shields.io/github/license/lazarus-org/api-response-shaper)](https://github.com/lazarus-org/api-response-shaper/blob/main/LICENSE)
[![PyPI Release](https://img.shields.io/pypi/v/api-response-shaper)](https://pypi.org/project/api-response-shaper/)
[![Pylint Score](https://img.shields.io/badge/pylint-10/10-brightgreen?logo=python&logoColor=blue)](https://www.pylint.org/)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/api-response-shaper)](https://pypi.org/project/api-response-shaper/)
[![Supported Django Versions](https://img.shields.io/pypi/djversions/api-response-shaper)](https://pypi.org/project/api-response-shaper/)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=yellow)](https://github.com/pre-commit/pre-commit)
[![Open Issues](https://img.shields.io/github/issues/lazarus-org/api-response-shaper)](https://github.com/lazarus-org/api-response-shaper/issues)
[![Last Commit](https://img.shields.io/github/last-commit/lazarus-org/api-response-shaper)](https://github.com/lazarus-org/api-response-shaper/commits/main)
[![Languages](https://img.shields.io/github/languages/top/lazarus-org/api-response-shaper)](https://github.com/lazarus-org/api-response-shaper)
[![Coverage](https://codecov.io/gh/lazarus-org/api-response-shaper/branch/main/graph/badge.svg)](https://codecov.io/gh/lazarus-org/api-response-shaper)

`api-response-shaper` is a Django middleware and decorator-based package that helps structure API responses in a consistent format. It includes dynamic configurations and various pre-built response formats, such as paginated responses, batch responses, minimal success responses, and error responses. This package allows developers to streamline response shaping for their Django REST Framework (DRF) APIs, ensuring a uniform response format across different API endpoints.

## Features

- **Dynamic Middleware**: Automatically structures API responses for successful and error cases.
- **Customizable Handlers**: Easily switch between different response formats using decorators.
- **Pre-built Response Types**: Supports a variety of response types, including:
  - Standard API responses
  - Paginated responses
  - Batch operation responses
  - Error responses
  - Authentication responses
  - Minimal success responses
- **Custom Response Handlers**: Define custom success and error handlers for fine-tuned control.
- **Exclusion Paths**: Skip specific routes from being processed by the middleware.
- **Django Version**: Compatible with Django REST Framework (DRF) and Django middleware.

## Installation

To install the `api-response-shaper`, simply use pip:

```bash
pip install api-response-shaper
```

## Configuration

### Middleware Setup

Add the middleware to your Django settings:

```python
MIDDLEWARE = [
    # other middleware
    'response_shaper.middleware.DynamicResponseMiddleware',
]
```

You can also configure the `response_shaper_config` in your Django settings:

```python
# settings.py

CUSTOM_RESPONSE_DEBUG = True or False
CUSTOM_RESPONSE_EXCLUDED_PATHS = ["urlpath", ...]
CUSTOM_RESPONSE_SUCCESS_HANDLER = "path.of_your.handler"
CUSTOM_RESPONSE_ERROR_HANDLER = "path.of_your.handler"

```

### Available Settings:

- `CUSTOM_RESPONSE_DEBUG`: When set to `True`, disables response shaping for debugging purposes.
- `CUSTOM_RESPONSE_EXCLUDED_PATHS`: List of paths that will be skipped by the middleware.
- `CUSTOM_RESPONSE_SUCCESS_HANDLER`: Path to the custom success handler function.
- `CUSTOM_RESPONSE_ERROR_HANDLER`: Path to the custom error handler function.

## Usage

### Decorators for Response Formatting

You can apply different response formats using decorators in your views. Available decorators:

- `@format_api_response`: Applies the standard API response format.
- `@format_paginated_response`: Applies the paginated response format.
- `@format_error_response`: Applies the error response format.
- `@format_minimal_success_response`: Applies the minimal success response format.
- `@format_batch_response`: Applies the batch operation response format.
- `@format_auth_response`: Applies the authentication response format.

Example usage:

```python
from response_shaper.decorators import format_api_response, format_paginated_response

@format_api_response
def my_api_view(request):
    data = {"key": "value"}
    return Response(data, status=200)

@format_paginated_response
def paginated_view(request):
    paginated_data = {
        "data": [{"id": 1}, {"id": 2}],
        "page": 1,
        "total_pages": 5,
        "total_items": 50,
    }
    return Response(paginated_data, status=200)
```

### Custom Success and Error Handlers

If you want more control over the response structure, you can define custom handlers. Use the `RESPONSE_SHAPER` settings to specify the paths to your custom handlers.

For example, define a custom success handler in `myapp.responses`:

```python
# myapp/responses.py
from rest_framework.response import Response

def custom_success_handler(response):
    return Response({
        "custom_status": "success",
        "code": response.status_code,
        "payload": response.data
    }, status=response.status_code)
```

Then configure this handler in your settings:

```python
CUSTOM_RESPONSE_SUCCESS_HANDLER = "path.of_your.custom_success_handler"
```

## Built-In Response Types

- **Standard API Response**:
  - `api_response(success: bool = True, message: str = None, data: dict = None, errors: dict = None, status_code: int = 200) -> Response`

- **Paginated Response**:
  - `paginated_api_response(success: bool = True, data: list = None, page: int = None, total_pages: int = None, total_items: int = None, status_code: int = 200) -> Response`

- **Error Response**:
  - `error_api_response(message: str = None, errors: dict = None, error_code: str = None, status_code: int = 400) -> Response`

- **Minimal Success Response**:
  - `minimal_success_response(message: str = "Request successful", status_code: int = 200) -> Response`

- **Batch Operation Response**:
  - `batch_api_response(success: bool = True, results: list = None, errors: dict = None, status_code: int = 200) -> Response`

- **Authentication Response**:
  - `auth_api_response(success: bool = True, message: str = None, token: str = None, user: dict = None, errors: dict = None, status_code: int = 200) -> Response`

## Exception Handling

The middleware automatically handles Django exceptions and structures error responses for common errors:

- `ObjectDoesNotExist` -> 404 Not Found
- `IntegrityError` -> 400 Bad Request
- `ValidationError` -> 400 Bad Request
- Generic exceptions -> 500 Internal Server Error

You can customize the exception response format by providing custom error handlers via the `RESPONSE_SHAPER` configuration.

## Contributing

Contributions are welcome! If you find any issues or want to add new features, feel free to create a pull request or open an issue on the repository.

## License

This package is licensed under the MIT License.
