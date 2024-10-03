from typing import Any, List

from django.core.checks import Error, register


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


@register()
def check_response_shaper_settings(app_configs: Any, **kwargs: Any) -> List[Error]:
    """Check and validate middleware settings in the Django configuration.

    This function registers as a system check in Django to validate custom settings.

    Args:
        app_configs: Unused argument, provided by Django system check framework.
        kwargs: Additional keyword arguments passed by Django system check framework.

    Returns:
        List[Error]: A list of validation errors for the custom settings, or an empty list if all settings are valid.

    """
    errors: List[Error] = []

    from django.conf import settings

    # Validate boolean settings
    errors.extend(
        validate_boolean_setting(
            getattr(settings, "CUSTOM_RESPONSE_DEBUG", None), "CUSTOM_RESPONSE_DEBUG"
        )
    )

    # Validate optional class settings for custom handlers (skip validation if the setting is None or empty)
    errors.extend(
        validate_class_setting(
            getattr(settings, "CUSTOM_RESPONSE_SUCCESS_HANDLER", None),
            "CUSTOM_RESPONSE_SUCCESS_HANDLER",
        )
    )

    errors.extend(
        validate_class_setting(
            getattr(settings, "CUSTOM_RESPONSE_ERROR_HANDLER", None),
            "CUSTOM_RESPONSE_ERROR_HANDLER",
        )
    )

    return errors
