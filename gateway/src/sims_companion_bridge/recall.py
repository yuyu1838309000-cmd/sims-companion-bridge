"""Interface-only cross-surface recall contract; disabled in v0.1."""

from abc import ABC, abstractmethod


class CrossSurfaceProvider(ABC):
    enabled = False

    @abstractmethod
    def recall(self, query, context):
        """Return external-memory candidates. Implementations must remain opt-in."""
        raise NotImplementedError


class DisabledCrossSurfaceProvider(CrossSurfaceProvider):
    def recall(self, query, context):
        return []
