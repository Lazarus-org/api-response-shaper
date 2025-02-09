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
