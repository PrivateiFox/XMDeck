"""XMDeck root entry point for Decky Loader runtime."""

import os
import sys

# Ensure plugin directory is in sys.path so 'backend' is importable in Decky's sandboxed environment
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from backend.main import Plugin  # noqa: E402

__all__ = ["Plugin"]

