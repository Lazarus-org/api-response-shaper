from typing import Any, List

from django.core.checks import Error
from django.utils.module_loading import import_string

BUILTIN_ERROR_EXTRACTION_STRATEGIES = {"first", "smart", "full"}
LEGACY_DEFAULT_HANDLER_PATHS = {"default_success_handler", "default_error_handler"}


def validate_boolean_setting(setting_value: Any, setting_name: str) -> List[Error]:
    errors: List[Error] = []
    if setting_value is None or not isinstance(setting_value, bool):
        errors.append(
            Error(
                f"{setting_name} should be a boolean value.",
                hint=f"Set {setting_name} to either True or False.",
                id=f"response_shaper.E001.{setting_name}",
            )
        )
    return errors


def validate_class_setting(setting_value: Any, setting_name: str) -> List[Error]:
    """Validate an optional dotted path to a callable response handler."""
    if setting_value is None or setting_value == "":
        return []

    if not isinstance(setting_value, str):
        return [
            Error(
                f"{setting_name} should be a valid Python callable path string.",
                hint=f"Set {setting_name} to a dotted import path for a callable.",
                id=f"response_shaper.E002.{setting_name}",
            )
        ]

    if setting_value in LEGACY_DEFAULT_HANDLER_PATHS:
        return []

    try:
        configured = import_string(setting_value)
    except (ImportError, AttributeError) as exc:
        return [
            Error(
                f"{setting_name} could not be imported: {exc}",
                hint=f"Set {setting_name} to an importable dotted callable path.",
                id=f"response_shaper.E008.{setting_name}",
            )
        ]

    if not callable(configured):
        return [
            Error(
                f"{setting_name} must resolve to a callable.",
                hint=f"Set {setting_name} to a callable function or class.",
                id=f"response_shaper.E009.{setting_name}",
            )
        ]

    return []


def validate_error_extraction_setting(
    setting_value: Any, setting_name: str
) -> List[Error]:
    """Validate a built-in extraction strategy or custom callable path."""
    if not isinstance(setting_value, str) or not setting_value:
        return [
            Error(
                f"{setting_name} should be a non-empty string.",
                hint=(
                    f"Set {setting_name} to 'first', 'smart', 'full', or a "
                    "dotted Python path to a custom extractor callable."
                ),
                id=f"response_shaper.E006.{setting_name}",
            )
        ]

    if setting_value in BUILTIN_ERROR_EXTRACTION_STRATEGIES:
        return []

    if "." not in setting_value:
        return [
            Error(
                f"{setting_name} contains an unknown extraction strategy.",
                hint=(
                    f"Set {setting_name} to 'first', 'smart', 'full', or a "
                    "dotted Python path to a custom extractor callable."
                ),
                id=f"response_shaper.E007.{setting_name}",
            )
        ]

    try:
        extractor = import_string(setting_value)
    except (ImportError, AttributeError) as exc:
        return [
            Error(
                f"{setting_name} could not be imported: {exc}",
                hint=f"Set {setting_name} to an importable dotted callable path.",
                id=f"response_shaper.E010.{setting_name}",
            )
        ]

    if not callable(extractor):
        return [
            Error(
                f"{setting_name} must resolve to a callable.",
                hint=f"Set {setting_name} to a callable function or class.",
                id=f"response_shaper.E011.{setting_name}",
            )
        ]

    return []


def validate_paths_list_setting(setting_value: Any, setting_name: str) -> List[Error]:
    errors: List[Error] = []
    if not isinstance(setting_value, list):
        errors.append(
            Error(
                f"{setting_name} should be a list.",
                hint=f"Set {setting_name} to a list of strings, e.g., ['/admin/', '/schema/swagger-ui/']",
                id=f"response_shaper.E003.{setting_name}",
            )
        )
    elif not all(isinstance(path, str) for path in setting_value):
        errors.append(
            Error(
                f"All items in {setting_name} should be strings.",
                hint="Ensure each path is a valid string.",
                id=f"response_shaper.E004.{setting_name}",
            )
        )
    else:
        for path in setting_value:
            if not (path.startswith("/") and path.endswith("/")):
                errors.append(
                    Error(
                        f"The path '{path}' in {setting_name} should start and end with a '/'.",
                        hint="Ensure each path in the list starts and ends with '/'.",
                        id=f"response_shaper.E005.{setting_name}",
                    )
                )
    return errors
