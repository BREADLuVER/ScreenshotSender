# overlay_popup.py
from PyQt5 import QtWidgets, QtCore
import sys
import threading

class OverlayWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.move_step = 20
        self.visible = True
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFocus()

        self.setGeometry(100, 100, 600, 150)

        self.background = QtWidgets.QFrame(self)
        self.background.setStyleSheet("background-color: rgba(0, 0, 0, 180); border-radius: 10px;")
        self.background.setGeometry(0, 0, 600, 150)

        self.label = QtWidgets.QLabel("GPT reply will appear here.", self)
        self.label.setGeometry(10, 10, 580, 130)
        self.label.setStyleSheet("color: white; font-size: 16px;")
        self.label.setAlignment(QtCore.Qt.AlignCenter)

    def update_text(self, message):
        self.label.setText(message)
        self.setVisible(True)
        self.raise_()
        self.activateWindow()
        self.setFocus()

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


class OverlayManager:
    def __init__(self):
        self.app = None
        self.window = None
        self.ready_event = threading.Event()

    def start(self):
        threading.Thread(target=self._run_qt, daemon=True).start()
        self.ready_event.wait()  # Wait until the window is ready

    def _run_qt(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = OverlayWindow()
        self.window.show()
        self.ready_event.set()
        self.app.exec_()

    def show_message(self, text):
        if self.window:
            def update():
                self.window.update_text(text)
            QtCore.QTimer.singleShot(0, update)
            
    def toggle(self):
        QtCore.QTimer.singleShot(0, self.window.toggle_visibility)
