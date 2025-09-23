"""Example usage of the StageWidget class.

In this example all the devices of type 'Stage' and 'XYStage' that are loaded
in micromanager are displayed with a 'StageWidget'.
"""

from math import cos, sin
from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus, DeviceType
from pymmcore_widgets.control._stage_widget import MoveStageButton
from qtpy.QtCore import QPointF, Qt
from qtpy.QtGui import QBrush, QColor, QFont, QPainter, QPen
from qtpy.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from superqt.iconify import QIconifyIcon

if TYPE_CHECKING:
    from pymmcore_plus.core import StageDevice


class _RotationCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setMinimumHeight(200)
        self.setMinimumWidth(200)
        self.angle = 0.0
        self.step = 1.0
        self.text_color = self.palette().color(self.foregroundRole())

    def setAngle(self, angle):
        self.angle = angle
        self.viewport().update()

    def setStep(self, step):
        self.step = step
        self.viewport().update()

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w/2, h/2
        radius = min(w, h) * 0.4

        # Transparent circle with text-colored edge
        painter.setBrush(QBrush(QColor(0,0,0,0)))
        pen = QPen(self.text_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Dashed line for 0 degrees
        zero_pen = QPen(self.text_color)
        zero_pen.setStyle(Qt.DashLine)
        zero_pen.setWidth(2)
        painter.setPen(zero_pen)
        painter.drawLine(QPointF(cx, cy), QPointF(cx, cy+radius))

        # Text "0 degrees"
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(self.text_color)
        painter.drawText(QPointF(cx, cy+radius+15), "0°")

        # Solid line for current angle
        angle_rad = self.angle * 3.14159265 / 180.0
        x2 = cx + radius * sin(angle_rad)
        y2 = cy + radius * cos(angle_rad)
        solid_pen = QPen(self.text_color)
        solid_pen.setWidth(3)
        painter.setPen(solid_pen)
        painter.drawLine(QPointF(cx, cy), QPointF(x2, y2))

        # Dashed green lines for preview angles
        preview_pen = QPen(QColor("green"))
        preview_pen.setStyle(Qt.DashLine)
        preview_pen.setWidth(2)
        for offset in [-self.step, self.step]:
            preview_angle = self.angle + offset
            preview_rad = preview_angle * 3.14159265 / 180.0
            px2 = cx + radius * sin(preview_rad)
            py2 = cy + radius * cos(preview_rad)
            painter.setPen(preview_pen)
            painter.drawLine(QPointF(cx, cy), QPointF(px2, py2))

class RotatorWidget(QWidget):
    """Widget to control a rotational stage device."""

    def __init__(
        self,
        *,
        parent: QWidget = None,
        mmcore: CMMCorePlus = None,
    ):
        super().__init__(parent)
        self._device: StageDevice | None = None
        self._mmc = mmcore or CMMCorePlus.instance()

        # Layouts
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # In your RotationalStageWidget.__init__:
        self._canvas = _RotationCanvas(self)
        main_layout.addWidget(self._canvas)

        # Position display and control
        self._angle_box = QDoubleSpinBox()
        self._angle_box.setSuffix(" °")
        self._angle_box.setDecimals(2)
        self._angle_box.setMinimum(-360)
        self._angle_box.setMaximum(360)
        self._angle_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._angle_box.editingFinished.connect(self._move_absolute)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Absolute:"))
        pos_layout.addWidget(self._angle_box)

        # Move buttons
        move_layout = QHBoxLayout()

        self._step_label = QLabel("Relative: ")
        move_layout.addWidget(self._step_label)

        self._btn_left = MoveStageButton("mdi:chevron-left", 0, -1, self)
        self._btn_left.setToolTip("Rotate clockwise by step")
        self._btn_left.clicked.connect(self._rotate_cw_by_step)
        move_layout.addWidget(self._btn_left)

        self._step_size = QDoubleSpinBox()
        self._step_size.setSuffix("°")
        self._step_size.setDecimals(2)
        self._step_size.setMinimum(0.01)
        self._step_size.setMaximum(90)
        self._step_size.setValue(1.0)
        self._step_size.valueChanged.connect(self._relative_step_changed)
        move_layout.addWidget(self._step_size)

        self._btn_right = MoveStageButton("mdi:chevron-right", 0, 1, self)
        self._btn_right.setToolTip("Rotate counter-clockwise by step")
        self._btn_right.clicked.connect(self._rotate_ccw_by_step)
        move_layout.addWidget(self._btn_right)

        # Halt button
        self._halt_btn = QPushButton()
        self._halt_btn.setIcon(QIconifyIcon("bi:sign-stop-fill", color="red"))
        self._halt_btn.setText("STOP!")
        self._halt_btn.setToolTip("Halt rotation")
        self._halt_btn.clicked.connect(self._halt)

        # Poll checkbox
        self._poll_cb = QCheckBox("Poll")
        self._poll_cb.setChecked(False)
        self._poll_cb.toggled.connect(self._toggle_poll_timer)
        self._poll_timer_id = None

        # Assemble UI
        main_layout.addLayout(move_layout)
        main_layout.addLayout(pos_layout)
        main_layout.addWidget(self._halt_btn)
        main_layout.addWidget(self._poll_cb)

        self._update_position_from_core()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_conf_loaded)
        self._on_conf_loaded()

    def _on_conf_loaded(self) -> None:
        for dev in self._mmc.getLoadedDevicesOfType(DeviceType.Stage):
            if "KBD101" in dev:
                obj = self._mmc.getDeviceObject(dev)
                if obj.getProperty("StageType") == "Rotational":
                    self._device = obj
                    # FIXME: Hardcoded for KBD101
                    self._dev_units_per_rotation = 4e6 * 360
                    self.setEnabled(True)
                    self._update_position_from_core()
                    return
        # No device found - disable controls
        self._device = None
        self.setEnabled(False)

    def _relative_step_changed(self):
        self._canvas.setStep(self._step_size.value())

    def _rotate_ccw_by_step(self) -> None:
        self._move_relative(self._step_size.value())

    def _rotate_cw_by_step(self) -> None:
        self._move_relative(-self._step_size.value())
    
    def _halt(self) -> None:
        self._mmc.stop(self._device)

    def _move_relative(self, delta: float):
        if self._device is None:
            return
        dev_delta = delta / 360 * self._dev_units_per_rotation
        self._device.getPositionAccumulator().add_relative(dev_delta)

    def wheelEvent(self, a0):
        """Handle mouse wheel events to rotate the stage."""
        delta = a0.angleDelta().y() / 120  # Each notch is 120 units
        self._move_relative(delta)


    def _move_absolute(self):
        angle = self._angle_box.value()
        dev_units = angle / 360 * self._dev_units_per_rotation
        self._device.getPositionAccumulator().set_absolute(dev_units)
        self._toggle_poll_timer(True)

    def _update_position_from_core(self):
        if self._device:
            self._mmc.waitForDevice(self._device.name())
            angle = self._device.getPosition() / self._dev_units_per_rotation * 360
            print(f"Updating angle from core: {angle}")
            self._angle_box.setValue(angle)
            self._canvas.setAngle(angle)

    def _toggle_poll_timer(self, on: bool):
        if on and self._poll_timer_id is None:
            self._poll_timer_id = self.startTimer(500)
        elif not on and self._poll_timer_id is not None:
            self.killTimer(self._poll_timer_id)
            self._poll_timer_id = None

    def timerEvent(self, event):
        """Handle timer events for polling the device position."""
        if event and event.timerId() == self._poll_timer_id:
            self._update_position_from_core()
        super().timerEvent(event)
