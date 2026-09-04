from typing import Any

from django.conf import settings


class ResponseShaperConfig:
    """A configuration handler.

    allowing dynamic settings loading from the Django settings, with
    default fallbacks.

    """

    def __init__(self) -> None:
        self.config_prefix = "RESPONSE_SHAPER_"
        self.debug = self.get_setting(f"{self.config_prefix}DEBUG_MODE", False)
        self.return_dict_error = self.get_setting(
            f"{self.config_prefix}RETURN_ERROR_AS_DICT", True
        )
        self.error_extraction = self.get_setting(
            f"{self.config_prefix}ERROR_EXTRACTION", "first"
        )
        self.excluded_paths = self.get_setting(
            f"{self.config_prefix}EXCLUDED_PATHS",
            ["/admin/", "/schema/swagger-ui/", "/schema/redoc/", "/schema/"],
        )
        self.success_handler = self.get_setting(
            f"{self.config_prefix}SUCCESS_HANDLER", ""
        )
        self.error_handler = self.get_setting(f"{self.config_prefix}ERROR_HANDLER", "")

    def get_setting(self, setting_name: str, default_value: Any) -> Any:
        """Retrieve a setting from Django settings with a default fallback."""
        return getattr(settings, setting_name, default_value)


# Create a global config object
response_shaper_config: ResponseShaperConfig = ResponseShaperConfig()
