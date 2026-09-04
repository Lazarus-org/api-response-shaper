import sys
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ImproperlyConfigured

from response_shaper.middleware import DynamicResponseMiddleware
from response_shaper.settings.check import check_response_shaper_settings
from response_shaper.settings.conf import response_shaper_config
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.settings,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


@pytest.mark.parametrize("handler_setting", ["success_handler", "error_handler"])
def test_non_string_handler_rejected_before_serving_requests(
    monkeypatch, handler_setting
):
    monkeypatch.setattr(response_shaper_config, handler_setting, 42)
    errors = check_response_shaper_settings(None)
    assert [error.id for error in errors] == [
        f"response_shaper.E002.RESPONSE_SHAPER_{handler_setting.upper()}"
    ]
    get_response = MagicMock()
    with pytest.raises(ImproperlyConfigured, match="dotted Python paths"):
        DynamicResponseMiddleware(get_response)
    get_response.assert_not_called()


@pytest.mark.parametrize("handler_setting", ["success_handler", "error_handler"])
def test_legacy_handler_sentinel_passes_system_check(monkeypatch, handler_setting):
    monkeypatch.setattr(
        response_shaper_config, handler_setting, f"default_{handler_setting}"
    )
    assert check_response_shaper_settings(None) == []


def test_real_custom_extractor_passes_system_check(monkeypatch):
    monkeypatch.setattr(
        response_shaper_config,
        "error_extraction",
        "response_shaper.tests.test_release_validation.extract_messages",
    )
    assert check_response_shaper_settings(None) == []


