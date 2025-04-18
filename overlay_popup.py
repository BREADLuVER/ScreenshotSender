# overlay_popup.py
from PyQt5 import QtWidgets, QtGui, QtCore
import ctypes, sys
from ctypes import windll
from ctypes import wintypes
import threading
from PyQt5.QtCore import pyqtSlot
import base64, os

class GhostCursor(QtWidgets.QWidget):
    def __init__(self, global_pos: QtCore.QPoint):
        super().__init__(
            None,
            QtCore.Qt.Tool
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.WindowTransparentForInput
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        cursor_pixmap = QtGui.QCursor().pixmap()
        if cursor_pixmap.isNull():
            cursor_pixmap = QtGui.QPixmap(16, 16)
            cursor_pixmap.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter(cursor_pixmap)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtCore.Qt.black)
            painter.drawLine(1, 1, 10, 5)
            painter.drawLine(1, 1, 5, 10)
            painter.end()

        self.setFixedSize(cursor_pixmap.size())
        self.move(global_pos)

        label = QtWidgets.QLabel(self)
        label.setPixmap(cursor_pixmap)
        label.move(0, 0)

        self.show()

WDA_EXCLUDEFROMCAPTURE = 0x11          # Windows 10 2004+
user32 = windll.user32

def enable_capture_protection(hwnd: int) -> None:
    """
    Must be called *after* the widget is visible, otherwise Windows
    rejects it with ERROR_INVALID_PARAMETER (87) and GetWindowDisplayAffinity
    stays 0x0.
    """
    if not user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
        err = windll.kernel32.GetLastError()
        if err == 87:                   # old Windows: fall back
            user32.SetWindowDisplayAffinity(hwnd, 0x1)  
class OverlayWindow(QtWidgets.QWidget):
    _ghost: "GhostCursor | None" = None

    def __init__(self, parent_manager):
        super().__init__(None, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlag(QtCore.Qt.WindowTransparentForInput)
        self.parent_manager = parent_manager
        self.move_step = 20
        self.visible = True
        self._ghost = None

        self.init_ui()                   # <— window must exist first
        self.show()  # must be after init_ui()
        hwnd = int(self.winId())
        enable_capture_protection(hwnd)

    def init_ui(self):
        self.setFixedSize(1000, 1000)
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFocus()

        self.setGeometry(1200, 300, 1000, 1000)

        self.background = QtWidgets.QFrame(self)
        self.background.setGeometry(0, 0, 1000, 1000)  # Match the full size
        self.background.setStyleSheet("background-color: rgba(0, 0, 0, 50); border-radius: 10px;")

        self.scroll_area = QtWidgets.QScrollArea(self.background)
        self.scroll_area.setGeometry(10, 10, 980, 900)
        self.scroll_area.setStyleSheet("border: none;")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.label = QtWidgets.QLabel()
        self.label.setStyleSheet("""
            background-color: transparent;
            color: white;
            font-size: 24px;
            padding: 5px;
        """)
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QtCore.Qt.black)
        shadow.setOffset(1, 1)
        self.label.setGraphicsEffect(shadow)
        self.label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.scroll_area.setWidget(self.label)

        self.input = QtWidgets.QLineEdit(self.background)
        self.input.setGeometry(10, 920, 800, 70)
        self.input.setStyleSheet("""
            background-color: white;
            border-radius: 5px;
            padding: 10px;
            font-size: 16px;
        """)

        self.send_button = QtWidgets.QPushButton("Send", self.background)
        self.send_button.setGeometry(820, 920, 160, 70)
        self.send_button.setStyleSheet("""
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            font-size: 16px;
        """)
        self.send_button.clicked.connect(self.handle_send)

        self.input.returnPressed.connect(self.handle_send)
        

    @QtCore.pyqtSlot(str)
    def update_text(self, message):
        previous = self.label.text()
        self.label.setText(previous + "\n\n" + message)
        QtCore.QTimer.singleShot(0, lambda: self.scroll_area.verticalScrollBar().setValue(
        self.scroll_area.verticalScrollBar().maximum()))
        self.setVisible(True)
        self.raise_()
        self.activateWindow()
        self.setFocus()

    @QtCore.pyqtSlot()
    def handle_send(self):
        user_input = self.input.text().strip()

        if user_input == "":
            return

        self.input.clear()
        self.parent_manager.handle_user_prompt(user_input)

    @QtCore.pyqtSlot(int)
    def hide_and_restore(self, delay_ms: int) -> None:
        """Hide now, re‑show after `delay_ms` (runs in GUI thread)."""
        self.hide()
        QtCore.QTimer.singleShot(delay_ms, self.show)

    def toggle_visibility(self):
        self.visible = not self.visible
        self.setVisible(self.visible)
        if self.visible:
            self.raise_()
            self.activateWindow()
            self.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        x, y = self.x(), self.y()

        if key == QtCore.Qt.Key_Escape:
            QtWidgets.QApplication.quit()
        elif key == QtCore.Qt.Key_Up:
            self.move(x, y - self.move_step)
        elif key == QtCore.Qt.Key_Down:
            self.move(x, y + self.move_step)
        elif key == QtCore.Qt.Key_Left:
            self.move(x - self.move_step, y)
        elif key == QtCore.Qt.Key_Right:
            self.move(x + self.move_step, y)

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusInEvent(event)

        if self._ghost is None:
            gp = QtGui.QCursor.pos()           # global position
            self._ghost = GhostCursor(gp)
        else:
            # We already have one; just raise it in case it was buried
            self._ghost.raise_()
            self._ghost.show()      

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusOutEvent(event)

        # Close only when the overlay really loses focus, otherwise
        # Windows would delete the ghost as soon as you start typing.
        if self._ghost is not None:
            # We just hide it, do not destroy – so it can be re‑used
            self._ghost.hide()

