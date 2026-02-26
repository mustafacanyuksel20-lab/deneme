import sys
import math
import random
import os
import json
import zlib
import csv
import base64
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import deque

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QButtonGroup, QSizePolicy, QGraphicsDropShadowEffect,
    QListWidget, QListWidgetItem, QStackedWidget, QDialog, QFormLayout, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QScrollArea, QProgressBar, QGroupBox, QFileDialog, QTabWidget,
    QAbstractSpinBox
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, QDate
from PyQt5.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QLinearGradient,
    QRadialGradient, QPainterPath, QImage, QPixmap
)
import pyqtgraph as pg
import cv2

# --- MODBUS ---
from pymodbus.client import ModbusTcpClient

# --- PDF / REPORT ---
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors as rl_colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Image as RLImage, Table, TableStyle, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pdfencrypt import StandardEncryption


# ═══════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════
MAX_GRAPH_POINTS = 3600
ANIM_FRAME_MS    = 16
PROCESS_TICK_MS  = 1000
NUM_AHSAP_SENSORS = 12
NUM_ORTAM_SENSORS = 4
NUM_TOTAL_SENSORS = NUM_AHSAP_SENSORS + NUM_ORTAM_SENSORS
SETTINGS_FILENAME = "scada_settings.json"

TURKISH_MONTHS = {
    1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan',
    5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos',
    9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
}
TURKISH_DAYS = {
    0: 'Pazartesi', 1: 'Salı', 2: 'Çarşamba', 3: 'Perşembe',
    4: 'Cuma', 5: 'Cumartesi', 6: 'Pazar'
}


# ═══════════════════════════════════════════════════════════
#  COLOR PALETTE
# ═══════════════════════════════════════════════════════════
class CLR:
    BG      = "#0f172a"
    SIDEBAR = "#1e293b"
    CARD    = "#1e293b"
    BORDER  = "#334155"
    INPUT   = "#0f172a"
    ACCENT  = "#38bdf8"
    GREEN   = "#10b981"
    GREEN_D = "#059669"
    GREEN_L = "#34d399"
    RED     = "#ef4444"
    RED_D   = "#dc2626"
    ORANGE  = "#f59e0b"
    PURPLE  = "#a78bfa"
    CYAN    = "#22d3ee"
    TEXT    = "#f8fafc"
    TEXT2   = "#94a3b8"
    TEXT3   = "#64748b"
    TEXT4   = "#475569"
    DIMMED  = "#334155"



# --- SPINBOX ARROW ASSETS ---
_UP_ARROW_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAKCAYAAAC9vt6cAAAAPklEQVR4nGNgoDWwvPD/Pz55JmI04zMEe/bs+Y8u5uNATF29evV/Ui5iNMUFnKUoJzGa8gLOUpSTwBsAAJ3tHzEjaTKRAAAAAElFTkSuQmCC"
_DOWN_ARROW_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAKCAYAAAC9vt6cAAAAR0lEQVR4nGNgoBAwwhiWF/7/J1XzcQNGDIDVq1f/J8UYgJgC1q5d+58ZiLEAowvYv3//f1IuYjSFBZylKCcxmvICzlKUk8AOAK98Nn52EYkpAAAAAElFTkSuQmCC"

def _ensure_spin_arrow_assets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    up_path = os.path.join(base_dir, "_spin_up_arrow.png")
    down_path = os.path.join(base_dir, "_spin_down_arrow.png")
    if not os.path.exists(up_path):
        with open(up_path, "wb") as f:
            f.write(base64.b64decode(_UP_ARROW_PNG_B64))
    if not os.path.exists(down_path):
        with open(down_path, "wb") as f:
            f.write(base64.b64decode(_DOWN_ARROW_PNG_B64))
    # Qt stylesheet için file URL
    up_url = up_path.replace("\\", "/")
    down_url = down_path.replace("\\", "/")
    if not up_url.startswith("/"):
        up_url = "/" + up_url
    if not down_url.startswith("/"):
        down_url = "/" + down_url
    return f"file://{up_url}", f"file://{down_url}"

SPIN_UP_ARROW_URL, SPIN_DOWN_ARROW_URL = _ensure_spin_arrow_assets()

