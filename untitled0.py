import sys, math, random
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QPushButton, QFrame, QButtonGroup, QSizePolicy, 
                             QGraphicsDropShadowEffect, QListWidget)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient, QPainterPath, QConicalGradient

import pyqtgraph as pg

# --- TASARIM KATMANI ---
STYLESHEET = """
QMainWindow { background-color: #0f172a; } 

/* SIDEBAR */
#Sidebar { 
    background-color: #1e293b; border-right: 1px solid #334155;
    min-width: 260px; max-width: 260px;
}
#SidebarLabel {
    color: #38bdf8; font-size: 24px; font-weight: 900; letter-spacing: 1.5px;
    padding: 30px 20px; border-bottom: 1px solid #334155;
}
QPushButton.navBtn {
    text-align: left; padding: 18px 25px;
    background-color: transparent; border: none; border-left: 4px solid transparent;
    color: #94a3b8; font-size: 15px; font-weight: 600;
}
QPushButton.navBtn:hover { background-color: #334155; color: white; }
QPushButton.navBtn:checked { 
    background-color: #1e293b; color: #38bdf8; border-left: 4px solid #38bdf8; font-weight: bold;
}

/* CONTENT AREA */
#ContentArea { background-color: #0f172a; }

/* HEADER */
#HeaderFrame {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e293b, stop:1 #0f172a);
    border-radius: 15px;
    border: 1px solid #334155;
}
#HeaderLine { background-color: #38bdf8; border-radius: 2px; }

/* Durum Rozeti */
QLabel[status="idle"] { 
    background-color: rgba(148, 163, 184, 0.1); color: #94a3b8; 
    border: 1px solid #475569; border-radius: 12px; padding: 4px 12px; font-weight: bold;
}
QLabel[status="running"] { 
    background-color: rgba(16, 185, 129, 0.15); color: #34d399; 
    border: 1px solid #10b981; border-radius: 12px; padding: 4px 12px; font-weight: bold;
}
QLabel[status="stopped"] { 
    background-color: rgba(239, 68, 68, 0.15); color: #f87171; 
    border: 1px solid #ef4444; border-radius: 12px; padding: 4px 12px; font-weight: bold;
}

/* KARTLAR */
QFrame.card {
    background-color: #1e293b; border: 1px solid #334155; border-radius: 12px;
}

/* SENSÖR KUTULARI */
QFrame.sensorNode {
    background-color: #0f172a; border-radius: 8px; border: 1px solid #334155;
}
QFrame.sensorNode[status="wait"] { border-left: 4px solid #f59e0b; }
QFrame.sensorNode[status="ok"] { border-left: 4px solid #10b981; background-color: rgba(16, 185, 129, 0.15); }

QLabel.nodeTitle { color: #94a3b8; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }
QLabel.nodeValue { color: #f8fafc; font-size: 28px; font-weight: 900; font-family: 'Segoe UI', sans-serif; }

/* LOG LİSTESİ */
QListWidget {
    background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #cbd5e1; font-family: 'Consolas'; font-size: 12px;
}

/* BUTONLAR */
QPushButton.actionBtn { border-radius: 8px; font-size: 14px; font-weight: bold; padding: 12px; color: white; }
#btnStart { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669); border: 1px solid #34d399; }
#btnStart:hover { background: #34d399; }
#btnStop { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ef4444, stop:1 #dc2626); border: 1px solid #f87171; }
#btnStop:hover { background: #f87171; }
"""