class TestResponseShaperSettings:
    @patch("response_shaper.settings.check.response_shaper_config")
    def test_valid_settings(self, mock_config: MagicMock) -> None:
        """
        Test that valid settings produce no errors.

        This test mocks valid configurations for `RESPONSE_SHAPER_DEBUG_MODE`,
        `RESPONSE_SHAPER_SUCCESS_HANDLER`, and `RESPONSE_SHAPER_ERROR_HANDLER`.
        It ensures that the check returns no errors when the settings are correct.

        :param mock_config: Mock of the response shaper configuration.
        """
        # Mock valid configuration values
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = "smart"
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = ""
        mock_config.error_handler = ""

        # Run check and assert no errors
        errors = check_response_shaper_settings(None)
        assert not errors  # No errors should be returned for valid settings

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_invalid_settings(self, mock_config: MagicMock) -> None:
        """
        Test that invalid settings return errors.

        This test mocks an invalid configuration for `RESPONSE_SHAPER_DEBUG_MODE`
         and `RESPONSE_SHAPER_EXCLUDED_PATHS`.
        It ensures that the check returns an error if the settings is not valid.

        :param mock_config: Mock of the response shaper configuration.
        """
        # Mock invalid settings
        mock_config.debug = "invalid_bool"  # must be bool
        mock_config.return_dict_error = "invalid_bool"  # must be bool
        mock_config.error_extraction = "first"
        mock_config.excluded_paths = {}  # must be a list
        mock_config.success_handler = ""
        mock_config.error_handler = ""

        # Run check and assert there is an error
        errors = check_response_shaper_settings(None)
        assert len(errors) == 3
        assert errors[0].id == "response_shaper.E001.RESPONSE_SHAPER_DEBUG_MODE"
        assert "should be a boolean value" in errors[0].msg

        mock_config.excluded_paths = [1, 2]
        errors = check_response_shaper_settings(None)

        assert len(errors) == 3

        mock_config.excluded_paths = ["admin"]  # path without /
        errors = check_response_shaper_settings(None)

        assert len(errors) == 3

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_invalid_class_path_settings(self, mock_config: MagicMock) -> None:
        """
        Test that invalid class paths return errors.

        This test mocks invalid class path settings for `RESPONSE_SHAPER_SUCCESS_HANDLER`
        and `RESPONSE_SHAPER_ERROR_HANDLER`. It ensures that the check returns errors if
        these settings are not valid Python class paths.

        :param mock_config: Mock of the response shaper configuration.
        """
        # Mock invalid class path settings
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = "first"
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = 123  # invalid type
        mock_config.error_handler = 456  # invalid type

        # Run check and assert errors for invalid class paths
        errors = check_response_shaper_settings(None)
        assert len(errors) == 2
        assert errors[0].id == "response_shaper.E002.RESPONSE_SHAPER_SUCCESS_HANDLER"
        assert errors[1].id == "response_shaper.E002.RESPONSE_SHAPER_ERROR_HANDLER"
        assert "should be a valid Python callable path string" in errors[0].msg

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_missing_optional_settings(self, mock_config: MagicMock) -> None:
        """
        Test that missing optional settings return no errors.

        This test mocks valid optional settings by assigning `None` and an empty
        string to `RESPONSE_SHAPER_SUCCESS_HANDLER` and `RESPONSE_SHAPER_ERROR_HANDLER`,
        respectively. It ensures that no errors are returned for missing optional settings.

        :param mock_config: Mock of the response shaper configuration.
        """
        # Mock valid optional settings (None or empty)
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = "first"
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = None  # Optional and valid
        mock_config.error_handler = ""  # Empty string is valid

        # Run check and assert no errors for missing optional settings
        errors = check_response_shaper_settings(None)
        assert not errors  # No errors should be returned

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_invalid_error_extraction_setting(self, mock_config: MagicMock) -> None:
        """Unknown extraction strategies should fail the Django system check."""
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = "unknown"
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = ""
        mock_config.error_handler = ""

        errors = check_response_shaper_settings(None)

        assert len(errors) == 1
        assert errors[0].id == "response_shaper.E007.RESPONSE_SHAPER_ERROR_EXTRACTION"

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_non_string_error_extraction_setting(self, mock_config: MagicMock) -> None:
        """Extraction strategy must be a non-empty string."""
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = None
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = ""
        mock_config.error_handler = ""

        errors = check_response_shaper_settings(None)

        assert len(errors) == 1
        assert errors[0].id == "response_shaper.E006.RESPONSE_SHAPER_ERROR_EXTRACTION"

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_importable_callable_handler_settings(self, mock_config: MagicMock) -> None:
        """Importable callable handler paths should pass the system check."""
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = "first"
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = "response_shaper.responses.api_response"
        mock_config.error_handler = "response_shaper.responses.error_api_response"

        assert check_response_shaper_settings(None) == []

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_missing_handler_path_fails_system_check(
        self, mock_config: MagicMock
    ) -> None:
        """A configured handler path must be importable."""
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = "first"
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = "response_shaper.missing.handler"
        mock_config.error_handler = ""

        errors = check_response_shaper_settings(None)

        assert len(errors) == 1
        assert errors[0].id == "response_shaper.E008.RESPONSE_SHAPER_SUCCESS_HANDLER"

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_non_callable_handler_path_fails_system_check(
        self, mock_config: MagicMock
    ) -> None:
        """A configured handler path must resolve to a callable."""
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = "first"
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = "response_shaper.tests.constants.PYTHON_VERSION"
        mock_config.error_handler = ""

        errors = check_response_shaper_settings(None)

        assert len(errors) == 1
        assert errors[0].id == "response_shaper.E009.RESPONSE_SHAPER_SUCCESS_HANDLER"

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_missing_custom_extractor_fails_system_check(
        self, mock_config: MagicMock
    ) -> None:
        """A custom extractor path must be importable."""
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = "response_shaper.missing.extractor"
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = ""
        mock_config.error_handler = ""

        errors = check_response_shaper_settings(None)

        assert len(errors) == 1
        assert errors[0].id == "response_shaper.E010.RESPONSE_SHAPER_ERROR_EXTRACTION"

    @patch("response_shaper.settings.check.response_shaper_config")
    def test_non_callable_custom_extractor_fails_system_check(
        self, mock_config: MagicMock
    ) -> None:
        """A custom extractor path must resolve to a callable."""
        mock_config.debug = True
        mock_config.return_dict_error = True
        mock_config.error_extraction = "response_shaper.tests.constants.PYTHON_VERSION"
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = ""
        mock_config.error_handler = ""

        errors = check_response_shaper_settings(None)

        assert len(errors) == 1
        assert errors[0].id == "response_shaper.E011.RESPONSE_SHAPER_ERROR_EXTRACTION"