# ═══════════════════════════════════════════════════════════
#  STYLESHEET
# ═══════════════════════════════════════════════════════════
STYLESHEET = f"""
QMainWindow {{ background-color: {CLR.BG}; }}
QWidget {{ color: {CLR.TEXT}; }}
QToolTip {{
    background: {CLR.CARD}; color: {CLR.TEXT};
    border: 1px solid {CLR.ACCENT}; padding: 5px; border-radius: 4px;
}}

/* ── SIDEBAR ── */
#Sidebar {{
    background-color: {CLR.SIDEBAR}; border-right: 1px solid {CLR.BORDER};
    min-width: 260px; max-width: 260px;
}}
#SidebarLogo {{
    color: {CLR.ACCENT}; font-size: 20px; font-weight: 900;
    letter-spacing: 1.5px; padding: 25px 20px;
    border-bottom: 1px solid {CLR.BORDER};
}}
#SidebarClock {{
    color: {CLR.TEXT}; font-family: 'Consolas'; font-size: 20px;
    font-weight: bold; padding: 15px;
}}
#SidebarDate {{
    color: {CLR.ACCENT}; font-size: 15px; font-weight: bold;
    padding: 0 15px 5px 15px;
}}
#SidebarDay {{
    color: {CLR.TEXT}; font-size: 13px; font-weight: 600;
    padding: 0 15px 15px 15px;
}}

QPushButton.navBtn {{
    text-align: left; padding: 16px 25px; background: transparent;
    border: none; border-left: 4px solid transparent;
    color: {CLR.TEXT2}; font-size: 14px; font-weight: 600;
}}
QPushButton.navBtn:hover {{ background: {CLR.BORDER}; color: white; }}
QPushButton.navBtn:checked {{
    background: rgba(56, 189, 248, 0.08); color: {CLR.ACCENT};
    border-left: 4px solid {CLR.ACCENT}; font-weight: bold;
}}

/* ── HEADER ── */
#HeaderFrame {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {CLR.SIDEBAR}, stop:1 {CLR.BG}
    );
    border-radius: 14px; border: 1px solid {CLR.BORDER};
}}
#HeaderLine {{ border-radius: 2px; }}

/* ── STATUS BADGE ── */
QLabel#statusBadge[status="idle"] {{
    background: rgba(148,163,184,0.1); color: {CLR.TEXT2};
    border: 1px solid {CLR.TEXT4}; border-radius: 12px;
    padding: 5px 14px; font-weight: bold; font-size: 13px;
}}
QLabel#statusBadge[status="heating"] {{
    background: rgba(245,158,11,0.15); color: {CLR.ORANGE};
    border: 1px solid {CLR.ORANGE}; border-radius: 12px;
    padding: 5px 14px; font-weight: bold; font-size: 13px;
}}
QLabel#statusBadge[status="running"] {{
    background: rgba(16,185,129,0.15); color: #34d399;
    border: 1px solid {CLR.GREEN}; border-radius: 12px;
    padding: 5px 14px; font-weight: bold; font-size: 13px;
}}
QLabel#statusBadge[status="stopped"] {{
    background: rgba(239,68,68,0.15); color: #f87171;
    border: 1px solid {CLR.RED}; border-radius: 12px;
    padding: 5px 14px; font-weight: bold; font-size: 13px;
}}
QLabel#statusBadge[status="done"] {{
    background: rgba(56,189,248,0.15); color: {CLR.ACCENT};
    border: 1px solid {CLR.ACCENT}; border-radius: 12px;
    padding: 5px 14px; font-weight: bold; font-size: 13px;
}}

/* ── CARDS ── */
QFrame.card {{
    background-color: {CLR.CARD}; border: 1px solid {CLR.BORDER};
    border-radius: 12px;
}}

/* ── SENSOR NODES ── */
QFrame.sensorNode {{
    background-color: {CLR.BG}; border-radius: 8px;
    border: 1px solid {CLR.BORDER};
}}
QFrame.sensorNode[status="wait"] {{ border-left: 4px solid {CLR.ORANGE}; }}
QFrame.sensorNode[status="ok"] {{
    border-left: 4px solid {CLR.GREEN_L};
    background: rgba(16,185,129,0.18);
    border-color: rgba(52,211,153,0.4);
}}
QFrame.sensorNode[status="off"] {{
    border-left: 4px solid {CLR.BORDER};
    background: rgba(15,23,42,0.5);
}}
QFrame.sensorNode[status="stop"] {{ border-left: 4px solid {CLR.RED}; }}

QLabel.nodeTitle {{
    color: {CLR.TEXT2}; font-size: 10px; font-weight: 800;
    letter-spacing: 0.5px;
}}
QLabel.nodeValue {{
    color: {CLR.TEXT}; font-size: 24px; font-weight: 900;
    font-family: 'Segoe UI';
}}
QLabel.nodeMinMax {{
    color: {CLR.TEXT2}; font-size: 12px; font-family: 'Consolas';
    font-weight: bold; letter-spacing: 0.3px;
}}

/* ── INPUT / FORM ── */
QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {{
    background: {CLR.INPUT}; color: {CLR.TEXT};
    border: 1px solid {CLR.BORDER}; border-radius: 6px;
    padding: 8px 12px; font-size: 13px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {CLR.ACCENT};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    width: 30px;
    background: #10213f;
    border-left: 1px solid #475569;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-position: top right;
    border-top-right-radius: 6px;
    border-bottom: 1px solid #475569;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-position: bottom right;
    border-bottom-right-radius: 6px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: #183764;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({SPIN_UP_ARROW_URL});
    width: 16px;
    height: 10px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({SPIN_DOWN_ARROW_URL});
    width: 16px;
    height: 10px;
}}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background: #0ea5e9;
}}
QSpinBox, QDoubleSpinBox {{
    padding-right: 38px;
}}
QCheckBox, QRadioButton {{ color: {CLR.TEXT}; font-size: 13px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border: 2px solid {CLR.TEXT4};
    border-radius: 4px; background: {CLR.INPUT};
}}
QCheckBox::indicator:checked {{
    background: {CLR.ACCENT}; border-color: {CLR.ACCENT};
}}
QRadioButton::indicator {{
    width: 18px; height: 18px; border: 2px solid {CLR.TEXT4};
    border-radius: 9px; background: {CLR.INPUT};
}}
QRadioButton::indicator:checked {{
    background: {CLR.ACCENT}; border-color: {CLR.ACCENT};
}}

/* ── GROUPBOX ── */
QGroupBox {{
    font-size: 13px; font-weight: bold; color: {CLR.ACCENT};
    border: 1px solid {CLR.BORDER}; border-radius: 10px;
    margin-top: 18px; padding: 18px 12px 12px 12px;
    background: {CLR.SIDEBAR};
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 15px; padding: 2px 8px;
    background: {CLR.SIDEBAR};
}}

/* ── LOG LIST ── */
QListWidget {{
    background: {CLR.BG}; border: 1px solid {CLR.BORDER};
    border-radius: 6px; color: {CLR.TEXT2};
    font-family: 'Consolas'; font-size: 11px; padding: 4px;
}}
QListWidget::item {{
    padding: 3px 6px; border-bottom: 1px solid {CLR.BORDER};
}}

/* ── TABLE ── */
QTableWidget {{
    background: {CLR.SIDEBAR}; color: {CLR.TEXT};
    border: 1px solid {CLR.BORDER}; border-radius: 8px;
    gridline-color: {CLR.BORDER}; font-size: 12px;
}}
QTableWidget::item {{ padding: 5px; }}
QTableWidget::item:selected {{
    background: rgba(56,189,248,0.15); color: {CLR.ACCENT};
}}
QHeaderView::section {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {CLR.CARD}, stop:1 {CLR.BG}
    );
    color: {CLR.ACCENT}; font-weight: bold; font-size: 11px;
    border: none; border-bottom: 2px solid {CLR.ACCENT}; padding: 8px;
}}

/* ── BUTTONS ── */
QPushButton.actionBtn {{
    border-radius: 8px; font-size: 14px; font-weight: bold;
    padding: 12px 20px; color: white; border: none;
}}
#btnStart {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 {CLR.GREEN}, stop:1 {CLR.GREEN_D}
    );
    border: 1px solid #34d399;
}}
#btnStart:hover {{ background: #34d399; }}
#btnStart:disabled {{
    background: {CLR.BORDER}; color: {CLR.TEXT3};
    border-color: {CLR.BORDER};
}}
#btnStop {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 {CLR.RED}, stop:1 {CLR.RED_D}
    );
    border: 1px solid #f87171;
}}
#btnStop:hover {{ background: #f87171; }}
#btnStop:disabled {{
    background: {CLR.BORDER}; color: {CLR.TEXT3};
    border-color: {CLR.BORDER};
}}

QPushButton.flatBtn {{
    background: transparent; border: 1px solid {CLR.BORDER};
    border-radius: 6px; padding: 8px 14px;
    color: {CLR.TEXT2}; font-weight: bold;
}}
QPushButton.flatBtn:hover {{ background: {CLR.BORDER}; color: white; }}

QPushButton.accentBtn {{
    background: {CLR.ACCENT}; border: none; border-radius: 6px;
    padding: 10px 20px; color: {CLR.BG}; font-weight: bold; font-size: 13px;
}}
QPushButton.accentBtn:hover {{ background: #7dd3fc; }}

QPushButton.greenBtn {{
    background: {CLR.GREEN}; border: none; border-radius: 6px;
    padding: 10px 20px; color: white; font-weight: bold; font-size: 13px;
}}
QPushButton.greenBtn:hover {{ background: #34d399; }}

QPushButton.orangeBtn {{
    background: {CLR.ORANGE}; border: none; border-radius: 6px;
    padding: 10px 20px; color: {CLR.BG}; font-weight: bold; font-size: 13px;
}}
QPushButton.orangeBtn:hover {{ background: #fbbf24; }}

/* ── PROGRESS BAR ── */
QProgressBar {{
    background: {CLR.BG}; border: 1px solid {CLR.BORDER};
    border-radius: 6px; text-align: center; color: {CLR.TEXT};
    font-weight: bold; font-size: 11px;
    min-height: 16px; max-height: 16px;
}}
QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {CLR.GREEN_D}, stop:1 {CLR.GREEN}
    );
    border-radius: 5px;
}}

/* ── SCROLLBAR ── */
QScrollBar:vertical {{
    background: {CLR.BG}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {CLR.TEXT4}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {CLR.ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


# ═══════════════════════════════════════════════════════════
#  SETTINGS MANAGER
# ═══════════════════════════════════════════════════════════
class SettingsManager:
    DEFAULTS: Dict = {
        'alt_limit': 56.0,
        'ust_limit': 80.0,
        'islem_suresi_dk': 30,
        'fan_modu': 'cift',
        'fan_sag_dk': 10,
        'fan_sol_dk': 10,
        'fan_bekleme_dk': 2,
        'active_ahsap': [0, 1],
        'active_ortam': [0, 1],
    }

    def __init__(self, path: Optional[str] = None):
        if path is None:
            base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, SETTINGS_FILENAME)
        self._path = path

    def load(self) -> Dict:
        data = dict(self.DEFAULTS)
        if os.path.exists(self._path):
            try:
                with open(self._path, 'r', encoding='utf-8') as f:
                    stored = json.load(f)
                data.update(stored)
            except (json.JSONDecodeError, IOError):
                pass
        return data

    def save(self, data: Dict) -> None:
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════
#  KILN ANIMATION WIDGET
# ═══════════════════════════════════════════════════════════
class SmoothKilnWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(380, 300)
        self._fan_angle: float = 0.0
        self._flow_offset: float = 0.0
        self._is_running: bool = False
        self._heat_glow: float = 0.0
        self._fan_direction: int = 1
        self._fan_spinning: bool = True

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)

    def start(self) -> None:
        self._is_running = True
        self._fan_spinning = True
        self._anim_timer.start(ANIM_FRAME_MS)

    def stop(self) -> None:
        self._is_running = False
        self._fan_spinning = False
        self._anim_timer.stop()
        self._heat_glow = 0.0
        self.update()

    def set_fan_direction(self, d: int) -> None:
        self._fan_direction = d

    def set_fan_spinning(self, spinning: bool) -> None:
        self._fan_spinning = spinning

    def _animate(self) -> None:
        if self._fan_spinning:
            self._fan_angle = (self._fan_angle + 8 * self._fan_direction) % 360
            self._flow_offset = (self._flow_offset - 1.5 * self._fan_direction) % 40
        if self._heat_glow < 1.0:
            self._heat_glow = min(1.0, self._heat_glow + 0.004)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        rect = QRectF(10, 10, w - 20, h - 20)
        wall = 14
        inner = rect.adjusted(wall, wall, -wall, -wall)

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor("#475569"))
        grad.setColorAt(1, QColor("#1e293b"))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(CLR.BG), 2))
        p.drawRoundedRect(rect, 8, 8)

        base = QColor(CLR.BG)
        hot = QColor(60, 20, 10)
        gl = self._heat_glow
        r = int(base.red() * (1 - gl) + hot.red() * gl)
        g = int(base.green() * (1 - gl) + hot.green() * gl)
        b = int(base.blue() * (1 - gl) + hot.blue() * gl)
        p.setBrush(QBrush(QColor(r, g, b)))
        p.setPen(QPen(QColor("#000"), 3))
        p.drawRect(inner)

        if self._is_running:
            rad = QRadialGradient(w / 2, h / 2, w / 1.5)
            rad.setColorAt(0, QColor(255, 100, 50, int(55 * gl)))
            rad.setColorAt(1, Qt.transparent)
            p.setBrush(QBrush(rad))
            p.setPen(Qt.NoPen)
            p.drawRect(inner)

        p.setPen(QPen(QColor(CLR.TEXT2), 2))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(inner.left(), inner.top() + 70)
        path.quadTo(inner.left() + 18, inner.top() + 18,
                    inner.left() + 90, inner.top())
        path.moveTo(inner.right(), inner.top() + 70)
        path.quadTo(inner.right() - 18, inner.top() + 18,
                    inner.right() - 90, inner.top())
        p.drawPath(path)

        fan_y = inner.top() + 45
        self._draw_fan(p, w / 2 - 80, fan_y, 36)
        self._draw_fan(p, w / 2 + 80, fan_y, 36)

        h_top = fan_y + 45
        h_bot = inner.bottom() - 25
        if self._is_running:
            pulse = 180 + int(70 * math.sin(self._fan_angle * 0.05))
            glow_c = QColor(255, 80, 20, pulse)
            p.setPen(QPen(glow_c, 7, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(inner.left() + 22, h_top),
                       QPointF(inner.left() + 22, h_bot))
            p.drawLine(QPointF(inner.right() - 22, h_top),
                       QPointF(inner.right() - 22, h_bot))
            p.setPen(QPen(QColor(255, 255, 200), 2, Qt.DotLine))
            p.drawLine(QPointF(inner.left() + 22, h_top),
                       QPointF(inner.left() + 22, h_bot))
            p.drawLine(QPointF(inner.right() - 22, h_top),
                       QPointF(inner.right() - 22, h_bot))

        sw = inner.width() * 0.55
        sh = inner.height() * 0.42
        sr = QRectF((w - sw) / 2, inner.bottom() - sh - 8, sw, sh)
        self._draw_stack(p, sr)

        if self._is_running and self._fan_spinning:
            self._draw_flow(p, inner, sr, fan_y)

    def _draw_fan(self, p: QPainter, x: float, y: float, r: int) -> None:
        p.save()
        p.translate(x, y)
        p.setPen(QPen(QColor(CLR.TEXT4), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, 0), r + 2, r + 2)

        spinning = self._is_running and self._fan_spinning
        blade_col = QColor(CLR.ACCENT) if spinning else QColor(CLR.TEXT4)

        if spinning:
            p.rotate(self._fan_angle)
            blur = QRadialGradient(0, 0, r)
            blur.setColorAt(0, Qt.transparent)
            blur.setColorAt(0.8, QColor(56, 189, 248, 40))
            blur.setColorAt(1, Qt.transparent)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(blur))
            p.drawEllipse(QPointF(0, 0), r, r)

        p.setBrush(QBrush(blade_col))
        p.setPen(Qt.NoPen)
        for _ in range(3):
            p.drawPie(QRectF(-r, -r, r * 2, r * 2), 0, 40 * 16)
            p.rotate(120)

        if self._is_running and not self._fan_spinning:
            p.setBrush(QBrush(QColor(CLR.ORANGE)))
            p.drawEllipse(QPointF(0, 0), 10, 10)
            p.setPen(QPen(QColor(CLR.BG), 2))
            p.drawLine(QPointF(-4, -4), QPointF(4, 4))
            p.drawLine(QPointF(-4, 4), QPointF(4, -4))
        else:
            p.setBrush(QBrush(QColor("#e2e8f0")))
            p.drawEllipse(QPointF(0, 0), 7, 7)
        p.restore()

    def _draw_stack(self, p: QPainter, rect: QRectF) -> None:
        p.setBrush(QBrush(QColor("#3f2e18")))
        p.setPen(Qt.NoPen)
        p.drawRect(QRectF(rect.left(), rect.bottom(), 22, 8))
        p.drawRect(QRectF(rect.center().x() - 11, rect.bottom(), 22, 8))
        p.drawRect(QRectF(rect.right() - 22, rect.bottom(), 22, 8))

        layers = 5
        step = rect.height() / layers
        p.setPen(QPen(QColor("#78350f"), 1))
        for i in range(layers):
            y = rect.bottom() - (i + 1) * step
            if i < layers - 1:
                p.setBrush(QBrush(QColor("#271502")))
                p.drawRect(QRectF(rect.left() + 8, y - 4,
                                  rect.width() - 16, 4))
            p.setBrush(QBrush(QColor("#d97706")))
            blocks = 6
            bw = rect.width() / blocks
            for k in range(blocks):
                p.drawRect(QRectF(rect.left() + k * bw + 2, y,
                                  bw - 4, step - 4))

    def _draw_flow(self, p: QPainter, bounds: QRectF,
                   stack: QRectF, fan_y: float) -> None:
        path = QPainterPath()
        path.moveTo(bounds.center().x() - 45, fan_y + 28)
        path.lineTo(bounds.left() + 38, fan_y + 28)
        path.lineTo(bounds.left() + 38, bounds.bottom() - 28)
        path.lineTo(stack.left() + 35, bounds.bottom() - 28)
        path.lineTo(stack.left() + 35, stack.top() + 18)

        path.moveTo(bounds.center().x() + 45, fan_y + 28)
        path.lineTo(bounds.right() - 38, fan_y + 28)
        path.lineTo(bounds.right() - 38, bounds.bottom() - 28)
        path.lineTo(stack.right() - 35, bounds.bottom() - 28)
        path.lineTo(stack.right() - 35, stack.top() + 18)

        col = (QColor(255, 120, 50, 200)
               if self._heat_glow > 0.5
               else QColor(0, 200, 255, 180))
        pen = QPen(col, 3)
        pen.setStyle(Qt.CustomDashLine)
        pen.setDashPattern([10, 10])
        pen.setDashOffset(self._flow_offset)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)


# ═══════════════════════════════════════════════════════════
#  MODERN POPUP DIALOG
# ═══════════════════════════════════════════════════════════
class ModernPopUp(QDialog):
    def __init__(self, title: str, message: str,
                 dtype: str = "info", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(460, 250)
        self._drag_pos: Optional[QPointF] = None

        type_colors = {
            "info": CLR.ACCENT, "warning": CLR.ORANGE,
            "critical": CLR.RED, "success": CLR.GREEN,
        }
        type_icons = {
            "info": "ℹ", "warning": "⚠",
            "critical": "✕", "success": "✓",
        }
        tc = type_colors.get(dtype, CLR.ACCENT)
        ti = type_icons.get(dtype, "ℹ")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {CLR.SIDEBAR};
                border: 1px solid {tc};
                border-top: 4px solid {tc};
                border-radius: 12px;
            }}
        """)
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(30)
        sh.setColor(QColor(tc))
        sh.setOffset(0, 0)
        frame.setGraphicsEffect(sh)

        fl = QVBoxLayout(frame)
        fl.setContentsMargins(25, 18, 25, 18)
        fl.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel(ti,
            styleSheet=f"color:{tc}; font-size:22px; border:none;"))
        hdr.addWidget(QLabel(title,
            styleSheet=f"color:{tc}; font-size:15px; font-weight:bold; border:none;"))
        hdr.addStretch()
        fl.addLayout(hdr)

        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{CLR.TEXT}; font-size:13px; border:none;")
        fl.addWidget(lbl)
        fl.addStretch()

        bl = QHBoxLayout()
        bl.addStretch()
        btn = QPushButton("TAMAM")
        btn.setFixedWidth(110)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{tc}; color:white; border-radius:6px;
                padding:9px; font-weight:bold;
            }}
            QPushButton:hover {{ background:white; color:{tc}; }}
        """)
        btn.clicked.connect(self.accept)
        bl.addWidget(btn)
        fl.addLayout(bl)
        layout.addWidget(frame)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.pos()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e) -> None:
        self._drag_pos = None


# ═══════════════════════════════════════════════════════════
#  CAMERA EVIDENCE DIALOG  (from ıspm_son_versiyon.py)
# ═══════════════════════════════════════════════════════════
class ProcessCameraDialog(QDialog):
    def __init__(self, video_klasoru: str, mode: str = "start",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(720, 620)
        self.video_klasoru = video_klasoru
        self.mode = mode
        self.img_step1_b64 = None
        self.img_step2_b64 = None
        self.is_recording = False
        self.record_step = 1
        self.kalan_sure = 10
        self.video_writer = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {CLR.SIDEBAR};
                border: 1px solid {CLR.ACCENT};
                border-top: 4px solid {CLR.ACCENT};
                border-radius: 12px;
            }}
        """)
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(30); sh.setColor(QColor(CLR.ACCENT)); sh.setOffset(0, 0)
        frame.setGraphicsEffect(sh)

        fl = QVBoxLayout(frame)
        fl.setContentsMargins(20, 15, 20, 15)

        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet(
            f"color:{CLR.ORANGE}; font-size:16px; font-weight:bold; border:none;")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        fl.addWidget(self.lbl_title)

        self.lbl_kamera = QLabel("Kamera Yükleniyor...")
        self.lbl_kamera.setAlignment(Qt.AlignCenter)
        self.lbl_kamera.setStyleSheet(
            f"background:{CLR.BG}; border:2px solid {CLR.BORDER}; "
            f"font-size:16px; color:{CLR.TEXT3}; border-radius:6px;")
        self.lbl_kamera.setMinimumSize(660, 400)
        fl.addWidget(self.lbl_kamera)

        self.lbl_sayac = QLabel("")
        self.lbl_sayac.setStyleSheet(
            f"color:{CLR.RED}; font-size:20px; font-weight:bold; border:none;")
        self.lbl_sayac.setAlignment(Qt.AlignCenter)
        fl.addWidget(self.lbl_sayac)

        btn_layout = QHBoxLayout()
        self.btn_iptal = QPushButton("İŞLEMİ İPTAL ET")
        self.btn_iptal.setProperty("class", "flatBtn")
        self.btn_iptal.clicked.connect(self.reject)

        self.btn_aksiyon = QPushButton("")
        self.btn_aksiyon.setProperty("class", "accentBtn")
        self.btn_aksiyon.clicked.connect(self.baslat_kayit)

        btn_layout.addWidget(self.btn_iptal)
        btn_layout.addWidget(self.btn_aksiyon)
        fl.addLayout(btn_layout)
        layout.addWidget(frame)

        if self.mode == "start":
            self.lbl_title.setText("📷  ZORUNLU KANIT KAYDI: 1. ADIM — BOŞ FIRIN")
            self.btn_aksiyon.setText("BOŞ FIRIN FOTOĞRAFI VE VİDEOSU ÇEK (10 SN)")
            self.file_1 = "TEMP_BOS.mp4"
            self.file_2 = "TEMP_DOLU.mp4"
        else:
            self.lbl_title.setText("📷  İŞLEM BİTİŞ KANITI: 1. ADIM — DOLU FIRIN")
            self.btn_aksiyon.setText("DOLU FIRIN FOTOĞRAFI VE VİDEOSU ÇEK (10 SN)")
            self.btn_iptal.hide()
            self.file_1 = "TEMP_SON_DOLU.mp4"
            self.file_2 = "TEMP_SON_BOS.mp4"

        self.cap = cv2.VideoCapture(0)
        self.cam_timer = QTimer()
        self.cam_timer.timeout.connect(self.update_frame)
        self.cam_timer.start(30)
        self.sayac_timer = QTimer()
        self.sayac_timer.timeout.connect(self.sayac_guncelle)

        for fn in [self.file_1, self.file_2]:
            p = os.path.join(self.video_klasoru, fn)
            if os.path.exists(p):
                os.remove(p)

    def reject(self):
        if self.mode == "end":
            ModernPopUp("UYARI",
                "İşlemi arşivlemek için kanıt kaydı zorunludur!",
                "warning", self).exec_()
        else:
            self.cam_timer.stop()
            if self.cap:
                self.cap.release()
            if self.video_writer:
                self.video_writer.release()
            super().reject()

    def update_frame(self):
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                if self.is_recording and self.video_writer is not None:
                    self.video_writer.write(frame)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame_rgb.shape
                qt_img = QImage(frame_rgb.data, w, h, ch * w,
                                QImage.Format_RGB888)
                self.lbl_kamera.setPixmap(
                    QPixmap.fromImage(qt_img).scaled(
                        self.lbl_kamera.width(), self.lbl_kamera.height(),
                        Qt.KeepAspectRatio))

    def baslat_kayit(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        if self.record_step == 1:
            _, buf = cv2.imencode('.jpg', frame)
            self.img_step1_b64 = base64.b64encode(buf).decode('utf-8')
            path = os.path.join(self.video_klasoru, self.file_1)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                path, fourcc, 20.0, (frame.shape[1], frame.shape[0]))
            self.record_step = 2
            mesaj = ("BOŞ FIRIN KAYDEDİLİYOR..." if self.mode == "start"
                     else "DOLU FIRIN KAYDEDİLİYOR...")
            self._start_recording_ui(mesaj)
        elif self.record_step == 3:
            _, buf = cv2.imencode('.jpg', frame)
            self.img_step2_b64 = base64.b64encode(buf).decode('utf-8')
            path = os.path.join(self.video_klasoru, self.file_2)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                path, fourcc, 20.0, (frame.shape[1], frame.shape[0]))
            self.record_step = 4
            mesaj = ("DOLU FIRIN KAYDEDİLİYOR..." if self.mode == "start"
                     else "BOŞ FIRIN KAYDEDİLİYOR...")
            self._start_recording_ui(mesaj)
        elif self.record_step == 5:
            self.cam_timer.stop()
            if self.cap:
                self.cap.release()
            self.accept()

    def _start_recording_ui(self, mesaj: str):
        self.btn_aksiyon.setEnabled(False)
        self.btn_iptal.setEnabled(False)
        self.lbl_title.setText(f"🔴  {mesaj}")
        self.lbl_title.setStyleSheet(
            f"color:{CLR.RED}; font-size:16px; font-weight:bold; border:none;")
        self.kalan_sure = 10
        self.lbl_sayac.setText(f"KAYIT DEVAM EDİYOR: {self.kalan_sure} SN")
        self.is_recording = True
        self.sayac_timer.start(1000)

    def sayac_guncelle(self):
        self.kalan_sure -= 1
        self.lbl_sayac.setText(f"KAYIT DEVAM EDİYOR: {self.kalan_sure} SN")
        if self.kalan_sure <= 0:
            self.sayac_timer.stop()
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.btn_aksiyon.setEnabled(True)
            if self.mode == "start":
                self.btn_iptal.setEnabled(True)
            self.lbl_sayac.setText("")

            if self.record_step == 2:
                self.record_step = 3
                if self.mode == "start":
                    self.lbl_title.setText(
                        "📷  ZORUNLU KANIT KAYDI: 2. ADIM — DOLU FIRIN")
                    self.lbl_title.setStyleSheet(
                        f"color:{CLR.GREEN}; font-size:16px; "
                        f"font-weight:bold; border:none;")
                    self.btn_aksiyon.setText(
                        "DOLU FIRIN FOTOĞRAFI VE VİDEOSU ÇEK (10 SN)")
                    self.btn_aksiyon.setStyleSheet(
                        f"background:{CLR.GREEN}; color:white; "
                        f"border-radius:6px; padding:10px 20px; font-weight:bold;")
                    ModernPopUp("BİLGİ",
                        "Boş fırın kaydı tamamlandı.\n"
                        "Lütfen fırını doldurun ve hazır olduğunuzda butona basın.",
                        "info", self).exec_()
                else:
                    self.lbl_title.setText(
                        "📷  İŞLEM BİTİŞ KANITI: 2. ADIM — BOŞ FIRIN")
                    self.lbl_title.setStyleSheet(
                        f"color:{CLR.GREEN}; font-size:16px; "
                        f"font-weight:bold; border:none;")
                    self.btn_aksiyon.setText(
                        "BOŞ FIRIN FOTOĞRAFI VE VİDEOSU ÇEK (10 SN)")
                    self.btn_aksiyon.setStyleSheet(
                        f"background:{CLR.GREEN}; color:white; "
                        f"border-radius:6px; padding:10px 20px; font-weight:bold;")
                    ModernPopUp("BİLGİ",
                        "Dolu fırın (Bitiş) kaydı tamamlandı.\n"
                        "Lütfen fırını BOŞALTIN ve hazır olduğunuzda butona basın.",
                        "info", self).exec_()

            elif self.record_step == 4:
                self.record_step = 5
                self.lbl_title.setText("✅  TÜM KAYITLAR TAMAMLANDI")
                self.lbl_title.setStyleSheet(
                    f"color:{CLR.ACCENT}; font-size:16px; "
                    f"font-weight:bold; border:none;")
                if self.mode == "start":
                    self.btn_aksiyon.setText("ONAYLA VE FİRMA BİLGİLERİNİ GİR")
                else:
                    self.btn_aksiyon.setText("ONAYLA VE RAPORU OLUŞTUR")
                self.btn_aksiyon.setStyleSheet(
                    f"background:{CLR.ORANGE}; color:{CLR.BG}; "
                    f"border-radius:6px; padding:12px 20px; "
                    f"font-size:14px; font-weight:bold;")
                self.btn_iptal.hide()


