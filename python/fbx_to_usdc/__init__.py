"""FBX to USDC Converter - build a UsdSkel pipeline from an FBX and write .usdc."""

__version__ = "1.0.12"

from . import core     # noqa: F401
from . import ui       # noqa: F401
from . import updater  # noqa: F401


def show():
    """Convenience entry so the shelf can call fbx_to_usdc.show()."""
    return ui.show()
