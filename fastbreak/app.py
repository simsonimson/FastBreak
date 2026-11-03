import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from . import keys

ASSETS = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "assets"

STYLE = """
#root { background: #f3f3f3; }
QLabel { color: #1c1c1c; }
#title { font-size: 12pt; font-weight: 600; }
#caption { color: #6b6b6b; font-size: 8pt; }
#key {
    background: #ffffff; border: 1px solid #c8c8c8; border-radius: 2px;
    padding: 4px 6px; font-weight: 600;
}
#key[capturing="true"] { color: #8a8a8a; font-weight: 400; }
#sep { background: #dddddd; border: none; }
QPushButton {
    background: #fbfbfb; color: #1c1c1c; border: 1px solid #bcbcbc;
    border-radius: 2px; padding: 4px 8px;
}
QPushButton:hover { background: #ffffff; border-color: #8c8c8c; }
QPushButton:pressed { background: #e7e7e7; }
QPushButton:disabled { color: #a8a8a8; border-color: #d8d8d8; background: #f6f6f6; }
#start { font-weight: 600; padding: 7px; letter-spacing: 2px; }
#start[running="true"] { background: #1c1c1c; color: #ffffff; border-color: #1c1c1c; }
#start[running="true"]:hover { background: #333333; }
#status { color: #555555; font-size: 8pt; letter-spacing: 1px; }
#dot { border-radius: 4px; background: #a6a6a6; }
#dot[state="active"] { background: #2e9d4f; }
#dot[state="held"] { background: #d42626; }
"""


def _restyle(widget, prop, value):
    widget.setProperty(prop, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class MainWindow(QWidget):
    def __init__(self, engine):
        super().__init__(None, Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self.engine = engine
        self.settings = QSettings("FastBreak", "FastBreak")
        self.running = False
        self.capturing = False
        hotkey = self.settings.value("hotkey", keys.DEFAULT_HOTKEY, type=int)
        self.hotkey = hotkey if keys.valid(hotkey) else keys.DEFAULT_HOTKEY

        self.setObjectName("root")
        self.setWindowTitle("FastBreak")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        title = QLabel("FastBreak", objectName="title")
        logo = QLabel()
        dpr = self.devicePixelRatioF()
        pm = QPixmap(str(ASSETS / "logo.png")).scaled(
            int(34 * dpr), int(34 * dpr), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        logo.setPixmap(pm)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(logo)

        sep = QFrame(objectName="sep")
        sep.setFixedHeight(1)

        self.key_label = QLabel(objectName="key")
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.change_btn = QPushButton("Change")
        self.change_btn.setFixedWidth(62)
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        key_row.addWidget(self.key_label, 1)
        key_row.addWidget(self.change_btn)

        self.start_btn = QPushButton("START", objectName="start")
        for b in (self.change_btn, self.start_btn):
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # hotkey must never click a button
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.dot = QLabel(objectName="dot")
        self.dot.setFixedSize(8, 8)
        self.status = QLabel("READY", objectName="status")
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        status_row.addStretch()
        status_row.addWidget(self.dot)
        status_row.addWidget(self.status)
        status_row.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 9)
        root.setSpacing(8)
        root.addLayout(header)
        root.addWidget(sep)
        hotkey_box = QVBoxLayout()
        hotkey_box.setSpacing(3)
        hotkey_box.addWidget(QLabel("Hotkey", objectName="caption"))
        hotkey_box.addLayout(key_row)
        root.addLayout(hotkey_box)
        root.addWidget(self.start_btn)
        root.addLayout(status_row)

        self.change_btn.clicked.connect(self.toggle_capture)
        self.start_btn.clicked.connect(self.toggle_running)
        engine.captured.connect(self.on_captured)
        engine.held_changed.connect(self.on_held)

        self.refresh()
        self.setFixedSize(220, self.sizeHint().height())

    def refresh(self):
        self.key_label.setText("Press a key…" if self.capturing else keys.name(self.hotkey))
        _restyle(self.key_label, "capturing", self.capturing)
        self.change_btn.setText("Cancel" if self.capturing else "Change")
        self.change_btn.setEnabled(not self.running)
        self.start_btn.setText("STOP" if self.running else "START")
        self.start_btn.setEnabled(not self.capturing)
        _restyle(self.start_btn, "running", self.running)
        self.status.setText("ACTIVE" if self.running else "READY")
        _restyle(self.dot, "state", "active" if self.running else "")

    def toggle_capture(self):
        if self.capturing:
            self.capturing = False
            self.engine.end_capture()
        else:
            self.capturing = self.engine.begin_capture()
        self.refresh()

    def on_captured(self, vk):
        self.capturing = False
        self.engine.end_capture()
        if vk:
            self.hotkey = vk
            self.settings.setValue("hotkey", vk)
        self.refresh()

    def toggle_running(self):
        if self.running:
            self.engine.stop()
            self.running = False
        else:
            self.running = self.engine.start(self.hotkey)
        self.refresh()

    def on_held(self, held):
        if self.running:
            _restyle(self.dot, "state", "held" if held else "active")

    def closeEvent(self, event):
        self.engine.shutdown()
        super().closeEvent(event)


def _light_palette() -> QPalette:
    p = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, "#f3f3f3"), (QPalette.ColorRole.WindowText, "#1c1c1c"),
        (QPalette.ColorRole.Base, "#ffffff"), (QPalette.ColorRole.Text, "#1c1c1c"),
        (QPalette.ColorRole.Button, "#fbfbfb"), (QPalette.ColorRole.ButtonText, "#1c1c1c"),
        (QPalette.ColorRole.Highlight, "#1c1c1c"), (QPalette.ColorRole.HighlightedText, "#ffffff"),
    ):
        p.setColor(role, QColor(color))
    return p


def main():
    if sys.platform != "win32":
        sys.exit("FastBreak runs on Windows only.")

    from . import win32
    from .engine import Engine

    win32.set_app_id("FastBreak.FastBreak")
    app = QApplication(sys.argv)
    app.setApplicationName("FastBreak")
    app.setStyle("Fusion")
    app.setPalette(_light_palette())
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(STYLE)

    icon = QIcon()
    for name in ("icon-16.png", "icon-32.png", "icon-256.png"):
        icon.addFile(str(ASSETS / name))
    app.setWindowIcon(icon)

    engine = Engine()
    _hook_excepthook(engine)
    app.aboutToQuit.connect(engine.shutdown)

    window = MainWindow(engine)
    window.show()
    code = app.exec()
    engine.shutdown()
    sys.exit(code)


def _hook_excepthook(engine):
    default = sys.excepthook

    def handler(*exc):
        try:
            engine.release_keys()
        finally:
            default(*exc)

    sys.excepthook = handler