# ═══════════════════════════════════════════════════════════
#  PROCESS SETTINGS DIALOG
# ═══════════════════════════════════════════════════════════
class PlusMinusSpinBase(QWidget):
    def __init__(self, spin, parent=None):
        super().__init__(parent)
        self.spin = spin
        self.spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.spin, 1)

        btn_col = QVBoxLayout()
        btn_col.setContentsMargins(0, 0, 0, 0)
        btn_col.setSpacing(4)

        self.btn_up = QPushButton('+')
        self.btn_down = QPushButton('−')
        for btn in (self.btn_up, self.btn_down):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(30, 18)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{CLR.ACCENT};
                    color:#ffffff;
                    border:none;
                    border-radius:4px;
                    font-size:15px;
                    font-weight:900;
                    padding:0px;
                }}
                QPushButton:hover {{ background:#0ea5e9; }}
                QPushButton:pressed {{ background:{CLR.GREEN}; }}
                QPushButton:disabled {{ background:#334155; color:#94a3b8; }}
            """)
        self.btn_up.clicked.connect(self.spin.stepUp)
        self.btn_down.clicked.connect(self.spin.stepDown)
        btn_col.addWidget(self.btn_up)
        btn_col.addWidget(self.btn_down)
        btn_col.addStretch(1)
        layout.addLayout(btn_col)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.spin.setEnabled(enabled)
        self.btn_up.setEnabled(enabled)
        self.btn_down.setEnabled(enabled)

    def __getattr__(self, name):
        return getattr(self.spin, name)


class PlusMinusSpinBox(PlusMinusSpinBase):
    def __init__(self, parent=None):
        super().__init__(QSpinBox(), parent)


class PlusMinusDoubleSpinBox(PlusMinusSpinBase):
    def __init__(self, parent=None):
        super().__init__(QDoubleSpinBox(), parent)


class ProcessSettingsDialog(QDialog):
    def __init__(self, ayarlar: Dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(680, 470)
        self._drag_pos: Optional[QPointF] = None
        self.ayarlar = ayarlar

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {CLR.SIDEBAR};
                border: 1px solid {CLR.GREEN};
                border-top: 4px solid {CLR.GREEN};
                border-radius: 12px;
            }}
        """)
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(40); sh.setColor(QColor(CLR.GREEN)); sh.setOffset(0, 0)
        frame.setGraphicsEffect(sh)

        fl = QVBoxLayout(frame)
        fl.setContentsMargins(25, 18, 25, 18)
        fl.setSpacing(10)

        fl.addWidget(QLabel("⚙  YENİ İŞLEM PARAMETRELERİ",
            styleSheet=(f"color:{CLR.GREEN}; font-size:17px; "
                        f"font-weight:bold; border:none;")))

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(
            f"background:{CLR.BORDER}; max-height:1px; border:none;")
        fl.addWidget(sep)

        ls = (f"color:{CLR.TEXT2}; font-size:12px; "
              f"font-weight:bold; border:none;")
        form = QFormLayout()
        form.setSpacing(10)

        self.txt_firma = QLineEdit()
        self.txt_firma.setPlaceholderText("Firma adını giriniz...")
        self.txt_urun = QLineEdit()
        self.txt_urun.setPlaceholderText("Ürün adını giriniz...")
        self.spin_adet = PlusMinusSpinBox()
        self.spin_adet.setRange(1, 99999)
        self.spin_adet.setValue(1)
        self.spin_m3 = PlusMinusDoubleSpinBox()
        self.spin_m3.setRange(0.1, 99999.0)
        self.spin_m3.setValue(1.0)
        self.spin_m3.setDecimals(2)
        self.spin_m3.setSuffix("  m³")
        self.spin_sicaklik = PlusMinusDoubleSpinBox()
        set_min = 56.0
        set_max = max(set_min, float(ayarlar['ust_limit']))
        self.spin_sicaklik.setRange(set_min, set_max)
        self.spin_sicaklik.setValue(set_min)
        self.spin_sicaklik.setSuffix(" °C")
        self.spin_sicaklik.setDecimals(1)

        form.addRow(QLabel("FİRMA İSMİ (*):", styleSheet=ls), self.txt_firma)
        form.addRow(QLabel("ÜRÜN İSMİ (*):", styleSheet=ls), self.txt_urun)
        form.addRow(QLabel("ÜRÜN ADETİ:", styleSheet=ls), self.spin_adet)
        form.addRow(QLabel("HACİM (m³):", styleSheet=ls), self.spin_m3)
        form.addRow(QLabel(
            f"SET SICAKLIĞI "
            f"(56–{set_max:.0f}°C):",
            styleSheet=ls), self.spin_sicaklik)
        fl.addLayout(form)

        info = QLabel("📡  Aktif sensörler Sistem Ayarları sayfasından alınır.")
        info.setStyleSheet(f"color:{CLR.CYAN}; font-size:12px; font-weight:bold; border:none;")
        fl.addWidget(info)
        fl.addStretch()

        bl = QHBoxLayout()
        btn_no = QPushButton("İPTAL")
        btn_no.setProperty("class", "flatBtn")
        btn_no.setFixedWidth(130)
        btn_no.clicked.connect(self.reject)
        btn_yes = QPushButton("✓  KAYDET VE BAŞLAT")
        btn_yes.setProperty("class", "greenBtn")
        btn_yes.clicked.connect(self._try_accept)
        bl.addWidget(btn_no)
        bl.addStretch()
        bl.addWidget(btn_yes)
        fl.addLayout(bl)
        layout.addWidget(frame)

    def get_active_sensors(self) -> Tuple[List[int], List[int]]:
        return (
            list(self.ayarlar.get('active_ahsap', [0, 1])),
            list(self.ayarlar.get('active_ortam', [0, 1])),
        )

    def _try_accept(self) -> None:
        if (not self.txt_firma.text().strip()
                or not self.txt_urun.text().strip()):
            ModernPopUp("EKSİK",
                "Firma ve Ürün alanları zorunludur.",
                "warning", self).exec_()
            return
        a, _ = self.get_active_sensors()
        if len(a) == 0:
            ModernPopUp("HATA",
                "Sistem Ayarları bölümünde en az 1 ahşap sensörü seçmelisiniz!",
                "critical", self).exec_()
            return
        self.accept()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.pos()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e) -> None:
        self._drag_pos = None


# ═══════════════════════════════════════════════════════════
#  SENSOR DATA MODEL
# ═══════════════════════════════════════════════════════════
class SensorData:
    def __init__(self, max_points: int = MAX_GRAPH_POINTS):
        self.temps: deque = deque(maxlen=max_points)
        self.times: deque = deque(maxlen=max_points)
        self.current: float = 0.0
        self.min_val: float = 999.0
        self.max_val: float = 0.0

    def reset(self, initial_temp: float = 20.0) -> None:
        self.temps.clear()
        self.times.clear()
        self.current = initial_temp
        self.min_val = 999.0
        self.max_val = 0.0

    def push(self, time_idx: int, temp: float) -> None:
        self.current = temp
        self.temps.append(temp)
        self.times.append(time_idx)
        if temp < self.min_val:
            self.min_val = temp
        if temp > self.max_val:
            self.max_val = temp


# ═══════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════


class TempColumn(QWidget):
    def __init__(self, min_temp: float = 0.0, max_temp: float = 150.0, parent=None):
        super().__init__(parent)
        self._min = float(min_temp)
        self._max = float(max_temp)
        self._temp = None
        self._setpoint = 60.0
        self._enabled = True
        self.setFixedSize(28, 110)

    def set_temp(self, temp: Optional[float], setpoint: float, enabled: bool = True) -> None:
        self._temp = temp
        self._setpoint = float(setpoint or 0.0)
        self._enabled = bool(enabled)
        self.update()

    def _mix(self, c1: str, c2: str, t: float) -> QColor:
        t = max(0.0, min(1.0, float(t)))
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return QColor(r, g, b)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        outer = self.rect().adjusted(2, 2, -2, -2)
        p.setPen(QPen(QColor(CLR.BORDER), 1))
        p.setBrush(QColor(CLR.CARD))
        p.drawRoundedRect(outer, 7, 7)

        # İç track: daha geniş, düşük sıcaklıkta da doluluk görünür
        track = outer.adjusted(3, 3, -3, -3)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1b2a40"))
        p.drawRoundedRect(track, 5, 5)

        if self._enabled and self._temp is not None:
            span = max(0.0001, self._max - self._min)
            ratio = (float(self._temp) - self._min) / span
            ratio = max(0.0, min(1.0, ratio))

            usable_h = max(1, track.height())
            fill_h = int(round(usable_h * ratio))
            if ratio > 0.0:
                fill_h = max(24, fill_h)
            fill_h = min(fill_h, usable_h)

            if fill_h > 0:
                fill_rect = QRectF(
                    track.left(),
                    track.bottom() - fill_h + 1,
                    track.width(),
                    fill_h,
                )

                goal_ratio = (float(self._temp) / self._setpoint) if self._setpoint else 0.0
                if goal_ratio <= 0.7:
                    fill = QColor(CLR.ORANGE)
                else:
                    fill = self._mix(CLR.ORANGE, CLR.GREEN, (goal_ratio - 0.7) / 0.3)

                p.setBrush(fill)
                p.drawRect(fill_rect)

        if not self._enabled:
            p.setPen(QPen(QColor(CLR.TEXT4), 1, Qt.DashLine))
            p.drawLine(track.left() + 4, track.center().y(), track.right() - 4, track.center().y())


class TempColumnDisplay(QWidget):
    def __init__(self, min_temp: float = 0.0, max_temp: float = 150.0, parent=None):
        super().__init__(parent)
        self._col = TempColumn(min_temp, max_temp)
        self._lbl = QLabel('--.-°C')
        self._lbl.setProperty('class', 'nodeValue')
        self._lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._lbl.setFixedWidth(78)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(self._col, 0, Qt.AlignVCenter)
        lay.addWidget(self._lbl, 0, Qt.AlignVCenter)
        lay.addStretch(1)

    def set_temp(self, temp: Optional[float], setpoint: float, enabled: bool = True) -> None:
        self._col.set_temp(temp, setpoint, enabled)
        if not enabled:
            self._lbl.setText('KAPALI')
            self._lbl.setStyleSheet(f'color:{CLR.TEXT4}; font-size:15px; font-weight:800;')
        elif temp is None:
            self._lbl.setText('--.-°C')
            self._lbl.setStyleSheet(f'color:{CLR.TEXT2}; font-size:18px; font-weight:900;')
        else:
            self._lbl.setText(f'{float(temp):.1f}°C')
            goal_ratio = (float(temp) / float(setpoint)) if setpoint else 0.0
            if goal_ratio <= 0.7:
                color = CLR.TEXT
            else:
                t = max(0.0, min(1.0, (goal_ratio - 0.7) / 0.3))
                c = self._col._mix(CLR.TEXT, CLR.GREEN_L, t)
                color = c.name()
            self._lbl.setStyleSheet(f'color:{color}; font-size:20px; font-weight:900;')


class MainScada(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAODİKYA OTOMASYON — ISPM-15 SCADA v4.0 (Delta PLC)")
        self.setMinimumSize(1600, 950)
        self.setStyleSheet(STYLESHEET)

        # ── Settings ──
        self._settings_mgr = SettingsManager()
        self.ayarlar: Dict = self._settings_mgr.load()

        # ── PLC ──
        self.plc_ip   = "192.168.1.5"  # Delta DVP-12SE
        self.plc_port = 502
        self.plc_client = ModbusTcpClient(
            self.plc_ip, port=self.plc_port, timeout=0.5)
        self.plc_bagli_mi: bool = False
        # D100=Ahşap1, D101=Ahşap2, D102=Ortam1, D103=Ortam2
        self.son_okunan_sicakliklar: List[float] = [0.0, 0.0, 0.0, 0.0]

        # ── Process state ──
        self.is_running: bool = False
        self.current_firma: str = ""
        self.current_urun: str = ""
        self.current_adet: int = 0
        self.current_m3: float = 0.0
        self.current_set: float = 56.0
        self.active_ahsap: List[int] = []
        self.active_ortam: List[int] = []
        self.baslangic_zamani: str = ""
        self.log_data: List[Dict] = []
        self.process_seconds: int = 0   # Start'tan itibaren toplam
        self.holding_seconds: int = 0   # Sadece hedefte sayan
        self.toplam_gecen_saniye: int = 0
        self.sim_counter: int = 0
        self.kural_ihlali_var: bool = False
        self.set_hedef_goruldu: bool = False
        self.rezistans_aktif: bool = True

        # ── Camera evidence images ──
        self.img_bos_b64: Optional[str] = None
        self.img_dolu_b64: Optional[str] = None
        self.img_son_dolu_b64: Optional[str] = None
        self.img_son_bos_b64: Optional[str] = None

        # ── Anti-cheat ──
        self.sensor_gecmisi: Dict[int, List] = {i: [] for i in range(NUM_TOTAL_SENSORS)}
        self.sensor_eslesme_sayaci: Dict = {}

        # ── Sensor data ──
        self.sensors: List[SensorData] = [
            SensorData() for _ in range(NUM_TOTAL_SENSORS)
        ]

        # ── File paths ──
        desk = os.path.join(os.path.expanduser("~"), "Desktop")
        self.kayit_klasoru = os.path.join(desk, "Isıl işlem kayıtları")
        self.video_klasoru = os.path.join(self.kayit_klasoru, "Videolar")
        os.makedirs(self.video_klasoru, exist_ok=True)

        self._init_ui()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        self._main_timer = QTimer(self)
        self._main_timer.timeout.connect(self._update_process)

    # ═══════════════════════════════════════════════════════
    #  UI SETUP
    # ═══════════════════════════════════════════════════════
    def _init_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        # ── SIDEBAR ──
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        logo = QLabel("LAODİKYA\nOTOMASYON")
        logo.setObjectName("SidebarLogo")
        logo.setAlignment(Qt.AlignCenter)
        sb.addWidget(logo)
        sb.addSpacing(15)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("📊  Kontrol Paneli",  0),
            ("📋  Canlı Takip",     1),
            ("📂  Rapor Arşivi",    2),
            ("⚙  Sistem Ayarları", 3),
        ]
        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setProperty("class", "navBtn")
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.clicked.connect(
                lambda checked, i=idx: self.stack.setCurrentIndex(i))
            self.nav_group.addButton(btn, idx)
            sb.addWidget(btn)

        sb.addStretch()

        self.lbl_clock = QLabel("00:00:00")
        self.lbl_clock.setObjectName("SidebarClock")
        self.lbl_clock.setAlignment(Qt.AlignCenter)
        self.lbl_date = QLabel("")
        self.lbl_date.setObjectName("SidebarDate")
        self.lbl_date.setAlignment(Qt.AlignCenter)
        self.lbl_day = QLabel("")
        self.lbl_day.setObjectName("SidebarDay")
        self.lbl_day.setAlignment(Qt.AlignCenter)
        sb.addWidget(self.lbl_clock)
        sb.addWidget(self.lbl_date)
        sb.addWidget(self.lbl_day)
        root.addWidget(sidebar)

        # ── STACKED PAGES ──
        self.stack = QStackedWidget()
        self.page_dashboard = QWidget()
        self.page_tracking  = QWidget()
        self.page_archive   = QWidget()
        self.page_settings  = QWidget()

        self._build_dashboard()
        self._build_tracking()
        self._build_archive()
        self._build_settings()

        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_tracking)
        self.stack.addWidget(self.page_archive)
        self.stack.addWidget(self.page_settings)
        root.addWidget(self.stack)

    # ═══════════════════════════════════════════════════════
    #  PAGE 1: DASHBOARD
    # ═══════════════════════════════════════════════════════
    def _build_dashboard(self) -> None:
        layout = QVBoxLayout(self.page_dashboard)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(18)

        # ── Header ──
        header = QFrame()
        header.setObjectName("HeaderFrame")
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(20); sh.setColor(QColor(0, 0, 0, 100)); sh.setOffset(0, 5)
        header.setGraphicsEffect(sh)

        h_outer = QVBoxLayout(header)
        h_outer.setContentsMargins(0, 0, 0, 0)
        h_outer.setSpacing(0)

        h_row = QHBoxLayout()
        h_row.setContentsMargins(25, 18, 25, 18)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)
        title_col.addWidget(QLabel(
            "ISPM-15 KONTROL ÜNİTESİ",
            styleSheet=("color:white; font-size:24px; "
                        "font-weight:900; letter-spacing:1px;")))

        self.lbl_status = QLabel("●  DURUM: BEKLEMEDE")
        self.lbl_status.setObjectName("statusBadge")
        self.lbl_status.setProperty("status", "idle")
        self.lbl_status.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        title_col.addWidget(self.lbl_status)
        h_row.addLayout(title_col)
        h_row.addStretch()

        self.lbl_firma_hdr = QLabel("")
        self.lbl_firma_hdr.setStyleSheet(f"color:{CLR.TEXT2}; font-size:13px;")
        self.lbl_urun_hdr = QLabel("")
        self.lbl_urun_hdr.setStyleSheet(f"color:{CLR.TEXT2}; font-size:13px;")
        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        info_col.addWidget(self.lbl_firma_hdr)
        info_col.addWidget(self.lbl_urun_hdr)
        h_row.addLayout(info_col)
        h_row.addSpacing(30)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        self.btn_start = QPushButton("▶  İŞLEMİ BAŞLAT")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setProperty("class", "actionBtn")
        self.btn_start.setMinimumSize(170, 52)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_process)

        self.btn_stop = QPushButton("■  ACİL DURDUR")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setProperty("class", "actionBtn")
        self.btn_stop.setMinimumSize(170, 52)
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_process)

        btn_box.addWidget(self.btn_start)
        btn_box.addWidget(self.btn_stop)
        h_row.addLayout(btn_box)
        h_outer.addLayout(h_row)

        self.header_line = QFrame()
        self.header_line.setObjectName("HeaderLine")
        self.header_line.setFixedHeight(4)
        self.header_line.setStyleSheet(f"background:{CLR.TEXT2};")
        h_outer.addWidget(self.header_line)
        layout.addWidget(header)

        # ── Main Grid ──
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)

        # ─ LEFT: Kiln + Sensors ─
        left_card = QFrame()
        left_card.setProperty("class", "card")
        lc = QVBoxLayout(left_card)
        lc.setContentsMargins(18, 18, 18, 18)
        lc.setSpacing(15)

        lc.addWidget(QLabel("🔥  FIRIN SİMÜLASYONU",
            styleSheet=(f"color:{CLR.ACCENT}; font-weight:bold; font-size:14px;")))
        self.kiln = SmoothKilnWidget()
        lc.addWidget(self.kiln)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background:{CLR.BORDER};")
        lc.addWidget(sep)

        lc.addWidget(QLabel(
            "🌡  CANLI SENSÖR VERİLERİ  (12 Ahşap + 4 Ortam)",
            styleSheet=(f"color:{CLR.ACCENT}; font-weight:bold; font-size:14px;")))

        sensor_grid = QGridLayout()
        sensor_grid.setHorizontalSpacing(12)
        sensor_grid.setVerticalSpacing(12)

        self.sensor_widgets: List[Dict] = []

        colors_a = [
            "#f87171", "#fb923c", "#fbbf24", "#a3e635",
            "#34d399", "#22d3ee", "#818cf8", "#c084fc",
            "#f472b6", "#94a3b8", "#fca5a5", "#fdba74",
        ]
        colors_o = [CLR.CYAN, "#7dd3fc", "#38bdf8", "#0ea5e9"]

        for i in range(NUM_AHSAP_SENSORS):
            card, val_lbl, mm_lbl = self._make_sensor_card(
                f"AHŞAP {i + 1}", colors_a[i], "🌲", "ahsap")
            r, c = divmod(i, 6)
            sensor_grid.addWidget(card, r, c)
            self.sensor_widgets.append({
                'card': card, 'val': val_lbl, 'mm': mm_lbl,
                'type': 'ahsap', 'id': i, 'idx': i,
                'color': colors_a[i],
            })

        for i in range(NUM_ORTAM_SENSORS):
            card, val_lbl, mm_lbl = self._make_sensor_card(
                f"ORTAM {i + 1}", colors_o[i], "🌡", "ortam")
            sensor_grid.addWidget(card, 2, i + 1)
            self.sensor_widgets.append({
                'card': card, 'val': val_lbl, 'mm': mm_lbl,
                'type': 'ortam', 'id': i, 'idx': NUM_AHSAP_SENSORS + i,
                'color': colors_o[i],
            })

        lc.addLayout(sensor_grid)
        grid.addWidget(left_card, 0, 0, 3, 1)

        # ─ RIGHT: Graph ─
        graph_card = QFrame()
        graph_card.setProperty("class", "card")
        gc = QVBoxLayout(graph_card)
        gc.setContentsMargins(12, 12, 12, 12)
        gc.addWidget(QLabel("📈  TREND ANALİZİ",
            styleSheet=(f"color:{CLR.ACCENT}; font-weight:bold; font-size:14px;")))

        pg.setConfigOption('background', CLR.CARD)
        pg.setConfigOption('foreground', CLR.TEXT2)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.08)
        self.plot_widget.setYRange(10, 90)
        self.plot_widget.getAxis('left').setLabel('°C', color=CLR.TEXT2)

        self.target_line = pg.InfiniteLine(
            pos=56, angle=0,
            pen=pg.mkPen(CLR.RED, width=2, style=Qt.DashLine),
            label='HEDEF',
            labelOpts={'color': CLR.RED, 'position': 0.95},
        )
        self.plot_widget.addItem(self.target_line)

        self.curves: List[pg.PlotDataItem] = []
        for sw in self.sensor_widgets:
            pen = pg.mkPen(color=sw['color'], width=2)
            curve = self.plot_widget.plot([], [], pen=pen)
            self.curves.append(curve)
            sw['curve'] = curve

        gc.addWidget(self.plot_widget)
        grid.addWidget(graph_card, 0, 1)

        # ─ RIGHT: Timer + Fan ─
        info_card = QFrame()
        info_card.setProperty("class", "card")
        ic = QVBoxLayout(info_card)
        ic.setContentsMargins(0, 0, 0, 0)
        ic.setSpacing(0)

        timer_w = QWidget()
        tw = QHBoxLayout(timer_w)
        tw.setContentsMargins(20, 18, 20, 18)

        col_e = QVBoxLayout()
        col_e.addWidget(QLabel("GEÇEN SÜRE", alignment=Qt.AlignCenter,
            styleSheet=(f"color:{CLR.TEXT2}; font-size:11px; font-weight:bold;")))
        self.lbl_elapsed = QLabel("00:00:00")
        self.lbl_elapsed.setAlignment(Qt.AlignCenter)
        self.lbl_elapsed.setStyleSheet(
            f"color:{CLR.GREEN}; font-size:42px; font-weight:bold; "
            f"font-family:'Consolas';")
        col_e.addWidget(self.lbl_elapsed)

        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.VLine)
        sep_v.setStyleSheet(f"background:{CLR.BORDER};")

        col_r = QVBoxLayout()
        col_r.addWidget(QLabel("KALAN SÜRE", alignment=Qt.AlignCenter,
            styleSheet=(f"color:{CLR.TEXT2}; font-size:11px; font-weight:bold;")))
        self.lbl_remain = QLabel("--:--:--")
        self.lbl_remain.setAlignment(Qt.AlignCenter)
        self.lbl_remain.setStyleSheet(
            f"color:{CLR.ORANGE}; font-size:34px; font-weight:bold; "
            f"font-family:'Consolas';")
        col_r.addWidget(self.lbl_remain)

        tw.addLayout(col_e)
        tw.addWidget(sep_v)
        tw.addLayout(col_r)
        ic.addWidget(timer_w)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        pw = QWidget()
        pwl = QHBoxLayout(pw)
        pwl.setContentsMargins(20, 0, 20, 10)
        pwl.addWidget(self.progress)
        ic.addWidget(pw)

        fan_strip = QFrame()
        fan_strip.setStyleSheet(f"""
            background:{CLR.BG};
            border-top:1px solid {CLR.BORDER};
            border-bottom-left-radius:12px;
            border-bottom-right-radius:12px;
        """)
        fs = QHBoxLayout(fan_strip)
        fs.setContentsMargins(20, 12, 20, 12)
        fs.addWidget(QLabel("🌀", styleSheet="font-size:22px;"))
        self.lbl_fan = QLabel("FAN: BEKLEMEDE")
        self.lbl_fan.setStyleSheet(
            f"color:{CLR.TEXT3}; font-size:14px; font-weight:bold;")
        fs.addWidget(self.lbl_fan)
        fs.addStretch()
        ic.addWidget(fan_strip)
        grid.addWidget(info_card, 1, 1)

        # ─ RIGHT: Log ─
        log_card = QFrame()
        log_card.setProperty("class", "card")
        lgl = QVBoxLayout(log_card)
        lgl.setContentsMargins(12, 12, 12, 12)
        lgl.addWidget(QLabel("📋  SİSTEM GÜNLÜĞÜ",
            styleSheet=(f"color:{CLR.ACCENT}; font-weight:bold; font-size:14px;")))
        self.list_logs = QListWidget()
        self._log("Sistem başlatıldı. PLC bağlantısı bekleniyor...")
        lgl.addWidget(self.list_logs)
        grid.addWidget(log_card, 2, 1)

        grid.setColumnStretch(0, 60)
        grid.setColumnStretch(1, 40)
        grid.setRowStretch(0, 40)
        grid.setRowStretch(1, 28)
        grid.setRowStretch(2, 32)
        layout.addLayout(grid)

    def _mix_color(self, c1: str, c2: str, t: float) -> str:
        """Linear blend between two hex colors (e.g. '#ff0000')."""
        t = max(0.0, min(1.0, float(t)))
        def _h2i(h): return int(h, 16)
        r1, g1, b1 = _h2i(c1[1:3]), _h2i(c1[3:5]), _h2i(c1[5:7])
        r2, g2, b2 = _h2i(c2[1:3]), _h2i(c2[3:5]), _h2i(c2[5:7])
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _set_temp_bar(self, bar, temp: Optional[float],
                      setpoint: float, enabled: bool) -> None:
        if hasattr(bar, "set_temp"):
            bar.set_temp(temp, setpoint, enabled)

    def _make_sensor_card(self, name: str, accent: str,
                          icon: str, sensor_type: str = "ortam") -> Tuple[QFrame, QWidget, QLabel]:
        card = QFrame()
        card.setProperty("class", "sensorNode")
        card.setProperty("status", "wait")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(6)

        top = QHBoxLayout()
        top.addWidget(QLabel(icon, styleSheet="font-size:12px;"))
        lbl_name = QLabel(name)
        lbl_name.setProperty("class", "nodeTitle")
        lbl_name.setStyleSheet(f"color:{accent};")
        top.addWidget(lbl_name)
        top.addStretch()
        v.addLayout(top)

        bar_max = 70.0 if sensor_type == "ahsap" else 150.0
        bar = TempColumnDisplay(0.0, bar_max)
        self._set_temp_bar(bar, None, 1.0, True)

        mid = QHBoxLayout()
        mid.addStretch()
        mid.addWidget(bar)
        mid.addStretch()
        v.addLayout(mid)

        lbl_mm = QLabel("")
        lbl_mm.setProperty("class", "nodeMinMax")
        lbl_mm.setAlignment(Qt.AlignCenter)
        lbl_mm.hide()

        return card, bar, lbl_mm

    # ═══════════════════════════════════════════════════════
    #  PAGE 2: CANLI TAKİP
    # ═══════════════════════════════════════════════════════
    def _build_tracking(self) -> None:
        layout = QVBoxLayout(self.page_tracking)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        hdr_row = QHBoxLayout()
        hdr_row.addWidget(QLabel("📋  CANLI PROSES TAKİBİ",
            styleSheet=(f"color:{CLR.ACCENT}; font-size:20px; font-weight:bold;")))
        hdr_row.addStretch()
        self.lbl_track_info = QLabel("Veri akışı bekleniyor...")
        self.lbl_track_info.setStyleSheet(f"color:{CLR.TEXT2}; font-weight:bold;")
        hdr_row.addWidget(self.lbl_track_info)
        layout.addLayout(hdr_row)

        self.table_live = QTableWidget()
        self.table_live.setColumnCount(4)
        self.table_live.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_live.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_live.setSelectionMode(QTableWidget.NoSelection)
        self.table_live.verticalHeader().setVisible(False)
        self.table_live.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.table_live.setAlternatingRowColors(True)
        self.table_live.setStyleSheet(f"""
            QTableWidget {{
                background: {CLR.SIDEBAR};
                alternate-background-color: {CLR.BG};
                color: {CLR.TEXT};
                gridline-color: {CLR.BORDER};
                border: 1px solid {CLR.BORDER};
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background: {CLR.CARD};
                color: {CLR.ACCENT};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {CLR.ACCENT};
            }}
        """)
        layout.addWidget(self.table_live)

    # ═══════════════════════════════════════════════════════
    #  PAGE 3: ARCHIVE
    # ═══════════════════════════════════════════════════════
    def _build_archive(self) -> None:
        layout = QVBoxLayout(self.page_archive)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        layout.addWidget(QLabel("📂  ARŞİV VE RAPORLAR",
            styleSheet=(f"color:{CLR.ACCENT}; font-size:20px; font-weight:bold;")))

        flt = QFrame()
        flt.setProperty("class", "card")
        fl2 = QHBoxLayout(flt)
        fl2.setContentsMargins(15, 12, 15, 12)
        fl2.setSpacing(10)
        ls = f"color:{CLR.TEXT2}; font-size:12px; font-weight:bold;"

        fl2.addWidget(QLabel("🔍", styleSheet="font-size:16px;"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Ürün adı ile ara...")
        self.txt_search.setMinimumWidth(180)
        fl2.addWidget(QLabel("ÜRÜN:", styleSheet=ls))
        fl2.addWidget(self.txt_search)

        self.date_from = QDateEdit(calendarPopup=True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to = QDateEdit(calendarPopup=True)
        self.date_to.setDate(QDate.currentDate())
        fl2.addWidget(QLabel("TARİH:", styleSheet=ls))
        fl2.addWidget(self.date_from)
        fl2.addWidget(QLabel("→", styleSheet=ls))
        fl2.addWidget(self.date_to)

        btn_f = QPushButton("FİLTRELE")
        btn_f.setProperty("class", "orangeBtn")
        btn_f.setCursor(Qt.PointingHandCursor)
        btn_f.clicked.connect(self._load_archive)
        fl2.addWidget(btn_f)

        btn_r = QPushButton("TÜMÜNÜ GÖSTER")
        btn_r.setProperty("class", "flatBtn")
        btn_r.setCursor(Qt.PointingHandCursor)
        btn_r.clicked.connect(self._reset_archive_filter)
        fl2.addWidget(btn_r)
        fl2.addStretch()
        layout.addWidget(flt)

        self.table_archive = QTableWidget()
        self.table_archive.setColumnCount(5)
        self.table_archive.setHorizontalHeaderLabels(
            ["Dosya", "Firma", "Ürün", "Tarih", "Durum"])
        self.table_archive.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.table_archive.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_archive.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_archive.setAlternatingRowColors(True)
        layout.addWidget(self.table_archive)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_pdf = QPushButton("🖨  PDF RAPORU YAZDIR")
        btn_pdf.setProperty("class", "accentBtn")
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.setFixedHeight(48)
        btn_pdf.clicked.connect(self._print_archive_pdf)
        btn_row.addWidget(btn_pdf)

        # CSV dışa aktarma kapatıldı

        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ═══════════════════════════════════════════════════════
    #  PAGE 4: SETTINGS
    # ═══════════════════════════════════════════════════════
    def _build_settings(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border:none; background:{CLR.BG}; }}")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(18)

        layout.addWidget(QLabel("⚙  SİSTEM ÇALIŞMA PARAMETRELERİ",
            styleSheet=(f"color:{CLR.ACCENT}; font-size:20px; font-weight:bold;")))
        layout.addWidget(QLabel(
            "Bu parametreler PLC kontrol mantığını ve işlem sürecini belirler.",
            styleSheet=f"color:{CLR.TEXT3}; font-size:12px;"))

        ls = f"color:{CLR.TEXT2}; font-size:12px; font-weight:bold;"

        g1 = QGroupBox("🔥  ISITMA ve SÜRE")
        g1l = QFormLayout(g1)
        g1l.setSpacing(12)
        g1l.setContentsMargins(15, 25, 15, 15)

        self.ay_alt = PlusMinusDoubleSpinBox()
        self.ay_alt.setRange(30, 150)
        self.ay_alt.setValue(self.ayarlar['alt_limit'])
        self.ay_alt.setSuffix(" °C")
        self.ay_ust = PlusMinusDoubleSpinBox()
        self.ay_ust.setRange(30, 150)
        self.ay_ust.setValue(self.ayarlar['ust_limit'])
        self.ay_ust.setSuffix(" °C")
        self.ay_sure = PlusMinusSpinBox()
        self.ay_sure.setRange(1, 999)
        self.ay_sure.setValue(self.ayarlar['islem_suresi_dk'])
        self.ay_sure.setSuffix("  dk")

        g1l.addRow(QLabel("Alt Set Limiti:", styleSheet=ls), self.ay_alt)
        g1l.addRow(QLabel("Üst Set Limiti:", styleSheet=ls), self.ay_ust)
        g1l.addRow(QLabel("Kesintisiz İşlem Süresi:",
                          styleSheet=ls), self.ay_sure)
        layout.addWidget(g1)

        g2 = QGroupBox("🌀  FAN KONTROL")
        g2l = QVBoxLayout(g2)
        g2l.setContentsMargins(15, 25, 15, 15)
        g2l.setSpacing(10)

        mr = QHBoxLayout()
        self.rb_tek = QRadioButton("Tek Yönlü Sürekli")
        self.rb_cift = QRadioButton("Çift Yönlü Değişken")
        bg = QButtonGroup(self)
        bg.addButton(self.rb_tek)
        bg.addButton(self.rb_cift)
        if self.ayarlar['fan_modu'] == 'tek':
            self.rb_tek.setChecked(True)
        else:
            self.rb_cift.setChecked(True)
        mr.addWidget(self.rb_tek)
        mr.addWidget(self.rb_cift)
        mr.addStretch()
        g2l.addLayout(mr)

        ff = QFormLayout()
        ff.setSpacing(10)
        self.ay_sag = PlusMinusSpinBox()
        self.ay_sag.setRange(1, 100)
        self.ay_sag.setValue(self.ayarlar['fan_sag_dk'])
        self.ay_sag.setSuffix("  dk")
        self.ay_sol = PlusMinusSpinBox()
        self.ay_sol.setRange(1, 100)
        self.ay_sol.setValue(self.ayarlar['fan_sol_dk'])
        self.ay_sol.setSuffix("  dk")
        self.ay_bekle = PlusMinusSpinBox()
        self.ay_bekle.setRange(1, 60)
        self.ay_bekle.setValue(self.ayarlar['fan_bekleme_dk'])
        self.ay_bekle.setSuffix("  dk")
        ff.addRow(QLabel("Sağ Dönüş:", styleSheet=ls), self.ay_sag)
        ff.addRow(QLabel("Sol Dönüş:", styleSheet=ls), self.ay_sol)
        ff.addRow(QLabel("Geçiş Bekleme:", styleSheet=ls), self.ay_bekle)
        g2l.addLayout(ff)

        self.rb_tek.toggled.connect(self._toggle_fan_ui)
        self.rb_cift.toggled.connect(self._toggle_fan_ui)
        self._toggle_fan_ui()
        layout.addWidget(g2)

        g3 = QGroupBox("📡  AKTİF SENSÖRLER")
        g3l = QGridLayout(g3)
        g3l.setSpacing(8)
        g3l.setContentsMargins(15, 25, 15, 15)

        g3l.addWidget(QLabel("🌲 AHŞAP", styleSheet=f"color:{CLR.ORANGE}; font-size:11px; font-weight:bold;"), 0, 0, 1, 4)
        self.ay_chk_ahsap: List[QCheckBox] = []
        aktif_a = set(self.ayarlar.get('active_ahsap', [0, 1]))
        for i in range(NUM_AHSAP_SENSORS):
            cb = QCheckBox(f"A{i + 1}")
            cb.setChecked(i in aktif_a)
            self.ay_chk_ahsap.append(cb)
            g3l.addWidget(cb, 1 + i // 4, i % 4)

        ortam_row = 1 + math.ceil(NUM_AHSAP_SENSORS / 4)
        g3l.addWidget(QLabel("🌡 ORTAM", styleSheet=f"color:{CLR.PURPLE}; font-size:11px; font-weight:bold;"), ortam_row, 0, 1, 4)
        self.ay_chk_ortam: List[QCheckBox] = []
        aktif_o = set(self.ayarlar.get('active_ortam', [0, 1]))
        for i in range(NUM_ORTAM_SENSORS):
            cb = QCheckBox(f"O{i + 1}")
            cb.setChecked(i in aktif_o)
            self.ay_chk_ortam.append(cb)
            g3l.addWidget(cb, ortam_row + 1, i)

        layout.addWidget(g3)

        btn_save = QPushButton("💾  SİSTEM AYARLARINI KAYDET")
        btn_save.setProperty("class", "greenBtn")
        btn_save.setFixedHeight(52)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save_settings)
        layout.addWidget(btn_save)
        layout.addStretch()

        pg_layout = QVBoxLayout(self.page_settings)
        pg_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        pg_layout.addWidget(scroll)

    def _toggle_fan_ui(self) -> None:
        en = self.rb_cift.isChecked()
        self.ay_sag.setEnabled(en)
        self.ay_sol.setEnabled(en)
        self.ay_bekle.setEnabled(en)

    def _save_settings(self) -> None:
        if self.ay_alt.value() >= self.ay_ust.value():
            ModernPopUp("HATA",
                "Alt limit, üst limitten küçük olmalıdır.",
                "critical", self).exec_()
            return

        aktif_a = [i for i, c in enumerate(self.ay_chk_ahsap) if c.isChecked()]
        aktif_o = [i for i, c in enumerate(self.ay_chk_ortam) if c.isChecked()]
        if len(aktif_a) == 0:
            ModernPopUp("HATA",
                "En az 1 ahşap sensörü seçmelisiniz.",
                "critical", self).exec_()
            return

        self.ayarlar['alt_limit']       = self.ay_alt.value()
        self.ayarlar['ust_limit']       = self.ay_ust.value()
        self.ayarlar['islem_suresi_dk'] = self.ay_sure.value()
        self.ayarlar['fan_modu']        = 'tek' if self.rb_tek.isChecked() else 'cift'
        self.ayarlar['fan_sag_dk']      = self.ay_sag.value()
        self.ayarlar['fan_sol_dk']      = self.ay_sol.value()
        self.ayarlar['fan_bekleme_dk']  = self.ay_bekle.value()
        self.ayarlar['active_ahsap']    = aktif_a
        self.ayarlar['active_ortam']    = aktif_o
        try:
            self._settings_mgr.save(self.ayarlar)
            self._log("Sistem ayarları güncellendi ve diske kaydedildi.", "ok")
            ModernPopUp("BAŞARILI", "Ayarlar başarıyla kaydedildi.",
                        "success", self).exec_()
        except IOError as e:
            self._log(f"Ayar kayıt hatası: {e}", "error")
            ModernPopUp("HATA", f"Ayarlar diske yazılamadı:\n{e}",
                        "critical", self).exec_()

    # ═══════════════════════════════════════════════════════
    #  ARCHIVE METHODS
    # ═══════════════════════════════════════════════════════
    def _load_archive(self) -> None:
        self.table_archive.setRowCount(0)
        if not os.path.exists(self.kayit_klasoru):
            return

        search = self.txt_search.text().strip().lower()
        d1 = self.date_from.date().toPyDate()
        d2 = self.date_to.date().toPyDate()

        for root_dir, dirs, files in os.walk(self.kayit_klasoru):
            for f in files:
                if not f.endswith('.ldk'):
                    continue
                path = os.path.join(root_dir, f)
                try:
                    with open(path, "rb") as fh:
                        raw = fh.read()
                    v = json.loads(zlib.decompress(raw).decode('utf-8'))
                    urun = v.get('urun', '').lower()
                    ts   = v.get('tarih', '')
                    try:
                        td = datetime.strptime(ts, '%d.%m.%Y %H:%M:%S').date()
                    except ValueError:
                        td = None
                    if search and search not in urun:
                        continue
                    if td and not (d1 <= td <= d2):
                        continue
                    row = self.table_archive.rowCount()
                    self.table_archive.insertRow(row)
                    item = QTableWidgetItem(f)
                    item.setData(Qt.UserRole, path)
                    self.table_archive.setItem(row, 0, item)
                    self.table_archive.setItem(row, 1, QTableWidgetItem(v.get('firma', '-')))
                    self.table_archive.setItem(row, 2, QTableWidgetItem(v.get('urun', '-')))
                    self.table_archive.setItem(row, 3, QTableWidgetItem(ts))
                    self.table_archive.setItem(row, 4, QTableWidgetItem("✓ Tamamlandı"))
                except Exception:
                    pass

    def _reset_archive_filter(self) -> None:
        self.txt_search.clear()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self._load_archive()

    def _print_archive_pdf(self) -> None:
        r = self.table_archive.currentRow()
        if r < 0:
            ModernPopUp("UYARI", "Lütfen tablodan bir kayıt seçin.",
                        "warning", self).exec_()
            return
        path = self.table_archive.item(r, 0).data(Qt.UserRole)
        if path:
            self._generate_pdf(path)

    def _export_csv(self) -> None:
        r = self.table_archive.currentRow()
        if r < 0:
            ModernPopUp("UYARI", "Tablodan bir kayıt seçin.",
                        "warning", self).exec_()
            return
        path = self.table_archive.item(r, 0).data(Qt.UserRole)
        try:
            with open(path, "rb") as f:
                v = json.loads(zlib.decompress(f.read()).decode('utf-8'))
            log_entries: List[Dict] = v.get('log_data', [])
            if not log_entries:
                ModernPopUp("BİLGİ", "Bu kayıtta veri yok.", "info", self).exec_()
                return
            save_path, _ = QFileDialog.getSaveFileName(
                self, "CSV Kaydet", "", "CSV Dosyaları (*.csv)")
            if not save_path:
                return
            fieldnames = list(log_entries[0].keys())
            with open(save_path, 'w', newline='', encoding='utf-8') as cf:
                writer = csv.DictWriter(cf, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(log_entries)
            ModernPopUp("BAŞARILI",
                f"CSV başarıyla kaydedildi:\n{save_path}",
                "success", self).exec_()
        except Exception as e:
            ModernPopUp("HATA", str(e), "critical", self).exec_()

    # ═══════════════════════════════════════════════════════
    #  PDF GENERATION  (from ıspm_son_versiyon.py)
    # ═══════════════════════════════════════════════════════
    def _get_pdf_header(self, veri: Dict, i_style) -> Table:
        header_data = [
            [Paragraph(f"<b>Firma:</b> {veri.get('firma', '-')}", i_style),
             Paragraph(f"<b>Ürün:</b> {veri.get('urun', '-')}", i_style)],
            [Paragraph(f"<b>Adet:</b> {veri.get('adet', '-')}", i_style),
             Paragraph(f"<b>Hacim:</b> {veri.get('m3', '-') } m³", i_style)],
            [Paragraph(f"<b>Parti No:</b> {veri.get('parti', '-')}", i_style),
             Paragraph(f"<b>Rapor Tarihi:</b> {veri.get('tarih', '-')}", i_style)],
            [Paragraph(f"<b>Başlangıç:</b> {veri.get('baslangic_zamani', '-')}", i_style),
             Paragraph(f"<b>Bitiş:</b> {veri.get('bitis_zamani', '-')}", i_style)],
        ]
        tbl = Table(header_data, colWidths=[4 * inch, 4 * inch])
        tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return tbl

    def _generate_pdf(self, dosya_yolu: str) -> None:
        try:
            with open(dosya_yolu, "rb") as f:
                raw = f.read()
            veri = json.loads(zlib.decompress(raw).decode('utf-8'))

            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_pdf = os.path.join(
                temp_dir, f"LDK_TEMP_{random.randint(1000, 9999)}.pdf")
            grafik_gecici = os.path.join(temp_dir, 'temp_graph.png')

            if veri.get('grafik_b64'):
                with open(grafik_gecici, "wb") as fh:
                    fh.write(base64.b64decode(veri["grafik_b64"]))

            try:
                pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
                f_norm, f_bold = 'Arial', 'Arial-Bold'
            except Exception:
                f_norm, f_bold = 'Helvetica', 'Helvetica-Bold'

            koruma = StandardEncryption(
                userPassword="", ownerPassword="LDK_GIZLI",
                canPrint=1, canModify=0, canCopy=0)
            doc = SimpleDocTemplate(
                temp_pdf, pagesize=landscape(A4), encrypt=koruma,
                rightMargin=20, leftMargin=20,
                topMargin=15, bottomMargin=15)
            elements = []
            styles   = getSampleStyleSheet()
            t_style  = ParagraphStyle('T', fontName=f_bold, fontSize=16,
                                      textColor=rl_colors.darkblue,
                                      alignment=1)
            i_style  = ParagraphStyle('I', fontName=f_norm, fontSize=10,
                                      spaceAfter=2)

            elements.append(Paragraph(
                "LAODİKYA OTOMASYON — ISPM-15 ISIL İŞLEM RAPORU", t_style))
            elements.append(Spacer(1, 5))
            elements.append(self._get_pdf_header(veri, i_style))
            elements.append(Spacer(1, 5))
            elements.append(Paragraph(
                "<i>* Aşağıdaki veriler ısıl işlem sürecine aittir.</i>",
                i_style))
            elements.append(Spacer(1, 5))

            aa = veri.get('active_ahsap', [])
            ao = veri.get('active_ortam', [])
            header_row = ["Zaman"] + \
                         [f"A.{i + 1}" for i in aa] + \
                         [f"O.{i + 1}" for i in ao]
            table_data = [header_row]
            for log in veri.get('log_data', []):
                row = ([log['zaman']]
                       + [f"{log.get(f'a_{i}', 0):.2f}" for i in aa]
                       + [f"{log.get(f'o_{i}', 0):.2f}" for i in ao])
                table_data.append(row)

            col_w = 700.0 / len(header_row) if header_row else 50
            t = Table(table_data, colWidths=[col_w] * len(header_row))
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, rl_colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            elements.append(t)

            elements.append(PageBreak())
            elements.append(Paragraph(
                "SİSTEM KAMERA KAYITLARI VE SÜREÇ GRAFİĞİ", t_style))
            elements.append(Spacer(1, 5))
            elements.append(self._get_pdf_header(veri, i_style))
            elements.append(Spacer(1, 5))

            cam_rows = []
            row1 = []
            if veri.get('img_bos_b64'):
                p = os.path.join(temp_dir, 'bos_temp.jpg')
                with open(p, "wb") as fh:
                    fh.write(base64.b64decode(veri["img_bos_b64"]))
                row1.append([RLImage(p, width=2.8*inch, height=2.0*inch),
                              Paragraph("<b>1. BAŞLANGIÇ: BOŞ FIRIN</b>", i_style)])
            if veri.get('img_dolu_b64'):
                p = os.path.join(temp_dir, 'dolu_temp.jpg')
                with open(p, "wb") as fh:
                    fh.write(base64.b64decode(veri["img_dolu_b64"]))
                row1.append([RLImage(p, width=2.8*inch, height=2.0*inch),
                              Paragraph("<b>2. BAŞLANGIÇ: DOLU FIRIN</b>", i_style)])
            if row1:
                cam_rows.append(row1)

            row2 = []
            if veri.get('img_son_dolu_b64'):
                p = os.path.join(temp_dir, 'son_dolu_temp.jpg')
                with open(p, "wb") as fh:
                    fh.write(base64.b64decode(veri["img_son_dolu_b64"]))
                row2.append([RLImage(p, width=2.8*inch, height=2.0*inch),
                              Paragraph("<b>3. BİTİŞ: DOLU FIRIN</b>", i_style)])
            if veri.get('img_son_bos_b64'):
                p = os.path.join(temp_dir, 'son_bos_temp.jpg')
                with open(p, "wb") as fh:
                    fh.write(base64.b64decode(veri["img_son_bos_b64"]))
                row2.append([RLImage(p, width=2.8*inch, height=2.0*inch),
                              Paragraph("<b>4. BİTİŞ: BOŞ FIRIN</b>", i_style)])
            if row2:
                cam_rows.append(row2)

            if cam_rows:
                img_table = Table(cam_rows, colWidths=[3.2*inch, 3.2*inch])
                img_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                elements.append(img_table)
                elements.append(Spacer(1, 5))
                if os.path.exists(grafik_gecici):
                    elements.append(
                        RLImage(grafik_gecici, width=6.0*inch, height=1.7*inch))

            doc.build(elements)
            os.startfile(temp_pdf)
            if os.path.exists(grafik_gecici):
                os.remove(grafik_gecici)

        except Exception as e:
            self._log(f"PDF Rapor Hatası: {e}", "error")
            ModernPopUp("HATA", f"PDF oluşturulamadı:\n{e}", "critical", self).exec_()

    # ═══════════════════════════════════════════════════════
    #  HELPER METHODS
    # ═══════════════════════════════════════════════════════
    def _log(self, msg: str, level: str = "info") -> None:
        t  = datetime.now().strftime("%H:%M:%S")
        icons  = {"info": "ℹ", "warn": "⚠", "error": "✕", "ok": "✓"}
        colors_map = {
            "info": CLR.TEXT2, "warn": CLR.ORANGE,
            "error": CLR.RED, "ok": CLR.GREEN,
        }
        ic = icons.get(level, "ℹ")
        cl = colors_map.get(level, CLR.TEXT2)
        item = QListWidgetItem(f"  {ic}  [{t}]  {msg}")
        item.setForeground(QColor(cl))
        self.list_logs.insertItem(0, item)
        while self.list_logs.count() > 500:
            self.list_logs.takeItem(self.list_logs.count() - 1)

    def _update_clock(self) -> None:
        now = datetime.now()
        self.lbl_clock.setText(now.strftime("%H:%M:%S"))
        day_name   = TURKISH_DAYS.get(now.weekday(), "")
        month_name = TURKISH_MONTHS.get(now.month, "")
        self.lbl_date.setText(f"{now.day} {month_name} {now.year}")
        self.lbl_day.setText(day_name)

    def _set_status(self, text: str, status: str) -> None:
        self.lbl_status.setText(text)
        self.lbl_status.setProperty("status", status)
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

    @staticmethod
    def _format_time(secs: int) -> str:
        h, r = divmod(secs, 3600)
        m, s = divmod(r, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _is_sensor_active(self, sw: Dict) -> bool:
        if sw['type'] == 'ahsap':
            return sw['id'] in self.active_ahsap
        return sw['id'] in self.active_ortam

    def _refresh_sensor_style(self, sw: Dict) -> None:
        sw['card'].style().unpolish(sw['card'])
        sw['card'].style().polish(sw['card'])

    def _temp_video_temizle(self) -> None:
        for fn in ["TEMP_BOS.mp4", "TEMP_DOLU.mp4",
                   "TEMP_SON_DOLU.mp4", "TEMP_SON_BOS.mp4"]:
            p = os.path.join(self.video_klasoru, fn)
            if os.path.exists(p):
                os.remove(p)

    def plc_stop_all(self) -> None:
        """Isıtıcı ve fan çıkışlarını güvenlice kapatır."""
        try:
            if not self.plc_client.is_socket_open():
                self.plc_client.connect()
            if self.plc_client.is_socket_open():
                self.plc_client.write_coil(address=1280, value=False, device_id=1)
                self.plc_client.write_coil(address=1281, value=False, device_id=1)
                self.plc_client.write_coil(address=1282, value=False, device_id=1)
        except Exception as e:
            print("PLC Stop Hatası:", e)

    def islem_basarisiz_oldu(self, hata_mesaji: str) -> None:
        self.is_running = False
        self.kural_ihlali_var = True
        self._main_timer.stop()
        self.plc_stop_all()
        self.kiln.stop()
        self._do_stop_ui()
        self._temp_video_temizle()
        self._log(f"KURAL İHLALİ: {hata_mesaji}", "error")
        ModernPopUp(
            "SİSTEM OTOMATİK DURDURULDU",
            f"DENETİM KURALI İHLALİ:\n\n{hata_mesaji}\n\n"
            "İşlem iptal edildi. Geçici kanıt videoları silindi.",
            "critical", self).exec_()

    def _do_stop_ui(self) -> None:
        self.rezistans_aktif = False
        self._set_status("●  DURDURULDU", "stopped")
        self.header_line.setStyleSheet(f"background:{CLR.RED};")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_fan.setText("FAN: PASİF")
        self.lbl_fan.setStyleSheet(
            f"color:{CLR.TEXT3}; font-size:14px; font-weight:bold;")
        for sw in self.sensor_widgets:
            if sw['card'].property("status") != "off":
                sw['card'].setProperty("status", "stop")
                self._refresh_sensor_style(sw)

    # ═══════════════════════════════════════════════════════
    #  PROCESS CONTROL
    # ═══════════════════════════════════════════════════════
    def start_process(self) -> None:
        if self.is_running:
            return

        # STEP 1: Camera evidence (start)
        cam_dialog = ProcessCameraDialog(
            self.video_klasoru, mode="start", parent=self)
        if cam_dialog.exec_() != QDialog.Accepted:
            self._log("Sistem başlatılması kamera adımında iptal edildi.", "warn")
            self._temp_video_temizle()
            return

        # STEP 2: Process parameters
        dlg = ProcessSettingsDialog(self.ayarlar, self)
        if dlg.exec_() != QDialog.Accepted:
            self._log("Parametre girişi iptal edildi.", "warn")
            self._temp_video_temizle()
            return

        self.current_firma = dlg.txt_firma.text().strip()
        self.current_urun  = dlg.txt_urun.text().strip()
        self.current_adet  = dlg.spin_adet.value()
        self.current_m3    = dlg.spin_m3.value()
        self.current_set   = dlg.spin_sicaklik.value()
        self.active_ahsap, self.active_ortam = dlg.get_active_sensors()

        self.img_bos_b64  = cam_dialog.img_step1_b64
        self.img_dolu_b64 = cam_dialog.img_step2_b64

        # Reset state
        self.is_running          = True
        self.kural_ihlali_var    = False
        self.process_seconds     = 0
        self.holding_seconds     = 0
        self.toplam_gecen_saniye = 0
        self.sim_counter         = 0
        self.set_hedef_goruldu   = False
        self.rezistans_aktif     = True
        self.log_data            = []
        self.sensor_gecmisi      = {i: [] for i in range(NUM_TOTAL_SENSORS)}
        self.sensor_eslesme_sayaci = {}
        self.baslangic_zamani    = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

        for sd in self.sensors:
            sd.reset()

        # Live tracking table
        self.table_live.setRowCount(0)
        headers = ["TARİH / SAAT"]
        for i in self.active_ahsap:
            headers.append(f"Ahşap {i + 1}")
        for i in self.active_ortam:
            headers.append(f"Ortam {i + 1}")
        self.table_live.setColumnCount(len(headers))
        self.table_live.setHorizontalHeaderLabels(headers)

        # Graph / UI reset
        hedef_sn = self.ayarlar['islem_suresi_dk'] * 60
        self.lbl_remain.setText(self._format_time(hedef_sn))
        self.lbl_elapsed.setText("00:00:00")
        self.progress.setValue(0)
        self.target_line.setValue(self.current_set)
        self.lbl_firma_hdr.setText(f"Firma: {self.current_firma}")
        self.lbl_urun_hdr.setText(
            f"Ürün: {self.current_urun}  │  Adet: {self.current_adet}  │  Hacim: {self.current_m3:.2f} m³  │  Set: {self.current_set:.1f}°C")

        self._set_status("●  ISITMA AKTİF", "heating")
        self.header_line.setStyleSheet(f"background:{CLR.ORANGE};")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        for sw in self.sensor_widgets:
            active = self._is_sensor_active(sw)
            if active:
                sw['card'].setProperty("status", "wait")
                self._set_temp_bar(sw['val'], None, self.current_set, True)
                sw['mm'].setText("")
                sw['curve'].setVisible(True)
            else:
                sw['card'].setProperty("status", "off")
                self._set_temp_bar(sw['val'], None, self.current_set, False)
                sw['mm'].setText("")
                sw['curve'].setVisible(False)
            self._refresh_sensor_style(sw)

        # Try PLC connection
        try:
            self.plc_client.connect()
        except Exception:
            pass

        self.kiln.start()
        self._log(
            f"İşlem başlatıldı → {self.current_firma} / "
            f"{self.current_urun} / {self.current_adet} adet / {self.current_m3:.2f} m³ / Hedef: {self.current_set:.1f}°C", "ok")
        self._main_timer.start(PROCESS_TICK_MS)

    def stop_process(self) -> None:
        if not self.is_running:
            return
        dlg = ModernPopUp(
            "ACİL DURDURMA",
            "İşlemi durdurmak istediğinize emin misiniz?\n"
            "Tüm geçici kayıtlar silinecek.",
            "critical", self)
        if dlg.exec_() == QDialog.Accepted:
            self.is_running = False
            self._main_timer.stop()
            self.plc_stop_all()
            self.kiln.stop()
            self._do_stop_ui()
            self._temp_video_temizle()
            self._log("Operatör sistemi manuel olarak durdurdu.", "error")
            ModernPopUp("SİSTEM DURDURULDU",
                "Isıl işlem iptal edildi ve geçici dosyalar silindi.",
                "critical", self).exec_()

    # ═══════════════════════════════════════════════════════
    #  MAIN UPDATE LOOP  (PLC + Security + ISPM-15 logic)
    # ═══════════════════════════════════════════════════════
    def _update_process(self) -> None:
        if not self.is_running or self.kural_ihlali_var:
            return

        self.process_seconds     += 1
        self.toplam_gecen_saniye += 1
        self.sim_counter         += 1
        self.lbl_elapsed.setText(self._format_time(self.process_seconds))

        # ── Fan management ──
        fan_spinning = True
        y1_ileri_fan = False
        y2_geri_fan  = False

        if self.ayarlar['fan_modu'] == 'tek':
            self.lbl_fan.setText("FAN: TEK YÖN ▶")
            self.lbl_fan.setStyleSheet(
                f"color:{CLR.ACCENT}; font-size:14px; font-weight:bold;")
            self.kiln.set_fan_direction(1)
            y1_ileri_fan = True
        else:
            sag = self.ayarlar['fan_sag_dk'] * 60
            bkl = self.ayarlar['fan_bekleme_dk'] * 60
            sol = self.ayarlar['fan_sol_dk'] * 60
            cyc = sag + bkl + sol + bkl
            if cyc > 0:
                t_cyc = self.toplam_gecen_saniye % cyc
                if t_cyc < sag:
                    self.lbl_fan.setText("FAN: SAĞ YÖN ▶")
                    self.lbl_fan.setStyleSheet(
                        f"color:{CLR.GREEN}; font-size:14px; font-weight:bold;")
                    self.kiln.set_fan_direction(1)
                    y1_ileri_fan = True
                elif t_cyc < sag + bkl:
                    self.lbl_fan.setText("FAN: BEKLİYOR ⏸")
                    self.lbl_fan.setStyleSheet(
                        f"color:{CLR.ORANGE}; font-size:14px; font-weight:bold;")
                    fan_spinning = False
                elif t_cyc < sag + bkl + sol:
                    self.lbl_fan.setText("FAN: SOL YÖN ◀")
                    self.lbl_fan.setStyleSheet(
                        f"color:{CLR.CYAN}; font-size:14px; font-weight:bold;")
                    self.kiln.set_fan_direction(-1)
                    y2_geri_fan = True
                else:
                    self.lbl_fan.setText("FAN: BEKLİYOR ⏸")
                    self.lbl_fan.setStyleSheet(
                        f"color:{CLR.ORANGE}; font-size:14px; font-weight:bold;")
                    fan_spinning = False

        self.kiln.set_fan_spinning(fan_spinning)

        # ── PLC sensor reading (D100–D103 via Modbus) ──
        try:
            if not self.plc_client.is_socket_open():
                self.plc_client.connect()
            result = self.plc_client.read_holding_registers(
                address=4196, count=4, device_id=1)
            if not result.isError():
                self.plc_bagli_mi = True
                self.son_okunan_sicakliklar = [
                    val / 10.0 for val in result.registers]
            else:
                self.plc_bagli_mi = False
        except Exception:
            self.plc_bagli_mi = False

        # ── Security Rule 0: PLC disconnected → stop ──
        if not self.plc_bagli_mi:
            self.islem_basarisiz_oldu(
                "HATA: PLC BAĞLANTISI KOPTU! "
                "İşlem güvenlik sebebiyle iptal edildi.")
            return

        # ── Sensor update ──
        ahsap_hedefte = True
        aktif_ahsap   = 0
        anlik: Dict[int, float] = {}

        for sw in self.sensor_widgets:
            if not self._is_sensor_active(sw):
                continue

            idx  = sw['idx']
            sid  = sw['id']
            stype = sw['type']
            sd   = self.sensors[idx]

            # Get reading from PLC (only first 2 of each type are wired)
            if stype == 'ahsap' and sid < 2:
                temp = self.son_okunan_sicakliklar[sid]
            elif stype == 'ortam' and sid < 2:
                temp = self.son_okunan_sicakliklar[sid + 2]
            else:
                temp = 0.0

            sd.push(self.sim_counter, temp)
            sw['curve'].setData(list(sd.times), list(sd.temps))

            self._set_temp_bar(sw['val'], temp, self.current_set, True)

            if len(sd.temps) > 0:
                sw['mm'].clear()

            ns = "ok" if temp >= self.current_set else "wait"
            if sw['card'].property("status") != ns:
                sw['card'].setProperty("status", ns)
                self._refresh_sensor_style(sw)

            anlik[idx] = temp
            self.sensor_gecmisi[idx].append((self.sim_counter, temp))
            if len(self.sensor_gecmisi[idx]) > 200:
                self.sensor_gecmisi[idx].pop(0)

            if stype == 'ahsap':
                aktif_ahsap += 1
                if temp < self.current_set:
                    ahsap_hedefte = False

        if aktif_ahsap == 0:
            ahsap_hedefte = False

        # ── Security Rule 1: Rapid heating (sensor removed cheat) ──
        for idx in self.active_ahsap:
            gecmis = self.sensor_gecmisi[idx]
            if len(gecmis) >= 60:
                if (gecmis[-1][1] - gecmis[-60][1]) > 4.0:
                    self.islem_basarisiz_oldu(
                        f"Ahşap {idx + 1} sensörü 1 dakikada "
                        "4°C'den fazla ısındı! (Sensör çıkarma hilesi)")
                    return

        # ── Security Rule 2: Short circuit (identical readings) ──
        aktif_idler = list(anlik.keys())
        for i in range(len(aktif_idler)):
            for j in range(i + 1, len(aktif_idler)):
                id1, id2 = aktif_idler[i], aktif_idler[j]
                pair_key = (id1, id2)
                if (anlik[id1] == anlik[id2] and anlik[id1] > 0.0):
                    self.sensor_eslesme_sayaci[pair_key] = \
                        self.sensor_eslesme_sayaci.get(pair_key, 0) + 1
                    if self.sensor_eslesme_sayaci[pair_key] >= 180:
                        self.islem_basarisiz_oldu(
                            "2 sensör 3 dakika boyunca aynı sıcaklığı "
                            "gösterdi! (Kısa devre / Hile)")
                        return
                else:
                    self.sensor_eslesme_sayaci[pair_key] = 0

        # ── Security Rule 3: Thermodynamic consistency ──
        if self.toplam_gecen_saniye > 60:
            if self.active_ortam and self.active_ahsap:
                o_vals = [anlik.get(NUM_AHSAP_SENSORS + oi, 0)
                          for oi in self.active_ortam
                          if (NUM_AHSAP_SENSORS + oi) in anlik]
                a_vals = [anlik.get(ai, 0)
                          for ai in self.active_ahsap
                          if ai in anlik]
                if o_vals and a_vals:
                    en_dusuk_ortam  = min(o_vals)
                    en_yuksek_ahsap = max(a_vals)
                    if en_dusuk_ortam < en_yuksek_ahsap:
                        self.islem_basarisiz_oldu(
                            f"Ortam sıcaklığı ({en_dusuk_ortam:.2f}°C), "
                            f"Ahşap sıcaklığının ({en_yuksek_ahsap:.2f}°C) "
                            "altına düştü! (Termodinamik ihlali)")
                        return

        # ── PLC output control (set -> üst limit -> alt limit histerezis) ──
        aktif_ahsap_degerleri = [anlik.get(ai, 0.0) for ai in self.active_ahsap if ai in anlik]
        min_ahsap_temp = min(aktif_ahsap_degerleri) if aktif_ahsap_degerleri else None

        if aktif_ahsap_degerleri:
            if not self.set_hedef_goruldu:
                # İlk aşama: operatörün verdiği set değerine kadar ısıt
                self.rezistans_aktif = True
                if ahsap_hedefte:
                    self.set_hedef_goruldu = True
                    self._log(
                        f"Set değeri görüldü ({self.current_set:.1f}°C). "
                        f"Rezistanslar üst limite ({self.ayarlar['ust_limit']:.1f}°C) kadar ısıtmaya devam edecek.",
                        "ok")
            else:
                # İkinci aşama: alt/üst limit arasında histerezisli kontrol
                if min_ahsap_temp is not None:
                    if self.rezistans_aktif and min_ahsap_temp >= self.ayarlar['ust_limit']:
                        self.rezistans_aktif = False
                        self._log(
                            f"Üst limit görüldü ({self.ayarlar['ust_limit']:.1f}°C). "
                            "Rezistanslar kapatıldı, fan çalışmaya devam ediyor.",
                            "warn")
                    elif (not self.rezistans_aktif) and min_ahsap_temp <= self.ayarlar['alt_limit']:
                        self.rezistans_aktif = True
                        self._log(
                            f"Alt limit görüldü ({self.ayarlar['alt_limit']:.1f}°C). "
                            "Rezistanslar yeniden devreye alındı.",
                            "ok")
        else:
            self.rezistans_aktif = False

        try:
            if self.plc_bagli_mi and self.plc_client.is_socket_open():
                self.plc_client.write_coil(
                    address=1280,
                    value=self.rezistans_aktif,
                    device_id=1)
                self.plc_client.write_coil(
                    address=1281, value=y1_ileri_fan, device_id=1)
                self.plc_client.write_coil(
                    address=1282, value=y2_geri_fan, device_id=1)
        except Exception as e:
            print("PLC Çıkış Hatası:", e)

        # ── Logging (every 60 s) ──
        if self.process_seconds % 60 == 0:
            ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            entry = {'zaman': ts}
            row_data = [ts]
            for ai in self.active_ahsap:
                val = anlik.get(ai, 0.0)
                entry[f'a_{ai}'] = val
                row_data.append(f"{val:.2f}")
            for oi in self.active_ortam:
                val = anlik.get(NUM_AHSAP_SENSORS + oi, 0.0)
                entry[f'o_{oi}'] = val
                row_data.append(f"{val:.2f}")
            self.log_data.append(entry)

            r = self.table_live.rowCount()
            self.table_live.insertRow(r)
            for c_idx, data in enumerate(row_data):
                self.table_live.setItem(r, c_idx, QTableWidgetItem(data))
            self.table_live.scrollToBottom()
            self.lbl_track_info.setText(
                f"Son Kayıt: {ts} — Toplam {len(self.log_data)} kayıt")

        # ── ISPM-15 sterilization logic ──
        hedef_sn = self.ayarlar['islem_suresi_dk'] * 60

        if ahsap_hedefte:
            self.holding_seconds += 1
            kalan = max(0, hedef_sn - self.holding_seconds)
            self.lbl_remain.setText(self._format_time(kalan))

            pct = (min(int((self.holding_seconds / hedef_sn) * 100), 100)
                   if hedef_sn > 0 else 0)
            self.progress.setValue(pct)

            self._set_status("●  STERİLİZASYON AKTİF", "running")
            self.header_line.setStyleSheet(f"background:{CLR.GREEN};")

            if self.holding_seconds >= hedef_sn:
                self._complete_process()
                return
        else:
            if self.holding_seconds > 0:
                self._log(
                    "Sıcaklık düştü! Sterilizasyon süresi sıfırlandı.",
                    "warn")
                self.holding_seconds = 0
                self.progress.setValue(0)
                self.lbl_remain.setText(self._format_time(hedef_sn))
            self._set_status("●  ISITMA / BEKLEME", "heating")
            self.header_line.setStyleSheet(f"background:{CLR.ORANGE};")

    # ═══════════════════════════════════════════════════════
    #  PROCESS COMPLETE  (camera end + archive + PDF)
    # ═══════════════════════════════════════════════════════
    def _complete_process(self) -> None:
        self.is_running = False
        self.rezistans_aktif = False
        self._main_timer.stop()
        self.plc_stop_all()
        self.kiln.stop()

        self._set_status("●  İŞLEM TAMAMLANDI", "done")
        self.header_line.setStyleSheet(f"background:{CLR.ACCENT};")
        self.progress.setValue(100)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        hedef_dk = self.ayarlar['islem_suresi_dk']
        self._log(f"{hedef_dk} dakikalık ısıl işlem tamamlandı. "
                  "Bitiş kanıtları bekleniyor...", "ok")

        ModernPopUp(
            "İLK AŞAMA TAMAM",
            f"{hedef_dk} dakikalık ısıl işlem başarıyla tamamlandı.\n\n"
            "Lütfen fırını boşaltma kanıtlarını (Dolu → Boş) çekmek için "
            "açılacak kamerayı kullanın.",
            "success", self).exec_()

        # End camera evidence
        cam_dialog = ProcessCameraDialog(
            self.video_klasoru, mode="end", parent=self)
        cam_dialog.exec_()
        self.img_son_dolu_b64 = cam_dialog.img_step1_b64
        self.img_son_bos_b64  = cam_dialog.img_step2_b64

        simdi = datetime.now()
        self.bitis_zamani  = simdi.strftime('%d.%m.%Y %H:%M:%S')
        current_parti      = f"PRT-{simdi.strftime('%Y%m%d-%H%M')}"

        try:
            parti_klasoru = os.path.join(self.kayit_klasoru, current_parti)
            os.makedirs(parti_klasoru, exist_ok=True)

            # Move temp videos to archive
            video_map = [
                ("TEMP_BOS.mp4",      f"{current_parti}_1_BASLANGIC_BOS.mp4"),
                ("TEMP_DOLU.mp4",     f"{current_parti}_2_BASLANGIC_DOLU.mp4"),
                ("TEMP_SON_DOLU.mp4", f"{current_parti}_3_BITIS_DOLU.mp4"),
                ("TEMP_SON_BOS.mp4",  f"{current_parti}_4_BITIS_BOS.mp4"),
            ]
            for temp_isim, kalici_isim in video_map:
                src = os.path.join(self.video_klasoru, temp_isim)
                dst = os.path.join(parti_klasoru, kalici_isim)
                if os.path.exists(src):
                    os.rename(src, dst)

            # Graph snapshot
            kesilecek = self.ayarlar['islem_suresi_dk'] * 60
            all_times = list(self.sensors[0].times)
            if len(all_times) >= kesilecek:
                self.plot_widget.setXRange(
                    all_times[-kesilecek], all_times[-1])
            elif all_times:
                self.plot_widget.setXRange(all_times[0], all_times[-1])

            QApplication.processEvents()
            grafik_gecici = os.path.join(parti_klasoru, 'grafik.png')
            pixmap = self.plot_widget.grab()
            pixmap.save(grafik_gecici, "PNG")
            self.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis)

            with open(grafik_gecici, "rb") as img_file:
                b64_grafik = base64.b64encode(img_file.read()).decode('utf-8')

            veri_paketi = {
                "firma":            self.current_firma,
                "urun":             self.current_urun,
                "parti":            current_parti,
                "adet":             self.current_adet,
                "m3":               self.current_m3,
                "set_sicaklik":     self.current_set,
                "tarih":            self.bitis_zamani,
                "baslangic_zamani": self.baslangic_zamani,
                "bitis_zamani":     self.bitis_zamani,
                "active_ahsap":     self.active_ahsap,
                "active_ortam":     self.active_ortam,
                "log_data":         self.log_data,
                "grafik_b64":       b64_grafik,
                "img_bos_b64":      self.img_bos_b64,
                "img_dolu_b64":     self.img_dolu_b64,
                "img_son_dolu_b64": self.img_son_dolu_b64,
                "img_son_bos_b64":  self.img_son_bos_b64,
            }

            sifreli = zlib.compress(
                json.dumps(veri_paketi, ensure_ascii=False).encode('utf-8'))
            ldk_yolu = os.path.join(parti_klasoru, f"{current_parti}.ldk")
            with open(ldk_yolu, "wb") as f:
                f.write(sifreli)

            self._log(
                f"Arşiv kaydedildi: {current_parti}", "ok")

            ModernPopUp(
                "İŞLEM BAŞARIYLA TAMAMLANDI",
                f"Parti No: {current_parti}\n"
                f"Firma: {self.current_firma}\n"
                f"Ürün: {self.current_urun}\n"
                f"Adet: {self.current_adet}\n"
                f"Hacim: {self.current_m3:.2f} m³\n\n"
                "Rapor ve videolar arşivlendi.",
                "success", self).exec_()

        except Exception as e:
            self._log(f"Kayıt Hatası: {e}", "error")
            ModernPopUp("KAYIT HATASI",
                f"Arşiv kaydedilirken hata oluştu:\n{e}",
                "critical", self).exec_()

        self.lbl_fan.setText("FAN: PASİF")
        self.lbl_fan.setStyleSheet(
            f"color:{CLR.TEXT3}; font-size:14px; font-weight:bold;")


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainScada()
    window.showMaximized()
    sys.exit(app.exec_())
