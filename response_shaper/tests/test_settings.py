import pytest
import sys
from django.core.checks import Error
from django.conf import settings
from unittest.mock import patch, MagicMock
from response_shaper.settings.check import check_response_shaper_settings
from response_shaper.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.settings,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]

class TestResponseShaperSettings:
    @patch("django.conf.settings")
    def test_valid_settings(self, mock_settings: MagicMock) -> None:
        """
        Test that valid settings produce no errors.

        This test mocks valid configurations for `CUSTOM_RESPONSE_DEBUG`, 
        `CUSTOM_RESPONSE_SUCCESS_HANDLER`, and `CUSTOM_RESPONSE_ERROR_HANDLER`. 
        It ensures that the check returns no errors when the settings are correct.
        
        :param mock_settings: Mock of Django settings.
        """
        # Mock valid configuration values
        mock_settings.CUSTOM_RESPONSE_DEBUG = True
        mock_settings.CUSTOM_RESPONSE_SUCCESS_HANDLER = "myapp.handlers.CustomSuccessHandler"
        mock_settings.CUSTOM_RESPONSE_ERROR_HANDLER = "myapp.handlers.CustomErrorHandler"

        # Run check and assert no errors
        errors = check_response_shaper_settings(None)
        assert not errors  # No errors should be returned for valid settings

    @patch("django.conf.settings")
    def test_invalid_boolean_settings(self, mock_settings: MagicMock) -> None:
        """
        Test that invalid boolean settings return errors.

        This test mocks an invalid boolean configuration for `CUSTOM_RESPONSE_DEBUG`. 
        It ensures that the check returns an error if the setting is not a boolean value.
        
        :param mock_settings: Mock of Django settings.
        """
        # Mock invalid boolean settings
        mock_settings.CUSTOM_RESPONSE_DEBUG = "invalid_bool"  # Should be bool
        mock_settings.CUSTOM_RESPONSE_SUCCESS_HANDLER = "myapp.handlers.CustomSuccessHandler"
        mock_settings.CUSTOM_RESPONSE_ERROR_HANDLER = "myapp.handlers.CustomErrorHandler"

        # Run check and assert there is an error
        errors = check_response_shaper_settings(None)
        assert len(errors) == 1
        assert errors[0].id == "response_shaper.E001.CUSTOM_RESPONSE_DEBUG"
        assert "should be a boolean value" in errors[0].msg

    @patch("django.conf.settings")
    def test_invalid_class_path_settings(self, mock_settings: MagicMock) -> None:
        """
        Test that invalid class paths return errors.

        This test mocks invalid class path settings for `CUSTOM_RESPONSE_SUCCESS_HANDLER`
        and `CUSTOM_RESPONSE_ERROR_HANDLER`. It ensures that the check returns errors if 
        these settings are not valid Python class paths.
        
        :param mock_settings: Mock of Django settings.
        """
        # Mock invalid class path settings
        mock_settings.CUSTOM_RESPONSE_DEBUG = True
        mock_settings.CUSTOM_RESPONSE_SUCCESS_HANDLER = 123  # Should be string
        mock_settings.CUSTOM_RESPONSE_ERROR_HANDLER = 456  # Should be string

        # Run check and assert errors for invalid class paths
        errors = check_response_shaper_settings(None)
        assert len(errors) == 2
        assert errors[0].id == "response_shaper.E002.CUSTOM_RESPONSE_SUCCESS_HANDLER"
        assert errors[1].id == "response_shaper.E002.CUSTOM_RESPONSE_ERROR_HANDLER"
        assert "should be a valid Python class path string" in errors[0].msg

    @patch("django.conf.settings")
    def test_missing_optional_settings(self, mock_settings: MagicMock) -> None:
        """
        Test that missing optional settings return no errors.

        This test mocks valid optional settings by assigning `None` and an empty 
        string to `CUSTOM_RESPONSE_SUCCESS_HANDLER` and `CUSTOM_RESPONSE_ERROR_HANDLER`, 
        respectively. It ensures that no errors are returned for missing optional settings.
        
        :param mock_settings: Mock of Django settings.
        """
        # Mock valid optional settings (None or empty)
        mock_settings.CUSTOM_RESPONSE_DEBUG = True
        mock_settings.CUSTOM_RESPONSE_SUCCESS_HANDLER = None  # Optional and valid
        mock_settings.CUSTOM_RESPONSE_ERROR_HANDLER = ""  # Empty string is valid

        # Run check and assert no errors for missing optional settings
        errors = check_response_shaper_settings(None)
        assert not errors  # No errors should be returned

    @patch("django.conf.settings")
    def test_none_values_for_required_settings(self, mock_settings: MagicMock) -> None:
        """
        Test that None values for required settings return errors.

        This test mocks a `None` value for the `CUSTOM_RESPONSE_DEBUG` setting, 
        which is required to be a boolean. It ensures that an error is returned 
        when required settings are assigned a `None` value.
        
        :param mock_settings: Mock of Django settings.
        """
        # Mock None values for required boolean settings
        mock_settings.CUSTOM_RESPONSE_DEBUG = None  # Should be bool
        mock_settings.CUSTOM_RESPONSE_SUCCESS_HANDLER = "myapp.handlers.CustomSuccessHandler"
        mock_settings.CUSTOM_RESPONSE_ERROR_HANDLER = "myapp.handlers.CustomErrorHandler"

        # Run check and assert error for None boolean
        errors = check_response_shaper_settings(None)
        assert len(errors) == 1
        assert errors[0].id == "response_shaper.E001.CUSTOM_RESPONSE_DEBUG"
        assert "should be a boolean value" in errors[0].msg
