from django.conf import settings


class ResponseShaperConfig:
    """A configuration handler.allowing dynamic settings loading from the
    Django settings, with default fallbacks."""

    def __init__(self):
        self.debug = self.get_setting("CUSTOM_RESPONSE_DEBUG", False)
        self.excluded_paths = self.get_setting(
            "CUSTOM_RESPONSE_EXCLUDED_PATHS",
            ["/admin/", "/schema/swagger-ui/", "/schema/redoc/", "/schema/"],
        )
        self.success_handler = self.get_setting(
            "CUSTOM_RESPONSE_SUCCESS_HANDLER", "default_success_handler"
        )
        self.error_handler = self.get_setting(
            "CUSTOM_RESPONSE_ERROR_HANDLER", "default_error_handler"
        )

    def get_setting(self, setting_name, default_value):
        """Retrieve a setting from Django settings with a default fallback."""
        return getattr(settings, setting_name, default_value)


# Create a global config object
response_shaper_config = ResponseShaperConfig()
