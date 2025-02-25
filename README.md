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


## Project Detail

- Language: Python >= 3.9
- Framework: Django >= 4.2
- Django REST Framework: >= 3.14


## Documentation

The documentation is organized into the following sections:

- [Installation](#installation)
- [Usage](#usage)
- [Settings](#settings)
- [Available Format Options](#available-format-options)
- [Required Email Settings](#required-email-settings)


## Setup
Setting up the `api-response-shaper` is simple, folow these steps to setup:

1. **Install the Package**:

To install the `api-response-shaper`, simply use pip:

```bash
$ pip install api-response-shaper
```

2. **Add to Installed Apps**

Add `response_shaper` to your `INSTALLED_APPS` in your Django settings file:

```python
INSTALLED_APPS = [
    # ...
    'response_shaper',
    # ...
]
```

3. **Configure Middleware**:

Add `DynamicResponseMiddleware` middleware to the MIDDLEWARE list in your Django `settings.py`:

```python
MIDDLEWARE = [
    # ...
    'response_shaper.middleware.DynamicResponseMiddleware',
    # ...
]
```
Once this middleware is added, all API responses will be dynamically structured. Whether it's a successful or an error response, the middleware ensures a consistent format across your API endpoints.
You can customize the response format using settings or decorators for specific views, but by default, this middleware provides a standardized API response format.
You can also configure the `api-response-shaper` for your project needs, for more details, please refer to the [Settings](#settings) section.

----

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
from rest_framework.response import Response
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

If you want more control over the response structure, you can define custom handlers. Use the `RESPONSE_SHAPER` settings to specify the paths to your custom handlers. for more details, please refer to the [Settings](#settings).

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
RESPONSE_SHAPER_SUCCESS_HANDLER = "path.to_your.custom_success_handler"
```

----

## Built-In Response Types

- **Standard API Response**:
```shell
api_response(
  success: bool = True,
  message: str = None,
  data: dict = None,
  errors: dict = None,
  status_code: int = 200
) -> Response
```

---

- **Paginated Response**:

```shell
paginated_api_response(
  success: bool = True,
  data: list = None,
  page: int = None,
  total_pages: int = None,
  total_items: int = None,
  status_code: int = 200
) -> Response
```

---

- **Error Response**:
```shell
error_api_response(
  message: str = None,
  errors: dict = None,
  error_code: str = None,
  status_code: int = 400
) -> Response
```

---

- **Minimal Success Response**:
```shell
minimal_success_response(
  message: str = "Request successful",
  status_code: int = 200
) -> Response
```

---

- **Batch Operation Response**:

```shell
batch_api_response(
  success: bool = True,
  results: list = None,
  errors: dict = None,
  status_code: int = 200
) -> Response`
```

---

- **Authentication Response**:

```shell
auth_api_response(
  success: bool = True,
  message: str = None,
  token: str = None,
  user: dict = None,
  errors: dict = None,
  status_code: int = 200
) -> Response
```

----

## DynamicResponseMiddleware

The `DynamicResponseMiddleware` is designed to structure API responses in a consistent format for both **synchronous** and **asynchronous** workflows.
It ensures that all responses, whether successful or erroneous, follow a standardized JSON structure.
This middleware is highly configurable and supports custom handlers for success and error responses.

### Key Features

- **Consistent Response Format**: Ensures all API responses follow a standardized structure, making it easier for clients to parse and handle responses.
- **Async Support**: Seamlessly handles both synchronous and asynchronous requests, ensuring compatibility with Django's ASGI stack.
- **Exception Handling**: Automatically catches and processes Django exceptions, returning structured error responses.
- **Customizable Handlers**: Allows customization of success and error response formats via the `RESPONSE_SHAPER` configuration.

---

## Exception Handling

The middleware automatically handles Django exceptions and structures error responses for both **synchronous** and **asynchronous** workflows.
It ensures consistent error responses for a wide range of exceptions, including:

### Common Exceptions

- **404 Not Found**:
  - `ObjectDoesNotExist`: The requested object was not found.
  - `FieldDoesNotExist`: The requested field does not exist.
  - `EmptyResultSet`: No results were found for the query.

- **400 Bad Request**:
  - `MultipleObjectsReturned`: Multiple objects were returned when only one was expected.
  - `SuspiciousOperation`: A suspicious operation was detected (e.g., security issues).
  - `DisallowedHost`: The request's host header is invalid or disallowed.
  - `DisallowedRedirect`: The request attempted a disallowed redirect.
  - `BadRequest`: A generic bad request error occurred.
  - `FieldError`: An error occurred with a field in the request.
  - `ValidationError`: Validation of the request data failed.
  - `IntegrityError`: A database integrity constraint was violated.
  - `DataError`: Invalid data was provided to the database.

- **403 Forbidden**:
  - `PermissionDenied`: The user does not have permission to perform the requested action.

- **500 Internal Server Error**:
  - `MiddlewareNotUsed`: A middleware component was not used.
  - `ImproperlyConfigured`: The application is improperly configured.
  - `ProgrammingError`: A database programming error occurred.
  - `OperationalError`: A database operational error occurred.
  - `InternalError`: An internal database error occurred.
  - `DatabaseError`: A generic database error occurred.
  - Generic exceptions: Any unexpected exception is caught and returned as a 500 error.

### Async Support for Exception Handling

With the addition of async support, the middleware now seamlessly handles exceptions in asynchronous contexts.
The `ExceptionHandler` class processes exceptions and returns structured JSON responses,
whether the request is synchronous or asynchronous. For example:

- **Synchronous Workflow**: Exceptions are caught and processed in the `process_exception` method.
- **Asynchronous Workflow**: Exceptions are handled in the same way, ensuring consistent error responses across both sync and async views.

----

## Settings

In this section, we dive deep into the settings configuration and defaults.

#### Default configuration:

Here are the default settings that are automatically applied:

```python
# settings.py

RESPONSE_SHAPER_DEBUG_MODE = False
RESPONSE_SHAPER_RETURN_ERROR_AS_DICT = True
RESPONSE_SHAPER_EXCLUDED_PATHS = ["/admin/", "/schema/swagger-ui/", "/schema/redoc/", "/schema/"]
RESPONSE_SHAPER_SUCCESS_HANDLER = ""
RESPONSE_SHAPER_ERROR_HANDLER = ""

```

`RESPONSE_SHAPER_DEBUG_MODE`
----------------------------

- **Type**: `bool`
- **Description**: When set to `True`, disables response shaping for debugging purposes.
- **Default**: `False`

`RESPONSE_SHAPER_RETURN_ERROR_AS_DICT`
--------------------------------------

- **Type**: `bool`
- **Description**: Controls the format of dict error messages extracted by the ExceptionHandler. When `True`, errors with **nested dictionary** structure are returned as a dictionary containing the innermost key-value pair from nested error structures. When `False`, only the innermost error message is returned as a string. This applies to error responses shaped by the handler, particularly for validation.
- **Default**: `True`

**Example**:
```python
# With RESPONSE_SHAPER_RETURN_ERROR_AS_DICT = True
error_input = {"field": {"detail": {"code": "invalid"}}}
# Result: {"code": "invalid"}

# With RESPONSE_SHAPER_RETURN_ERROR_AS_DICT = False
error_input = {"field": {"detail": {"code": "invalid"}}}
# Result: "invalid"
```

`RESPONSE_SHAPER_EXCLUDED_PATHS`
--------------------------------

- **Type**: `List[str]`
- **Description**: A list of URL paths where the middleware will not shape responses. This is useful for excluding admin or documentation routes from being processed, ensuring that those paths retain their original behavior.
- **Default**: `["/admin/", "/schema/swagger-ui/", "/schema/redoc/", "/schema/"]`


`RESPONSE_SHAPER_SUCCESS_HANDLER`
---------------------------------

- **Type**: `str`
- **Description**: Path to the custom handler to manage successful responses. you can specify a custom handler if you want to modify the success response format.
- **Default**: Default Success handler in `DynamicResponseMiddleware`

`RESPONSE_SHAPER_ERROR_HANDLER`
-------------------------------

- **Type**: `str`
- **Description**: Path to the custom handler to manage error responses. Similar to the success handler, it allows you to provide your own handler to modify the error response format if the default behavior does not meet your needs.
- **Default**: Default Error handler in `DynamicResponseMiddleware`


Thank you for using `api-response-shaper`. We hope this package enhances your Django application's API responses. If you have any questions or issues, feel free to open an issue on our [GitHub repository](https://github.com/lazarus-org/api-response-shaper).
