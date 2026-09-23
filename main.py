"""XMDeck root entry point for Decky Loader runtime."""

from __future__ import annotations

import os
import sys

# Ensure plugin directory is in sys.path before importing internal packages
# in Decky's sandboxed environment
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
for _path in (_PLUGIN_DIR, "/home/deck/homebrew/plugins/XMDeck"):
    if _path and os.path.exists(_path) and _path not in sys.path:
        sys.path.insert(0, _path)

from backend.main import Plugin  # noqa: E402

__all__ = ["Plugin"]
