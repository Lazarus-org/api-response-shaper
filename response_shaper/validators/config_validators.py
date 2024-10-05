from typing import Any, List

from django.core.checks import Error


def validate_boolean_setting(setting_value: Any, setting_name: str) -> List[Error]:
    """Helper function to validate boolean settings.

    Args:
        setting_value: The value of the setting to validate.
        setting_name: The name of the setting being validated.

    Returns:
        List[Error]: A list of errors if the validation fails, or an empty list if valid.

    """
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
    """Helper function to validate settings that are class paths (strings).

    Args:
        setting_value: The value of the setting to validate.
        setting_name: The name of the setting being validated.

    Returns:
        List[Error]: A list of errors if the validation fails, or an empty list if valid.

    """
    errors: List[Error] = []
    # Only validate if the setting is not empty (since an empty string is allowed)
    if (
        setting_value is not None
        and setting_value != ""
        and not isinstance(setting_value, str)
    ):
        errors.append(
            Error(
                f"{setting_name} should be a valid Python class path string.",
                hint=f"Set {setting_name} to a valid import path for a class.",
                id=f"response_shaper.E002.{setting_name}",
            )
        )
    return errors


def validate_paths_list_setting(setting_value: Any, setting_name: str) -> List[Error]:
    """Validates that the given setting is a list of paths, ensuring each path
    is a string and starts and ends with a forward slash ('/').

    Args:
        setting_value (Any): The value of the setting to validate, expected to be a list of strings.
        setting_name (str): The name of the setting being validated.

    Returns:
        List[Error]: A list of errors if the validation fails, or an empty list if valid.

    Validation Criteria:
    - The setting must be a list.
    - Each item in the list must be a string.
    - Each path must start and end with a forward slash ('/').

    Example:
        A valid setting: ['/admin/', '/schema/swagger-ui/']
        An invalid setting: ['admin', '/schema/swagger-ui', '/schema']

    """
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
