"""XMDeck root entry point for Decky Loader runtime."""

from __future__ import annotations

import os
import sys

# Ensure plugin directory is in sys.path before importing internal packages
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR and _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

from backend.main import Plugin  # noqa: E402

__all__ = ["Plugin"]
