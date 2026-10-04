OVERLAY_STYLESHEET = """
QWidget#overlay {
    background-color: rgba(17, 24, 31, 238);
    color: #e8eef2;
    border: 1px solid #35444d;
    border-radius: 8px;
}
QLabel#title {
    color: #68d7d0;
    font-size: 14px;
    font-weight: 700;
}
QLabel#status {
    color: #a7b5bd;
    font-size: 11px;
}
QLabel#cue {
    background-color: rgba(104, 215, 208, 20);
    border-left: 3px solid #68d7d0;
    padding: 8px;
    color: #f2fbfa;
    font-size: 12px;
}
QPlainTextEdit#transcript {
    background-color: rgba(8, 13, 17, 180);
    border: 1px solid #35444d;
    border-radius: 5px;
    color: #e8eef2;
    font-size: 12px;
    selection-background-color: #287e7a;
}
QPushButton {
    background-color: #68d7d0;
    border: none;
    border-radius: 4px;
    color: #10201f;
    font-weight: 700;
    padding: 7px 10px;
}
QPushButton:hover {
    background-color: #8ce4de;
}
QPushButton:disabled {
    background-color: #526269;
    color: #bac5c9;
}
QPushButton#close {
    background-color: transparent;
    color: #a7b5bd;
    font-size: 17px;
    padding: 0 6px;
}
QPushButton#close:hover {
    color: #ffffff;
}
"""

ALERT_STYLESHEET = (
    "color: #FFB4A9; font-weight: bold; font-size: 12px; "
    "background-color: rgba(255, 82, 82, 0.15); padding: 8px; border-radius: 6px;"
)

OVERLAY = OVERLAY_STYLESHEET
HEADER = "color: #68d7d0; font-size: 14px; font-weight: 700;"
CUE = "background-color: rgba(104, 215, 208, 20); border-left: 3px solid #68d7d0; padding: 8px; color: #f2fbfa; font-size: 12px;"
SAVE_BUTTON = "background-color: #68d7d0; color: #10201f; font-weight: 700; padding: 7px 10px; border: none; border-radius: 4px;"
ICON_BUTTON = "QPushButton { background: transparent; color: #94A3B8; border: none; font-size: 14px; font-weight: bold; padding: 0 6px; } QPushButton:hover { color: #FFFFFF; background-color: rgba(255,255,255,0.08); border-radius: 4px; }"
CLOSE_BUTTON = "QPushButton { background: transparent; color: #94A3B8; border: none; font-size: 13px; font-weight: bold; padding: 0 6px; } QPushButton:hover { color: #FF6B6B; background-color: rgba(255,82,82,0.12); border-radius: 4px; }"
PILL = "#pill { background-color: rgba(20, 24, 33, 0.92); border: 1px solid rgba(0, 229, 255, 0.4); border-radius: 14px; }"
PILL_TITLE = "color: #68d7d0; font-weight: bold; font-size: 12px;"
DOT_IDLE = "#64748B"
DOT_CUE = "#00FF87"
DOT_ALERT = "#FF5252"


def dot_style(color: str) -> str:
    return f"color: {color}; font-size: 14px;"
