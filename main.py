"""XMDeck root entry point for Decky Loader runtime."""

import os
import sys

# Ensure plugin directory is in sys.path so 'backend' is importable in Decky's sandboxed environment
plugin_dir = os.path.dirname(os.path.abspath(__file__))
for path in [plugin_dir, "/home/deck/homebrew/plugins/XMDeck"]:
    if path and os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

from backend.main import Plugin  # noqa: E402

__all__ = ["Plugin"]

