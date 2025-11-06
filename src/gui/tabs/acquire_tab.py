# gui/tabs/acquire_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel,
    QSpinBox, QLineEdit, QPushButton, QTextEdit,
    QFileDialog, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt
import os
import numpy as np

# Matplotlib 嵌入 PySide6
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core.acquire_controller import AcquisitionController


# ===================== 内嵌图像画布类 =====================
class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        super().__init__(self.fig)
        self.setParent(parent)
        self.fig.tight_layout(pad=2.0)

    def update_plots(self, data):
        """更新采集结果图像"""
        if data is None:
            return
        self.ax1.clear()
        self.ax2.clear()

        # 图 1：Sum over Y-axis
        self.ax1.set_title("Sum over Y-axis")
        self.ax1.plot(data["data"].sum(axis=0).T)
        self.ax1.set_xlabel("Channel")
        self.ax1.set_ylabel("Counts")

        # 图 2：Total sum
        self.ax2.set_title("Total sum")
        self.ax2.plot(data["data"].sum(axis=0).sum(axis=1).T)
        self.ax2.set_xlabel("Index")
        self.ax2.set_ylabel("Counts")

        self.draw()


# ===================== 主采集界面类 =====================
class AcquireTab(QWidget):
    def __init__(self, det_ctrl=None):
        super().__init__()
        self.det_ctrl = det_ctrl
        self.acq_ctrl = AcquisitionController(det_ctrl)
        self._setup_ui()

    # ------------------------------------------------------------
    def _setup_ui(self):
        layout = QVBoxLayout()
        grid = QGridLayout()
        w_input = 90
        row = 0

        # === 参数输入 ===
        grid.addWidget(QLabel("电压 (kV)"), row, 0)
        self.voltage = QSpinBox(); self.voltage.setRange(10, 200); self.voltage.setValue(40); self.voltage.setFixedWidth(w_input)
        grid.addWidget(self.voltage, row, 1)

        row += 1
        grid.addWidget(QLabel("电流 (mA)"), row, 0)
        self.current = QSpinBox(); self.current.setRange(1, 50); self.current.setValue(7); self.current.setFixedWidth(w_input)
        grid.addWidget(self.current, row, 1)

        row += 1
        grid.addWidget(QLabel("滤波范围"), row, 0)
        self.f1, self.f2 = QSpinBox(), QSpinBox()
        for f in (self.f1, self.f2):
            f.setRange(0, 5000); f.setFixedWidth(w_input)
        self.f1.setValue(1650); self.f2.setValue(1950)
        hb_filter = QHBoxLayout()
        hb_filter.addWidget(self.f1); hb_filter.addWidget(QLabel("~")); hb_filter.addWidget(self.f2)
        grid.addLayout(hb_filter, row, 1)

        row += 1
        grid.addWidget(QLabel("速度 (mm/s)"), row, 0)
        self.speed = QSpinBox(); self.speed.setRange(0, 5000); self.speed.setValue(666); self.speed.setFixedWidth(w_input)
        grid.addWidget(self.speed, row, 1)

        row += 1
        grid.addWidget(QLabel("采集时长 (s)"), row, 0)
        self.duration = QSpinBox(); self.duration.setRange(1, 999); self.duration.setValue(8); self.duration.setFixedWidth(w_input)
        grid.addWidget(self.duration, row, 1)

        row += 1
        grid.addWidget(QLabel("采样间隔 (×10ms)"), row, 0)
        self.interval = QSpinBox(); self.interval.setRange(1, 100); self.interval.setValue(20); self.interval.setFixedWidth(w_input)
        grid.addWidget(self.interval, row, 1)

        row += 1
        grid.addWidget(QLabel("WinRange"), row, 0)
        self.win_id, self.win_low, self.win_high = QSpinBox(), QSpinBox(), QSpinBox()
        for w in (self.win_id, self.win_low, self.win_high):
            w.setRange(0, 1024); w.setFixedWidth(w_input)
        self.win_low.setValue(0); self.win_high.setValue(119)
        hb_win = QHBoxLayout()
        hb_win.addWidget(QLabel("ID")); hb_win.addWidget(self.win_id)
        hb_win.addWidget(QLabel("Low")); hb_win.addWidget(self.win_low)
        hb_win.addWidget(QLabel("High")); hb_win.addWidget(self.win_high)
        grid.addLayout(hb_win, row, 1)

        row += 1
        grid.addWidget(QLabel("自定义名"), row, 0)
        self.name = QLineEdit("test17"); self.name.setFixedWidth(160)
        grid.addWidget(self.name, row, 1)

        row += 1
        grid.addWidget(QLabel("保存路径"), row, 0)
        self.dir_edit = QLineEdit(os.path.join(os.getcwd(), "AcqData"))
        self.dir_edit.setFixedWidth(260)
        self.dir_btn = QPushButton("选择目录"); self.dir_btn.setFixedWidth(80)
        hb_dir = QHBoxLayout()
        hb_dir.addWidget(self.dir_edit); hb_dir.addWidget(self.dir_btn)
        grid.addLayout(hb_dir, row, 1)

        layout.addLayout(grid)

        # === 控制按钮 ===
        ctrl = QHBoxLayout()
        ctrl.addStretch()
        self.btn_start = QPushButton("开始采集")
        self.btn_start.setFixedWidth(120)
        ctrl.addWidget(self.btn_start)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # === 日志 + 图像显示 ===
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        # 嵌入的 matplotlib 区域
        self.canvas = MatplotlibCanvas(self)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

        # 事件绑定
        self.dir_btn.clicked.connect(self.select_dir)
        self.btn_start.clicked.connect(self.start_acquisition)

    # ------------------------------------------------------------
    def select_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存路径")
        if folder:
            self.dir_edit.setText(folder)
            self.log_box.append(f"[INFO] 保存路径：{folder}")

    # ------------------------------------------------------------
    def start_acquisition(self):
        if self.det_ctrl is None or self.det_ctrl.offline:
            self.log_box.append("[ERROR] 当前未连接探测器，请先在“连接”界面建立连接。")
            return
        
        # --- 采集参数 ---
        v, a = self.voltage.value(), self.current.value()
        f1, f2 = self.f1.value(), self.f2.value()
        s = self.speed.value()
        dur, inter = self.duration.value(), self.interval.value()
        win = (self.win_id.value(), self.win_low.value(), self.win_high.value())
        name = self.name.text().strip()
        save_dir = self.dir_edit.text().strip()
        os.makedirs(save_dir, exist_ok=True)

        # --- 文件名 ---
        file_name = f"{name}_{s}mmps_{f1}-{f2}_{v}kV_{a}mA_win{win[0]}_{win[1]}-{win[2]}_{dur}s_int{inter}.mat"
        file_path = os.path.join(save_dir, file_name)

        # --- ✅ 在采集前弹窗检查 ---
        if os.path.exists(file_path):
            res = QMessageBox.question(
                self,
                "文件已存在",
                f"文件已存在：\n{file_path}\n\n是否覆盖？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if res == QMessageBox.No or res == QMessageBox.Cancel:
                self.log_box.append("[INFO] 用户取消采集。")
                return  # ✅ 用户拒绝覆盖，直接退出
            else:
                self.log_box.append(f"[WARN] 用户选择覆盖已有文件：{file_name}")

        # --- 启动采集 ---
        self.log_box.append(f"[INFO] 开始采集：{file_name}")

        self.acq_ctrl.acquire(
            file_path, v, a, (f1, f2), s, dur, inter, win, self._on_log_update
        )

    # ------------------------------------------------------------
    def _on_log_update(self, level, message):
        """采集状态更新"""
        self.log_box.append(f"{level} {message}")

        # # 采集完成后更新嵌入式图像
        # if "[DONE]" in level or level == "[DONE]":
        #     if hasattr(self.acq_ctrl, "last_data"):
        #         self.canvas.update_plots(self.acq_ctrl.last_data)