# --- FIRIN WIDGET'I (Aynı) ---
class SmoothKilnWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 350)
        self.fan_angle = 0.0
        self.flow_offset = 0.0
        self.is_running = False
        self.heat_glow = 0.0
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animate)
        
    def start(self):
        self.is_running = True
        self.anim_timer.start(16) 
        
    def stop(self):
        self.is_running = False
        self.anim_timer.stop()
        self.heat_glow = 0.0
        self.update()

    def animate(self):
        self.fan_angle = (self.fan_angle + 8) % 360 
        self.flow_offset = (self.flow_offset - 1.5) % 40 
        if self.heat_glow < 1.0: self.heat_glow += 0.005
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        
        rect = QRectF(10, 10, w-20, h-20)
        wall_thick = 15
        inner_rect = rect.adjusted(wall_thick, wall_thick, -wall_thick, -wall_thick)
        
        metal_grad = QLinearGradient(0, 0, 0, h)
        metal_grad.setColorAt(0, QColor("#475569"))
        metal_grad.setColorAt(1, QColor("#1e293b"))
        p.setBrush(QBrush(metal_grad))
        p.setPen(QPen(QColor("#0f172a"), 2))
        p.drawRoundedRect(rect, 8, 8)
        
        base_blue = QColor("#0f172a")
        hot_red = QColor(60, 20, 10)
        bg_color = self.mix_colors(base_blue, hot_red, self.heat_glow)
        
        p.setBrush(QBrush(bg_color))
        p.setPen(QPen(QColor("#000"), 3))
        p.drawRect(inner_rect)
        
        if self.is_running:
            radial = QRadialGradient(w/2, h/2, w/1.5)
            radial.setColorAt(0, QColor(255, 100, 50, int(60 * self.heat_glow)))
            radial.setColorAt(1, Qt.transparent)
            p.setBrush(QBrush(radial))
            p.setPen(Qt.NoPen)
            p.drawRect(inner_rect)

        p.setPen(QPen(QColor("#94a3b8"), 3))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(inner_rect.left(), inner_rect.top() + 80)
        path.quadTo(inner_rect.left() + 20, inner_rect.top() + 20, inner_rect.left() + 100, inner_rect.top())
        path.moveTo(inner_rect.right(), inner_rect.top() + 80)
        path.quadTo(inner_rect.right() - 20, inner_rect.top() + 20, inner_rect.right() - 100, inner_rect.top())
        p.drawPath(path)

        fan_y = inner_rect.top() + 50
        self.draw_smooth_fan(p, w/2 - 90, fan_y, 40)
        self.draw_smooth_fan(p, w/2 + 90, fan_y, 40)

        heater_y_start = fan_y + 50
        heater_y_end = inner_rect.bottom() - 30
        
        if self.is_running:
            pulse = 180 + int(70 * math.sin(self.fan_angle * 0.05))
            glow_col = QColor(255, 80, 20, pulse)
            p.setPen(QPen(glow_col, 8, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(inner_rect.left()+25, heater_y_start), QPointF(inner_rect.left()+25, heater_y_end))
            p.drawLine(QPointF(inner_rect.right()-25, heater_y_start), QPointF(inner_rect.right()-25, heater_y_end))
            
            p.setPen(QPen(QColor(255, 255, 200), 2, Qt.DotLine))
            p.drawLine(QPointF(inner_rect.left()+25, heater_y_start), QPointF(inner_rect.left()+25, heater_y_end))
            p.drawLine(QPointF(inner_rect.right()-25, heater_y_start), QPointF(inner_rect.right()-25, heater_y_end))

        stack_w = inner_rect.width() * 0.55
        stack_h = inner_rect.height() * 0.45
        stack_rect = QRectF((w - stack_w)/2, inner_rect.bottom() - stack_h - 10, stack_w, stack_h)
        self.draw_stack(p, stack_rect)

        if self.is_running:
            self.draw_flow(p, inner_rect, stack_rect, fan_y)

    def mix_colors(self, c1, c2, ratio):
        r = int(c1.red() * (1-ratio) + c2.red() * ratio)
        g = int(c1.green() * (1-ratio) + c2.green() * ratio)
        b = int(c1.blue() * (1-ratio) + c2.blue() * ratio)
        return QColor(r, g, b)

    def draw_smooth_fan(self, p, x, y, r):
        p.save()
        p.translate(x, y)
        p.setPen(QPen(QColor("#475569"), 3))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0,0), r+2, r+2)
        
        if self.is_running:
            p.rotate(self.fan_angle)
            blade_color = QColor("#38bdf8")
            blur_grad = QRadialGradient(0,0, r)
            blur_grad.setColorAt(0, Qt.transparent)
            blur_grad.setColorAt(0.8, QColor(56, 189, 248, 50))
            blur_grad.setColorAt(1, Qt.transparent)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(blur_grad))
            p.drawEllipse(QPointF(0,0), r, r)
        else:
            blade_color = QColor("#64748b")
            
        p.setBrush(QBrush(blade_color))
        p.setPen(Qt.NoPen)
        for _ in range(3):
            p.drawPie(QRectF(-r, -r, r*2, r*2), 0, 40 * 16)
            p.rotate(120)
        p.setBrush(QBrush(QColor("#e2e8f0")))
        p.drawEllipse(QPointF(0,0), 8, 8)
        p.restore()

    def draw_stack(self, p, rect):
        p.setBrush(QBrush(QColor("#3f2e18")))
        p.setPen(Qt.NoPen)
        p.drawRect(QRectF(rect.left(), rect.bottom(), 25, 10))
        p.drawRect(QRectF(rect.center().x()-12, rect.bottom(), 25, 10))
        p.drawRect(QRectF(rect.right()-25, rect.bottom(), 25, 10))
        
        layers = 5
        h_step = rect.height() / layers
        wood_col = QColor("#d97706")
        p.setPen(QPen(QColor("#78350f"), 1))
        
        for i in range(layers):
            y = rect.bottom() - (i+1)*h_step
            if i < layers - 1:
                p.setBrush(QBrush(QColor("#271502")))
                p.drawRect(QRectF(rect.left()+10, y-5, rect.width()-20, 5))
            p.setBrush(QBrush(wood_col))
            blocks = 6
            bw = rect.width() / blocks
            for k in range(blocks):
                p.drawRect(QRectF(rect.left() + k*bw + 2, y, bw - 4, h_step - 5))

    def draw_flow(self, p, bounds, stack, fan_y):
        path = QPainterPath()
        path.moveTo(bounds.center().x() - 50, fan_y + 30)
        path.lineTo(bounds.left() + 40, fan_y + 30)
        path.lineTo(bounds.left() + 40, bounds.bottom() - 30)
        path.lineTo(stack.left() + 40, bounds.bottom() - 30)
        path.lineTo(stack.left() + 40, stack.top() + 20)
        path.lineTo(bounds.center().x() - 50, fan_y + 50)
        
        path.moveTo(bounds.center().x() + 50, fan_y + 30)
        path.lineTo(bounds.right() - 40, fan_y + 30)
        path.lineTo(bounds.right() - 40, bounds.bottom() - 30)
        path.lineTo(stack.right() - 40, bounds.bottom() - 30)
        path.lineTo(stack.right() - 40, stack.top() + 20)
        path.lineTo(bounds.center().x() + 50, fan_y + 50)

        pen = QPen(QColor(0, 200, 255, 180), 4)
        if self.heat_glow > 0.5: pen.setColor(QColor(255, 120, 50, 200))
        pen.setStyle(Qt.CustomDashLine)
        pen.setDashPattern([10, 10]) 
        pen.setDashOffset(self.flow_offset)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

