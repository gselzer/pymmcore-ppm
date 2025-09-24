"""Example usage of the StageWidget class.

In this example all the devices of type 'Stage' and 'XYStage' that are loaded
in micromanager are displayed with a 'StageWidget'.
"""
from __future__ import annotations

from math import cos, pi, sin
from typing import TYPE_CHECKING

import cmap
from pyconify import svg_path
from pymmcore_plus import CMMCorePlus, DeviceType
from pymmcore_widgets.control._q_stage_controller import QStageMoveAccumulator
from qtpy.QtCore import QPointF, Qt
from qtpy.QtGui import QBrush, QColor, QFont, QPainter, QPen
from qtpy.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from superqt.iconify import QIconifyIcon

if TYPE_CHECKING:
    from pymmcore_plus.core import StageDevice


# Forked from: https://github.com/pymmcore-plus/pymmcore-widgets/blob/2b33e43aa4d49b0861b52b383ab1cd0123ecc61a/src/pymmcore_widgets/control/_stage_widget.py#L51
# Forked in order to provide configurable color
class _MoveStageButton(QPushButton):
    def __init__(
        self,
        glyph: str,
        xmag: int,
        ymag: int,
        parent: QWidget | None = None,
        color: cmap.Color | None = None
    ):
        super().__init__(parent=parent)
        self.xmag = xmag
        self.ymag = ymag
        self._color: cmap.Color = color or cmap.Color("lime")
        self._glyph = glyph
        self.color = self._color
        self.setAutoRepeat(True)
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def color(self) -> cmap.Color:
        return self._color

    @color.setter
    def color(self, color: cmap.Color) -> None:
        self._color = color

        r, g, b = self._color.rgba8[:3]
        # Normally the button will be half the intensity of the color...
        normal_path = svg_path(
            self._glyph,
            color=f"rgb({r // 2}, {g // 2}, {b})"
        ).as_posix()
        # ...but when hovering, it will be full intensity...
        hover_path = svg_path(
            self._glyph,
            color=f"rgb({r}, {g}, {b})"
        ).as_posix()
        # ...and when pressed, it will be 3/4 intensity.
        press_path = svg_path(
            self._glyph,
            color=f"rgb({3 * r // 4}, {3 * g // 4}, {3 * b // 4})"
        ).as_posix()

        self.setStyleSheet(
            f"""
            _MoveStageButton {{
                border: none;
                width: 38px;
                image: url({normal_path});
                font-size: 38px;
            }}
            _MoveStageButton:hover:!pressed {{
                image: url({hover_path});
            }}
            _MoveStageButton:pressed {{
                image: url({press_path});
            }}
            """
        )
        return self._color

