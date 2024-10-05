from typing import Any, List

from django.core.checks import Error, register

from response_shaper.settings.conf import response_shaper_config
from response_shaper.validators.config_validators import (
    validate_boolean_setting,
    validate_class_setting,
    validate_paths_list_setting,
)


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

    # Validate boolean settings
    errors.extend(
        validate_boolean_setting(
            response_shaper_config.debug, "RESPONSE_SHAPER_DEBUG_MODE"
        )
    )

    # Validate optional excluded path settings
    errors.extend(
        validate_paths_list_setting(
            response_shaper_config.excluded_paths, "RESPONSE_SHAPER_EXCLUDED_PATHS"
        )
    )

    # Validate optional class settings for custom handlers (skip validation if the setting is None or empty)
    errors.extend(
        validate_class_setting(
            response_shaper_config.success_handler,
            "RESPONSE_SHAPER_SUCCESS_HANDLER",
        )
    )

    errors.extend(
        validate_class_setting(
            response_shaper_config.error_handler,
            "RESPONSE_SHAPER_ERROR_HANDLER",
        )
    )

    return errors
