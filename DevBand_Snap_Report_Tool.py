
import sys
import os
import requests

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout
)
from PySide6.QtGui import QMovie
from PySide6.QtCore import Qt

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

TO_EMAIL = "safety@snapchat.com"
FROM_EMAIL = "zcflupkj@telegmail.com"
SUBJECT = "Urgent Report – Account Engaging in Sexual Exploitation and Blackmail"


class SnapReportTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snap Report Tool | DevBand")
        self.setFixedSize(440, 560)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setup_ui()

    def setup_ui(self):
        self.bg = QLabel(self)
        self.bg.setGeometry(0, 0, 440, 560)

        gif_path = os.path.join(os.path.dirname(__file__), "background.gif")
        self.movie = QMovie(gif_path)
        self.movie.setScaledSize(self.size())
        self.bg.setMovie(self.movie)
        self.movie.start()

        card = QWidget(self)
        card.setGeometry(30, 30, 380, 500)
        card.setStyleSheet("""
            QWidget {
                background-color: rgba(15,15,15,170);
                border-radius: 20px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 40, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Snapchat Report")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:22px;font-weight:bold;color:white;")

        brand = QLabel("DevBand")
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet("font-size:12px;letter-spacing:2px;color:#00e5ff;")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.style_input(self.email_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.style_input(self.username_input)

        reason = QLabel("Reason: Sexual Exploitation")
        reason.setAlignment(Qt.AlignCenter)
        reason.setStyleSheet("color:#ff5252;font-weight:bold;")

        self.send_btn = QPushButton("Send Report")
        self.send_btn.clicked.connect(self.send_report)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background:#00e5ff;
                padding:14px;
                border-radius:14px;
                font-weight:bold;
            }
            QPushButton:disabled {
                background:#444;
                color:#999;
            }
        """)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color:#9cff57;")

        layout.addWidget(title)
        layout.addWidget(brand)
        layout.addWidget(self.email_input)
        layout.addWidget(self.username_input)
        layout.addWidget(reason)
        layout.addSpacing(20)
        layout.addWidget(self.send_btn)
        layout.addWidget(self.status)

    def style_input(self, w):
        w.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.08);
                border-radius: 12px;
                padding: 12px;
                color: white;
            }
        """)

    def send_report(self):
        if not SENDGRID_API_KEY:
            self.status.setText("API KEY NOT FOUND")
            return

        username = self.username_input.text().strip()
        if not username:
            return

        message = f"""Dear Snapchat Support Team,

I am writing to urgently report the following account:
Username: @{username}

This account is involved in sexual exploitation and blackmail.

Sincerely,
Ahmed
"""

        payload = {
            "personalizations": [{
                "to": [{"email": TO_EMAIL}],
                "subject": SUBJECT
            }],
            "from": {"email": FROM_EMAIL, "name": "DevBand"},
            "content": [{
                "type": "text/plain",
                "value": message
            }]
        }

        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }

        r = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers=headers
        )

        if r.status_code == 202:
            self.send_btn.setEnabled(False)
            self.send_btn.setText("Sent ✓")
            self.status.setText("✓")
        else:
            self.status.setText("FAILED")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SnapReportTool()
    window.show()
    sys.exit(app.exec())
