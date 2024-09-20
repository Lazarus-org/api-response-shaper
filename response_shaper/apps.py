from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class ResponseShaperConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "response_shaper"
    verbose_name = _("Response Shaper")
