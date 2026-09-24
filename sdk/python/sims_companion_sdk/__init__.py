"""Minimal provider-neutral backend adapter SDK (Python 3.9+)."""

from .adapter import BackendAdapter, BackendCapabilities, CrossSurfaceProvider, TurnRequest, TurnResponse

__all__ = ["BackendAdapter", "BackendCapabilities", "CrossSurfaceProvider", "TurnRequest", "TurnResponse"]
__version__ = "0.1.0"
