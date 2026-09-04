## Unreleased

### Changed

- **compatibility**: drop Python 3.9, Django 4.2/5.0/5.1, and DRF 3.14-3.17; require Python 3.10-3.13, Django 5.2 LTS, and DRF 3.18 (including its dictionary-shaped list serializer errors)

### Feat

- **exceptions**: add configurable `first`, `smart`, `full`, and custom error extraction strategies
- **exceptions**: preserve flat structured error payloads in `smart` mode without relying on reserved key names
- **middleware**: support synchronous and asynchronous custom success/error handlers in both sync and async middleware modes
- **decorators**: preserve async execution for decorated async views

### Fix

- **validation**: avoid corrupting non-UTF-8 JSON and preserve custom `JsonResponse` subclass content by limiting byte wrapping to plain UTF-8 responses
- **validation**: invalidate `Content-Digest` and `Repr-Digest` when shaping changes the body
- **validation**: recognize callable objects with async `__call__` methods when adapting custom handlers
- **ci**: run the pytest hook in the installed Python environment and make Bandit select Python source files
- **exceptions**: preserve structured Django `ValidationError` messages for `smart`, `full`, and custom extractors while retaining legacy `first` behavior
- **exceptions**: preserve atomic mapping identity/type and non-string leaves in `smart` extraction
- **exceptions**: resolve subclass exceptions using the nearest configured class in the exception MRO
- **middleware**: handle plain JSON error dictionaries, arrays, and scalars without dropping or crashing on their payloads
- **middleware**: bypass streaming, bodyless-status, content-encoded, and non-`application/json` responses safely
- **middleware**: preserve valid headers/cookies and invalidate stale body-derived metadata after shaping
- **middleware**: keep DRF's negotiated renderer and response object when shaping DRF responses
- **middleware**: prevent package-owned decorator/helper responses from being shaped twice
- **settings**: fail fast for explicit handler/extractor paths that cannot be imported or are not callable
- **responses**: set `Location` for redirects and `Retry-After` for rate-limited responses when supplied
- **ci**: correct coverage target and add an explicit Python/Django/DRF compatibility matrix

### Performance

- **middleware**: envelope successful Django `JsonResponse` bodies directly instead of parsing and re-serializing the already-valid JSON payload

## v1.2.1 (2025-02-26)

### Fix

- **exceptions**: `extract_first_error` returns string or dict-type errors dynamically from settings

### Refactor

- **exceptions**: Enhance `extract_first_error` for nested dicts to return one key-value pair

## v1.2.0 (2025-02-10)

### Feat

- **middleware**: Add async support to DynamicResponseMiddleware
- **exceptions**: Add centralized ExceptionHandler class for consistent error responses

## v1.1.0 (2024-10-13)

### ✨ Features
- **chore(python)**: Add support for Python 3.13 and drop support for Python 3.8. ([8fead45](https://github.com/MEHRSHAD-MIRSHEKARY/api-response-shaper/commit/8fead45))
  - Updated the project configuration to support Python 3.13 while removing compatibility with Python 3.8.
  - This change ensures compatibility with the latest Python release and removes support for outdated versions.
  - **Closes #24**.

### 🐛 Bug Fixes
- **fix(tests)**: Update required PYTHON_VERSION for running tests. ([7094071](https://github.com/MEHRSHAD-MIRSHEKARY/api-response-shaper/commit/7094071))
  - Modified test constants to reflect the new required Python version (3.13) for running tests.
  - Ensured test compatibility with Python 3.13 for smoother CI/CD pipelines.

### 🔀 Merged
- **Merge PR #25**: Add support for Python 3.13 and drop support for Python 3.8. ([f974a8b](https://github.com/Lazarus-org/api-response-shaper/commit/f974a8b))
  - This merge includes the changes for Python 3.13 compatibility and marks the official transition from Python 3.8.

## v1.0.0 (2024-10-7)
- 🎉initial Release
