"""PyInstaller runtime hook: point Qt at bundled platform plugins."""

import os
import sys

if getattr(sys, "frozen", False):
    base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    plugins = os.path.join(base, "PyQt5", "Qt5", "plugins")
    platforms = os.path.join(plugins, "platforms")
    if os.path.isdir(platforms):
        os.environ.setdefault("QT_PLUGIN_PATH", plugins)
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", platforms)
