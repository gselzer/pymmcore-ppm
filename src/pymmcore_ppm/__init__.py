"""A set of widgets for PPM, built atop pymmcore-plus, for pymmcore-gui."""

from importlib.metadata import PackageNotFoundError, version

from pymmcore_ppm._util import augment_pymmcore_gui, run

try:
    __version__ = version("pymmcore-ppm")
except PackageNotFoundError:
    __version__ = "uninstalled"

__all__: list[str] = ["__version__", "augment_pymmcore_gui", "run"]
