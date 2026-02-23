"""INELNET Blinds REST API client – one object per channel (host + channel)."""

from .client import Action, InelnetChannel

__all__ = ["Action", "InelnetChannel"]
__version__ = "1.0.1"
