"""Pytest configuration and fixtures for INELNET Blinds tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the repo root is on path so custom_components.inelnet can be loaded
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Only load the HA plugin when installed, so pytest runs even without it
try:
    import pytest_homeassistant_custom_component  # noqa: F401
    pytest_plugins = ("pytest_homeassistant_custom_component",)
    HAS_HA_PLUGIN = True
except ImportError:
    pytest_plugins = ()
    HAS_HA_PLUGIN = False


if HAS_HA_PLUGIN:

    @pytest.fixture
    def auto_enable_custom_integrations(enable_custom_integrations):
        """Enable custom integrations. Use @pytest.mark.usefixtures for tests that need it."""
        yield
else:

    @pytest.fixture
    def enable_custom_integrations():
        """Stub: skip tests that need HA when the plugin is not installed."""
        pytest.skip("Install pytest-homeassistant-custom-component to run integration tests")
