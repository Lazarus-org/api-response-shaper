from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ResponseShaperConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "response_shaper"
    verbose_name = _("Response Shaper")

    def ready(self) -> None:
        """Import and register system checks for the Response Shaper app.

        This method is called when the app is ready and ensures that the settings
        checks from `response_shaper.settings.check` are imported. This allows
        Django's system check framework to validate the Response Shaper configuration during
        startup.

        """
        from response_shaper.settings import check
