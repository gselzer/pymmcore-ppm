from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus

from pymmcore_ppm.widgets import RotatorWidget

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_rotator_widget_disabled(qtbot: QtBot) -> None:
    """Tests how RotatorWidget behaves when the device is unavailable."""
    mmcore = CMMCorePlus.instance()
    wdg = RotatorWidget(mmcore=mmcore)
    qtbot.addWidget(wdg)

    assert not wdg.isEnabled()
