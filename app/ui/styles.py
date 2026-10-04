QSS = """
* {
    font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
}

QMainWindow, QDialog, QWidget#Root {
    background: #0c0b09;
    color: #f3ede2;
}

QWidget#Canvas {
    background: #100f0c;
}

QLabel#Brand {
    color: #f6efe4;
    font-family: "Palatino Linotype", "Georgia", serif;
    font-size: 28px;
    font-weight: 600;
    letter-spacing: 3px;
}

QLabel#Tagline, QLabel#Muted, QLabel#Meta {
    color: #9b9284;
    font-size: 12px;
    letter-spacing: 1px;
}

QLabel#Section {
    color: #d8c4a0;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2.4px;
}

QLabel#Headline {
    color: #f4eee6;
    font-family: "Palatino Linotype", "Georgia", serif;
    font-size: 22px;
}

QLabel#Value {
    color: #f3ede2;
    font-size: 13px;
}

QFrame#Card, QFrame#Panel {
    background: #16140f;
    border: 1px solid #2b261d;
    border-radius: 18px;
}

QFrame#Hairline {
    background: #2b261d;
    max-height: 1px;
    min-height: 1px;
    border: none;
}

QPushButton {
    background: #1d1a14;
    color: #f3ede2;
    border: 1px solid #3a3428;
    border-radius: 12px;
    padding: 10px 16px;
    font-size: 13px;
}

QPushButton:hover {
    background: #262218;
    border-color: #c9a36a;
}

QPushButton:pressed {
    background: #1a1712;
}

QPushButton:disabled {
    color: #6f685c;
    border-color: #2b261d;
}

QPushButton#Primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #d7b072, stop:1 #b8863f);
    color: #1a140c;
    border: none;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 14px 22px;
    font-size: 14px;
}

QPushButton#Primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #e4c48a, stop:1 #c9a36a);
}

QPushButton#Primary:disabled {
    background: #3a3428;
    color: #8a8174;
}

QPushButton#Ghost {
    background: transparent;
    border: 1px solid #3a3428;
}

QPushButton#IconBtn {
    background: transparent;
    border: none;
    color: #c9b89a;
    padding: 4px 8px;
    font-size: 16px;
}

QPushButton#IconBtn:hover {
    color: #f3ede2;
}

QCheckBox {
    color: #f3ede2;
    spacing: 10px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid #5a4e38;
    background: #1a1712;
}

QCheckBox::indicator:checked {
    background: #c9a36a;
    border-color: #c9a36a;
}

QRadioButton {
    color: #e8dfd0;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid #5a4e38;
    background: #1a1712;
}

QRadioButton::indicator:checked {
    background: #c9a36a;
    border-color: #c9a36a;
}

QSlider::groove:horizontal {
    height: 4px;
    background: #2b261d;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -7px 0;
    border-radius: 8px;
    background: #e4c48a;
}

QSlider::sub-page:horizontal {
    background: #c9a36a;
    border-radius: 2px;
}

QProgressBar {
    background: #1a1712;
    border: 1px solid #2b261d;
    border-radius: 8px;
    text-align: center;
    color: #f3ede2;
    height: 14px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #b8863f, stop:1 #e4c48a);
    border-radius: 7px;
}

QScrollArea {
    border: none;
    background: transparent;
}
"""