# --- ANA UYGULAMA ---
class MainScada(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAODİKYA SCADA V14.0 - FERAH SÜRÜM")
        self.setMinimumSize(1600, 950)
        self.setStyleSheet(STYLESHEET)
        
        self.set_duration_minutes = 45 
        self.elapsed_seconds = 0   
        self.remaining_seconds = 0 
        self.is_counting = False
        
        self.initUI()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_demo)
        self.timer.start(1000)

    def initUI(self):
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(central)

        # 1. SIDEBAR
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sb_layout = QVBoxLayout(sidebar)
        
        lbl_logo = QLabel("LAODİKYA\nOTOMASYON")
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setObjectName("SidebarLabel")
        sb_layout.addWidget(lbl_logo)
        
        btn_dash = QPushButton("📊  Kontrol Paneli")
        btn_dash.setProperty("class", "navBtn")
        btn_dash.setCheckable(True)
        btn_dash.setChecked(True)
        sb_layout.addSpacing(20)
        sb_layout.addWidget(btn_dash)

        btn_archive = QPushButton("📂  Rapor Arşivi")
        btn_archive.setProperty("class", "navBtn")
        sb_layout.addWidget(btn_archive)

        btn_settings = QPushButton("⚙  Sistem Ayarları")
        btn_settings.setProperty("class", "navBtn")
        sb_layout.addWidget(btn_settings)
        sb_layout.addStretch()
        
        time_lbl = QLabel("12:00:00")
        time_lbl.setStyleSheet("color:white; font-size:20px; font-weight:bold; padding:20px;")
        time_lbl.setAlignment(Qt.AlignCenter)
        self.time_lbl = time_lbl
        sb_layout.addWidget(time_lbl)
        
        main_layout.addWidget(sidebar)

        # 2. İÇERİK
        content = QWidget()
        content.setObjectName("ContentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # HEADER
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,100)); shadow.setOffset(0,5)
        header_frame.setGraphicsEffect(shadow)
        
        hl_outer = QVBoxLayout(header_frame)
        hl_outer.setContentsMargins(0,0,0,0)
        hl_outer.setSpacing(0)
        
        hl = QHBoxLayout()
        hl.setContentsMargins(25, 20, 25, 20)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(8)
        lbl_title = QLabel("ISPM-15 KONTROL ÜNİTESİ")
        lbl_title.setStyleSheet("color: white; font-size: 26px; font-weight: 900; letter-spacing: 1px;")
        self.lbl_status = QLabel("●  DURUM: BEKLEMEDE")
        self.lbl_status.setProperty("status", "idle")
        self.lbl_status.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        title_box.addWidget(lbl_title)
        title_box.addWidget(self.lbl_status)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(15)
        btn_start = QPushButton("İŞLEMİ BAŞLAT")
        btn_start.setObjectName("btnStart")
        btn_start.setProperty("class", "actionBtn")
        btn_start.setMinimumSize(160, 55)
        btn_start.setCursor(Qt.PointingHandCursor)
        btn_start.clicked.connect(self.start_sys)
        btn_stop = QPushButton("ACİL DURDUR")
        btn_stop.setObjectName("btnStop")
        btn_stop.setProperty("class", "actionBtn")
        btn_stop.setMinimumSize(160, 55)
        btn_stop.setCursor(Qt.PointingHandCursor)
        btn_stop.clicked.connect(self.stop_sys)
        btn_box.addWidget(btn_start)
        btn_box.addWidget(btn_stop)
        
        hl.addLayout(title_box)
        hl.addStretch()
        hl.addLayout(btn_box)
        hl_outer.addLayout(hl)
        
        self.header_line = QFrame()
        self.header_line.setObjectName("HeaderLine")
        self.header_line.setFixedHeight(4)
        self.header_line.setStyleSheet("background-color: #94a3b8;")
        hl_outer.addWidget(self.header_line)
        
        content_layout.addWidget(header_frame)

        # GRID
        grid = QGridLayout()
        # --- DÜZELTME BURADA: Boşluklar arttırıldı ---
        grid.setHorizontalSpacing(25) 
        grid.setVerticalSpacing(30)
        
        # SOL SÜTUN
        left_col = QFrame()
        left_col.setProperty("class", "card")
        lc_layout = QVBoxLayout(left_col)
        lc_layout.setContentsMargins(20, 20, 20, 20)
        lc_layout.setSpacing(20) # Kart içi eleman boşluğu da arttı
        
        lc_layout.addWidget(QLabel("🔥 FIRIN SİMÜLASYONU", styleSheet="color: #38bdf8; font-weight: bold; font-size: 16px;"))
        self.kiln = SmoothKilnWidget()
        lc_layout.addWidget(self.kiln)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #334155;")
        lc_layout.addWidget(line)
        
        lc_layout.addWidget(QLabel("🌡️ CANLI SICAKLIKLAR (13 AHŞAP + 2 ORTAM)", styleSheet="color: #38bdf8; font-weight: bold; font-size: 16px;"))
        
        sensor_grid = QGridLayout()
        # --- DÜZELTME BURADA: Sensör ızgarası boşlukları arttırıldı ---
        sensor_grid.setHorizontalSpacing(20)
        sensor_grid.setVerticalSpacing(25)
        self.sensors = []
        total_sensors = 15
        columns = 4 
        
        for i in range(total_sensors):
            node = QFrame()
            node.setProperty("class", "sensorNode")
            node.setProperty("status", "wait")
            nl = QVBoxLayout(node)
            # --- DÜZELTME BURADA: Sensör kutusu iç boşlukları rahatlatıldı ---
            nl.setContentsMargins(20, 15, 20, 15)
            
            if i < 13:
                name = f"AHŞAP - {i+1}"
                color_code = "#94a3b8"
            else:
                name = f"ORTAM - {i-12}"
                color_code = "#38bdf8"
                
            title = QLabel(name)
            title.setProperty("class", "nodeTitle")
            title.setStyleSheet(f"color: {color_code};")
            nl.addWidget(title)
            
            val = QLabel("24.5")
            val.setProperty("class", "nodeValue")
            val.setAlignment(Qt.AlignRight)
            nl.addWidget(val)
            
            row = i // columns
            col = i % columns
            sensor_grid.addWidget(node, row, col)
            self.sensors.append({'frame': node, 'val': val})
            
        lc_layout.addLayout(sensor_grid)
        grid.addWidget(left_col, 0, 0, 3, 1)

        # === SAĞ SÜTUN ===
        graph_card = QFrame()
        graph_card.setProperty("class", "card")
        gc_layout = QVBoxLayout(graph_card)
        gc_layout.setContentsMargins(10,10,10,10)
        gc_layout.addWidget(QLabel("📈 TREND ANALİZİ", styleSheet="color: #38bdf8; font-weight: bold;"))
        
        pg.setConfigOption('background', '#1e293b')
        pg.setConfigOption('foreground', '#94a3b8')
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.1)
        self.plot.getAxis('left').setWidth(40)
        self.curve = self.plot.plot(pen=pg.mkPen('#10b981', width=2))
        gc_layout.addWidget(self.plot)
        grid.addWidget(graph_card, 0, 1, 1, 1)

        # BİLGİ KARTI
        info_card = QFrame()
        info_card.setProperty("class", "card")
        ic_layout = QVBoxLayout(info_card)
        ic_layout.setSpacing(0)
        ic_layout.setContentsMargins(0,0,0,0) 
        
        time_container = QWidget()
        hbox_time = QHBoxLayout(time_container)
        hbox_time.setContentsMargins(20, 20, 20, 20)
        
        vbox_elapsed = QVBoxLayout()
        lbl_e_title = QLabel("GEÇEN SÜRE")
        lbl_e_title.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        lbl_e_title.setAlignment(Qt.AlignCenter)
        self.lbl_elapsed = QLabel("00:00:00")
        self.lbl_elapsed.setStyleSheet("color: #10b981; font-size: 34px; font-weight: bold; font-family: 'Consolas';")
        self.lbl_elapsed.setAlignment(Qt.AlignCenter)
        vbox_elapsed.addWidget(lbl_e_title)
        vbox_elapsed.addWidget(self.lbl_elapsed)
        
        line_v = QFrame()
        line_v.setFrameShape(QFrame.VLine)
        line_v.setStyleSheet("color: #334155;")
        
        vbox_remain = QVBoxLayout()
        lbl_r_title = QLabel("KALAN SÜRE")
        lbl_r_title.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        lbl_r_title.setAlignment(Qt.AlignCenter)
        self.lbl_remain = QLabel("00:45:00")
        self.lbl_remain.setStyleSheet("color: #f59e0b; font-size: 34px; font-weight: bold; font-family: 'Consolas';")
        self.lbl_remain.setAlignment(Qt.AlignCenter)
        vbox_remain.addWidget(lbl_r_title)
        vbox_remain.addWidget(self.lbl_remain)
        
        hbox_time.addLayout(vbox_elapsed)
        hbox_time.addWidget(line_v)
        hbox_time.addLayout(vbox_remain)
        ic_layout.addWidget(time_container)
        
        fan_strip = QFrame()
        fan_strip.setStyleSheet("background-color: #0f172a; border-top: 1px solid #334155; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        hbox_fan = QHBoxLayout(fan_strip)
        hbox_fan.setContentsMargins(20, 15, 20, 15)
        
        lbl_fan_icon = QLabel("🌀")
        lbl_fan_icon.setStyleSheet("font-size: 24px;")
        self.lbl_fan_text = QLabel("FAN DURUMU: BEKLEMEDE")
        self.lbl_fan_text.setStyleSheet("color: #64748b; font-size: 16px; font-weight: bold;")
        
        hbox_fan.addWidget(lbl_fan_icon)
        hbox_fan.addWidget(self.lbl_fan_text)
        hbox_fan.addStretch()
        
        ic_layout.addWidget(fan_strip)
        grid.addWidget(info_card, 1, 1, 1, 1)

        # SİSTEM LOGLARI
        log_card = QFrame()
        log_card.setProperty("class", "card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(10,10,10,10)
        log_layout.addWidget(QLabel("📋 SİSTEM GÜNLÜĞÜ", styleSheet="color: #38bdf8; font-weight: bold;"))
        
        self.list_logs = QListWidget()
        self.log_msg("Sistem başlatıldı.")
        self.log_msg("15 Sensör tanımlandı.")
        log_layout.addWidget(self.list_logs)
        grid.addWidget(log_card, 2, 1, 1, 1)

        grid.setColumnStretch(0, 65)
        grid.setColumnStretch(1, 35)
        grid.setRowStretch(0, 40) 
        grid.setRowStretch(1, 25) 
        grid.setRowStretch(2, 35) 
        
        content_layout.addLayout(grid)
        main_layout.addWidget(content)

        self.data = [24.5] * 100
        self.counter = 0

    def log_msg(self, msg):
        t = datetime.now().strftime("%H:%M:%S")
        self.list_logs.insertItem(0, f"[{t}] {msg}")

    def update_demo(self):
        from datetime import datetime
        self.time_lbl.setText(datetime.now().strftime("%H:%M:%S"))
        
        if self.kiln.is_running:
            self.counter += 1
            self.elapsed_seconds += 1
            
            eh, er = divmod(self.elapsed_seconds, 3600)
            em, es = divmod(er, 60)
            self.lbl_elapsed.setText(f"{eh:02d}:{em:02d}:{es:02d}")
            
            if self.remaining_seconds > 0:
                self.remaining_seconds -= 1
                rh, rr = divmod(self.remaining_seconds, 3600)
                rm, rs = divmod(rr, 60)
                self.lbl_remain.setText(f"{rh:02d}:{rm:02d}:{rs:02d}")
            else:
                if self.is_counting:
                    self.stop_sys()
                    self.log_msg("Hedef süre tamamlandı!")
                    self.is_counting = False

            nxt = self.data[-1] + random.uniform(-0.2, 0.4)
            if nxt > 60: nxt=60
            self.data = self.data[1:] + [nxt]
            self.curve.setData(self.data)
            
            for i, s in enumerate(self.sensors):
                v = self.data[-1] + random.uniform(-2, 2)
                if i >= 13: v -= 5
                s['val'].setText(f"{v:.1f}")
                if v > 56: s['frame'].setProperty("status", "ok")
                else: s['frame'].setProperty("status", "wait")
                s['frame'].style().unpolish(s['frame'])
                s['frame'].style().polish(s['frame'])
            
            if (self.counter // 10) % 2 == 0:
                self.lbl_fan_text.setText("FAN DURUMU: SAĞ YÖN (CW)")
                self.lbl_fan_text.setStyleSheet("color: #10b981; font-size: 16px; font-weight: bold;")
            else:
                self.lbl_fan_text.setText("FAN DURUMU: SOL YÖN (CCW)")
                self.lbl_fan_text.setStyleSheet("color: #38bdf8; font-size: 16px; font-weight: bold;")

    def start_sys(self):
        self.kiln.start()
        self.lbl_status.setText("●  DURUM: ISITMA AKTİF")
        self.lbl_status.setProperty("status", "running")
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)
        self.header_line.setStyleSheet("background-color: #10b981;")
        self.log_msg("Isıl işlem başlatıldı.")
        
        self.elapsed_seconds = 0
        self.remaining_seconds = self.set_duration_minutes * 60
        self.is_counting = True
        self.lbl_elapsed.setText("00:00:00")
        rh, rr = divmod(self.remaining_seconds, 3600)
        rm, rs = divmod(rr, 60)
        self.lbl_remain.setText(f"{rh:02d}:{rm:02d}:{rs:02d}")

    def stop_sys(self):
        self.kiln.stop()
        self.is_counting = False
        self.lbl_status.setText("●  DURUM: DURDURULDU")
        self.lbl_status.setProperty("status", "stopped")
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)
        self.header_line.setStyleSheet("background-color: #ef4444;")
        self.lbl_fan_text.setText("FAN DURUMU: PASİF")
        self.lbl_fan_text.setStyleSheet("color: #64748b; font-size: 16px; font-weight: bold;")
        self.log_msg("İşlem operatör tarafından durduruldu.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainScada()
    window.show()
    sys.exit(app.exec_())