class OverlayManager:
    def __init__(self, conversation_history, openai, log_response, screenshot_paths):
        self.conversation_history = conversation_history
        self.openai = openai
        self.log_response = log_response
        self.app = None
        self.window = None
        self.ready_event = threading.Event()
        self.screenshot_paths = screenshot_paths

    def start(self):
        threading.Thread(target=self._run_qt, daemon=True).start()
        self.ready_event.wait()  # Wait until the window is ready

    def _run_qt(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = OverlayWindow(self)
        self.window.show()
        self.ready_event.set()
        self.app.exec_()

    def hide_temporarily(self, delay_ms: int = 500) -> None:
        if not self.window:
            return

        QtCore.QMetaObject.invokeMethod(
            self.window,
            "hide_and_restore",           # slot name as *string*
            QtCore.Qt.QueuedConnection,   # cross‑thread delivery
            QtCore.Q_ARG(int, delay_ms)   # pass the delay
        )

    def show_message(self, text):
        if self.window:
            QtCore.QMetaObject.invokeMethod(
                self.window,
                "update_text",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, text)
            )

    def toggle(self):
        QtCore.QTimer.singleShot(0, self.window.toggle_visibility)

    def handle_user_prompt(self, prompt: str):
        threading.Thread(target=self._send_text_to_openai, args=(prompt,), daemon=True).start()

    def _send_text_to_openai(self, prompt):
        content = [{"type": "text", "text": prompt}]

        # Optionally cap the number of images (here: last 3)
        MAX_IMAGES = 3
        for image_path in self.screenshot_paths[-MAX_IMAGES:]:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf‑8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64}",
                        "detail": "low",
                    },
                }
            )

        # ➋ Append message to history
        self.conversation_history.append(
            {"role": "user", "content": content}
        )

        # ➌ Send
        try:
            resp = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=self.conversation_history,
                max_tokens=150,
                temperature=0.5,
            )
            reply = resp.choices[0].message.content

            self.conversation_history.append(
                {"role": "assistant", "content": reply}
            )
            full = f"🧑 {prompt}\n\n🤖 {reply}"
            self.show_message(full)
            self.log_response(
                "[typed prompt + screenshots]",
                prompt,
                reply,
            )
        except Exception as e:
            self.show_message(f"[Error] {e}")

        # ➍ Clear screenshots so they won't be reused inadvertently
        self.screenshot_paths.clear()
