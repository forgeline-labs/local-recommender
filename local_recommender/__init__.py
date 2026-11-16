"""Deterministic item-item collaborative recommendations.

The package exports a single public function, :func:`recommend`. It uses only
the Python standard library and performs no I/O, caching or mutation.
"""

from .recommend import recommend

__all__ = ["recommend"]
__version__ = "0.1.0"
