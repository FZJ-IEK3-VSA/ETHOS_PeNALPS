"""Pre-create proplot config dirs to avoid pytest-xdist mkdir race."""
import os

_xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
for _sub in ("", "cmaps", "cycles", "colors", "fonts"):
    os.makedirs(os.path.join(_xdg, "proplot", _sub), exist_ok=True)
