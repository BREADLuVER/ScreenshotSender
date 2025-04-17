# overlay_popup.py
from PyQt5 import QtWidgets, QtCore
import sys
import threading
from PyQt5.QtCore import pyqtSlot

class OverlayWindow(QtWidgets.QWidget):
    def __init__(self, parent_manager):
        super().__init__()
        self.parent_manager = parent_manager
        self.move_step = 20
        self.visible = True
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(1000, 1000)
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
            font-size: 16px;
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
    def __init__(self, conversation_history, openai, log_response):
        self.conversation_history = conversation_history
        self.openai = openai
        self.log_response = log_response
        self.app = None
        self.window = None
        self.ready_event = threading.Event()

    def start(self):
        threading.Thread(target=self._run_qt, daemon=True).start()
        self.ready_event.wait()  # Wait until the window is ready

    def _run_qt(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = OverlayWindow(self)
        self.window.show()
        self.ready_event.set()
        self.app.exec_()

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
        self.conversation_history.append({
            "role": "user",
            "content": prompt
        })

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=self.conversation_history,
                max_tokens=150,
                temperature=0.5
            )

            reply = response.choices[0].message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": reply
            })

            full_text = f"🧑 {prompt}\n\n🤖 {reply}"
            self.show_message(full_text)

            # Optional log
            self.log_response("[typed prompt]", prompt, reply)

        except Exception as e:
            self.show_message(f"[Error] {e}")



