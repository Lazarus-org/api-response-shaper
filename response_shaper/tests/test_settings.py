import sys
from unittest.mock import MagicMock, patch

import pytest

from response_shaper.settings.check import check_response_shaper_settings
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.settings,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


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
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = "myapp.handlers.custom_success_handler"
        mock_config.error_handler = "myapp.handlers.custom_error_handler"

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
        mock_config.excluded_paths = {}  # must be a list
        mock_config.success_handler = "myapp.handlers.custom_success_handler"
        mock_config.error_handler = "myapp.handlers.custom_error_handler"

        # Run check and assert there is an error
        errors = check_response_shaper_settings(None)
        assert len(errors) == 2
        assert errors[0].id == "response_shaper.E001.RESPONSE_SHAPER_DEBUG_MODE"
        assert "should be a boolean value" in errors[0].msg

        mock_config.excluded_paths = [1, 2]
        errors = check_response_shaper_settings(None)

        assert len(errors) == 2

        mock_config.excluded_paths = ["admin"]  # path without /
        errors = check_response_shaper_settings(None)

        assert len(errors) == 2

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
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = 123  # invalid type
        mock_config.error_handler = 456  # invalid type

        # Run check and assert errors for invalid class paths
        errors = check_response_shaper_settings(None)
        assert len(errors) == 2
        assert errors[0].id == "response_shaper.E002.RESPONSE_SHAPER_SUCCESS_HANDLER"
        assert errors[1].id == "response_shaper.E002.RESPONSE_SHAPER_ERROR_HANDLER"
        assert "should be a valid Python class path string" in errors[0].msg

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
        mock_config.excluded_paths = ["/admin/"]
        mock_config.success_handler = None  # Optional and valid
        mock_config.error_handler = ""  # Empty string is valid

        # Run check and assert no errors for missing optional settings
        errors = check_response_shaper_settings(None)
        assert not errors  # No errors should be returned
