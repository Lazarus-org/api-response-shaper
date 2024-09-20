from django.conf import settings
import django


def configure_django_settings():
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
            ],
            LANGUAGE_CODE="en-us",
            TIME_ZONE="UTC",
            USE_I18N=True,
            USE_TZ=True,
        )
        django.setup()

configure_django_settings()