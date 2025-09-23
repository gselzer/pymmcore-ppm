from pymmcore_gui import create_mmgui
from pymmcore_gui.actions import WidgetActionInfo
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QWidget

from pymmcore_ppm.widgets import (
    RotatorWidget,
)


def augment_pymmcore_gui() -> None:
    """Installs package functionality into pymmcore-gui."""
    # By Creating these WidgetActionInfos, they are installed in pymmcore-gui.
    _get_action_infos()


def run() -> None:
    """Run the pymmcore-gui with OpenScan widgets."""
    augment_pymmcore_gui()
    create_mmgui()


def _get_action_infos() -> list[WidgetActionInfo]:
    return [
        WidgetActionInfo(
            key="",
            text="ThorLabs KBD101",
            icon="mdi:axis-z-rotate-counterclockwise",
            create_widget=_create_rot,
        ),
    ]


# -- Widget Creators --


def _create_rot(parent: QWidget) -> QWidget:
    mmcore = CMMCorePlus.instance()
    return RotatorWidget(parent=parent, mmcore=mmcore)
