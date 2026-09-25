"""The Sims 4 loader bootstrap for Sims Companion Bridge."""
from __future__ import absolute_import

try:
    import services  # noqa: F401
except ImportError:
    services = None

if services is not None:
    import sims_companion_bridge.runtime  # noqa: F401