# End fork

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
        self.reference_angles = [0, 45, -45, 90, -90, 60.3]

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

        # Reference Text for major angles
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(self.text_color)
        for angle in self.reference_angles:
            text = f"{angle}°"
            rx = sin(angle * pi / 180.0)
            ry = cos(angle * pi / 180.0)
            rect = painter.fontMetrics().boundingRect(text)
            dx = rx * (radius + 5) + (rect.width() // 2 * (rx-1))
            dy = ry * (radius + 5) + (rect.height() // 4 * (ry+1))
            painter.drawText(QPointF(cx + dx, cy + dy), text)

        # Solid line for current angle
        angle_rad = self.angle * 3.14159265 / 180.0
        x2 = cx + radius * sin(angle_rad)
        y2 = cy + radius * cos(angle_rad)
        solid_pen = QPen(self.text_color)
        solid_pen.setWidth(3)
        painter.setPen(solid_pen)
        painter.drawLine(QPointF(cx, cy), QPointF(x2, y2))

        # Dashed lines for preview angles
        preview_pen = QPen(QColor("green"))
        preview_pen.setStyle(Qt.DashLine)
        preview_pen.setWidth(2)
        for offset, color in [(self.step, QColor("green")), (-self.step, QColor("deepPink"))]:
            preview_angle = self.angle + offset
            preview_rad = preview_angle * pi / 180.0
            px2 = cx + radius * sin(preview_rad)
            py2 = cy + radius * cos(preview_rad)
            preview_pen.setColor(color)
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
        self._dev_controller: QStageMoveAccumulator | None = None
        self._mmc = mmcore or CMMCorePlus.instance()

        # Grid Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Canvas
        self._canvas = _RotationCanvas(self)
        main_layout.addWidget(self._canvas)

        # Absolute and relative Rotation controls go in a Grid layout
        self._move_wdg = QWidget(self)
        move_layout = QGridLayout(self._move_wdg)
        main_layout.addWidget(self._move_wdg)

        self._abs_label = QLabel("Absolute:", self._move_wdg)

        self._abs_box = QDoubleSpinBox()
        self._abs_box.setSuffix(" °")
        self._abs_box.setDecimals(2)
        self._abs_box.setMinimum(-360)
        self._abs_box.setMaximum(360)
        self._abs_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._abs_box.editingFinished.connect(self._move_absolute)

        move_layout.addWidget(self._abs_label, 1, 0, 1, 0)
        move_layout.addWidget(self._abs_box, 1, 1, 1, 3)  # spans 3 columns

        # Relative Move buttons - row 1
        self._step_label = QLabel("Relative:")
        move_layout.addWidget(self._step_label, 0, 0)

        self._btn_left = _MoveStageButton("mdi:chevron-left", 0, -1, self)
        self._btn_left.color = cmap.Color("deepPink")
        self._btn_left.setToolTip("Rotate clockwise by step")
        self._btn_left.clicked.connect(self._rotate_cw_by_step)
        move_layout.addWidget(self._btn_left, 0, 1)

        self._step_size = QDoubleSpinBox()
        self._step_size.setSuffix("°")
        self._step_size.setDecimals(2)
        self._step_size.setMinimum(0.01)
        self._step_size.setMaximum(90)
        self._step_size.setValue(1.0)
        self._step_size.valueChanged.connect(self._relative_step_changed)
        move_layout.addWidget(self._step_size, 0, 2)

        self._btn_right = _MoveStageButton("mdi:chevron-right", 0, 1, self)
        self._btn_right.setToolTip("Rotate counter-clockwise by step")
        self._btn_right.clicked.connect(self._rotate_ccw_by_step)
        move_layout.addWidget(self._btn_right, 0, 3)

        self._btns = QWidget(self)
        self._btn_layout = QHBoxLayout(self._btns)
        main_layout.addWidget(self._btns)

        # Halt button
        self._halt_btn = QPushButton()
        self._halt_btn.setIcon(QIconifyIcon("mdi:stop-alert", color="red"))
        self._halt_btn.setText("STOP!")
        self._halt_btn.setToolTip("Halt rotation")
        self._halt_btn.clicked.connect(self._halt)
        self._btn_layout.addWidget(self._halt_btn)

        # Home button
        self._home_btn = QPushButton()
        self._home_btn.setIcon(QIconifyIcon("mdi:home", color="cyan"))
        self._home_btn.setText("Home")
        self._home_btn.setToolTip("Move to home position")
        self._home_btn.clicked.connect(self._home)
        self._btn_layout.addWidget(self._home_btn)

        # Poll checkbox - row 4, spans half row
        self._poll_cb = QCheckBox("Poll")
        self._poll_cb.setChecked(False)
        self._poll_cb.toggled.connect(self._toggle_poll_timer)
        self._poll_timer_id = None

        self.snap_checkbox = QCheckBox(text="Snap on Click")

        self._invert_y = QCheckBox(text="Invert Relative Rotation")

        chxbox_grid = QGridLayout()
        chxbox_grid.setSpacing(12)
        chxbox_grid.setContentsMargins(0, 0, 0, 0)
        chxbox_grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chxbox_grid.addWidget(self.snap_checkbox, 0, 0)
        chxbox_grid.addWidget(self._poll_cb, 0, 1)
        chxbox_grid.addWidget(self._invert_y, 1, 1)
        main_layout.addLayout(chxbox_grid)

        self._update_position_from_core()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_conf_loaded)
        self._invert_y.checkStateChanged.connect(self._on_invert_toggle)
        self.snap_checkbox.stateChanged.connect(self._on_snap_checkbox_toggled)
        self._on_conf_loaded()

    def _on_snap_checkbox_toggled(self):
        if self._dev_controller:
            self._dev_controller.snap_on_finish = self.snap_checkbox.isChecked()

    def _on_invert_toggle(self):
        inverted = self._invert_y.isChecked()
        green = cmap.Color("lime")
        pink = cmap.Color("deepPink")
        self._btn_left.color = green if inverted else pink
        self._btn_right.color = pink if inverted else green

    def _on_conf_loaded(self) -> None:
        for dev in self._mmc.getLoadedDevicesOfType(DeviceType.Stage):
            if "KBD101" in dev:
                obj = self._mmc.getDeviceObject(dev)
                if obj.getProperty("StageType") == "Rotational":
                    self._device = obj
                    self._dev_controller = QStageMoveAccumulator.for_device(self._device.name())
                    self._dev_controller.snap_on_finish = self.snap_checkbox.isChecked()
                    self._dev_controller.moveFinished.connect(self._update_position_from_core)
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

    def _home(self) -> None:
        if self._device is None:
            return
        self._home_btn.setText("Homing...")
        self._mmc.home(self._device.name())
        self._home_btn.setText("Home")

    def _move_relative(self, delta: float):
        if self._device is None:
            return
        dev_delta = delta / 360 * self._dev_units_per_rotation
        if self._invert_y.isChecked():
            dev_delta = -dev_delta
        self._dev_controller.move_relative(dev_delta)

    def wheelEvent(self, a0):
        """Handle mouse wheel events to rotate the stage."""
        delta = a0.angleDelta().y() / 120  # Each notch is 120 units
        self._move_relative(delta)

    def _move_absolute(self):
        angle = self._abs_box.value()
        dev_units = angle / 360 * self._dev_units_per_rotation
        self._dev_controller.move_absolute(dev_units)

    def _update_position_from_core(self):
        if self._device:
            self._mmc.waitForDevice(self._device.name())
            angle = self._device.getPosition() / self._dev_units_per_rotation * 360
            print(f"Updating angle from core: {angle}")
            # Only update the spinbox if the user isn't currently editing it
            if not self._abs_box.hasFocus():
                self._abs_box.setValue(angle)
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
