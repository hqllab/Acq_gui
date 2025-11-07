# gui/tabs/acquire_tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel,
    QSpinBox, QDoubleSpinBox, QLineEdit, QPushButton,
    QTextEdit, QFileDialog, QHBoxLayout, QGroupBox, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt
import os
import numpy as np
import matplotlib.pyplot as plt

from core.acquire_controller import AcquisitionController
from core.AcqFunc.AcqFunc import _show


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

        # === 采集参数输入 ===
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

        # === 日志输出 ===
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        # === 绘图参数设置 ===
        plot_group = QGroupBox("绘图参数设置")
        plot_layout = QGridLayout()

        # 1️⃣ 帧数据
        self.show_frame = QCheckBox("帧数据 (Frame)")
        self.show_frame.setChecked(True)  # ✅ 默认选中
        # self.frame_index = QSpinBox(); self.frame_index.setRange(0, 1000); self.frame_index.setValue(0)
        plot_layout.addWidget(self.show_frame, 0, 0)
        # plot_layout.addWidget(QLabel("帧索引:"), 0, 1)
        # plot_layout.addWidget(self.frame_index, 0, 2)

        # 2️⃣ Naive 重建
        self.show_recon = QCheckBox("Naive Recon")
        self.show_recon.setChecked(True)  # ✅ 默认选中
        
        # pos_step
        self.pos_step = QDoubleSpinBox()
        self.pos_step.setRange(0.0000, 10.0000)
        self.pos_step.setDecimals(4)           # ✅ 显示 4 位小数
        self.pos_step.setSingleStep(0.0005)    # ✅ 调整步长
        self.pos_step.setValue(0.0375)         # ✅ 准确显示 0.0375
        # self.pos_step.setSuffix(" mm")         # 可选：显示单位
        self.pos_step.setKeyboardTracking(False)

        # rate
        self.rate = QDoubleSpinBox()
        self.rate.setRange(0.000, 100.000)
        self.rate.setDecimals(3)
        self.rate.setSingleStep(0.010)
        self.rate.setValue(680/500)            # ✅ 1.36
        self.rate.setKeyboardTracking(False)

        # cal_sel
        self.cal_start = QSpinBox()
        self.cal_end   = QSpinBox()
        for sb in (self.cal_start, self.cal_end):
            sb.setRange(0, 100000)
        self.cal_start.setValue(350)
        self.cal_end.setValue(400)

        # ▶︎ 排版：带上标签，紧凑在一行里
        recon_grid = QGridLayout()
        recon_grid.setHorizontalSpacing(8)
        recon_grid.setVerticalSpacing(2)
        recon_grid.setContentsMargins(5, 2, 5, 2)

        # 第一行：勾选框 + pos_step + rate
        recon_grid.addWidget(self.show_recon, 0, 0, 1, 2)
        recon_grid.addWidget(QLabel("pos_step(mm):"), 0, 2)
        recon_grid.addWidget(self.pos_step, 0, 3)
        recon_grid.addWidget(QLabel("rate:"), 0, 4)
        recon_grid.addWidget(self.rate, 0, 5)

        # 第二行：cal_sel 起止范围
        recon_grid.addWidget(QLabel("cal_sel(mm):"), 1, 2)
        recon_grid.addWidget(self.cal_start, 1, 3)
        recon_grid.addWidget(QLabel("~"), 1, 4)
        recon_grid.addWidget(self.cal_end, 1, 5)

        # 添加到主布局
        plot_layout.addLayout(recon_grid, 1, 0, 1, 6)

        # 3️⃣ Sum(Y)
        self.show_sumy = QCheckBox("Sum(Y) 曲线")
        self.show_sumy.setChecked(True)
        self.sumy_start = QSpinBox(); self.sumy_start.setRange(0, 2048); self.sumy_start.setValue(2)
        self.sumy_end = QSpinBox(); self.sumy_end.setRange(0, 2048); self.sumy_end.setValue(120)
        sumy_layout = QHBoxLayout()
        sumy_layout.addWidget(self.show_sumy)
        sumy_layout.addWidget(QLabel("idx:"))
        sumy_layout.addWidget(self.sumy_start)
        sumy_layout.addWidget(QLabel("~"))
        sumy_layout.addWidget(self.sumy_end)
        plot_layout.addLayout(sumy_layout, 2, 0, 1, 6)

        # 4️⃣ TotalSum
        self.show_totalsum = QCheckBox("TotalSum 曲线")
        self.show_totalsum.setChecked(True)
        self.tot_start = QSpinBox(); self.tot_start.setRange(0, 2048); self.tot_start.setValue(2)
        self.tot_end = QSpinBox(); self.tot_end.setRange(0, 2048); self.tot_end.setValue(120)
        total_layout = QHBoxLayout()
        total_layout.addWidget(self.show_totalsum)
        total_layout.addWidget(QLabel("idx:"))
        total_layout.addWidget(self.tot_start)
        total_layout.addWidget(QLabel("~"))
        total_layout.addWidget(self.tot_end)
        plot_layout.addLayout(total_layout, 3, 0, 1, 6)

        plot_group.setLayout(plot_layout)
        layout.addWidget(plot_group)

        # === 绘图按钮 ===
        self.btn_plot = QPushButton("显示图像")
        layout.addWidget(self.btn_plot)

        self.setLayout(layout)

        # === 事件绑定 ===
        self.dir_btn.clicked.connect(self.select_dir)
        self.btn_start.clicked.connect(self.start_acquisition)
        self.btn_plot.clicked.connect(self.show_plots)

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

        # --- 参数 ---
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

        # --- 文件存在检查 ---
        if os.path.exists(file_path):
            self.log_box.append(f"[WARN] 文件 {file_name} 已存在，采集终止。")
            return

        # --- 采集 ---
        self.log_box.append(f"[INFO] 开始采集：{file_name}")
        self.acq_ctrl.acquire(file_path, v, a, (f1, f2), s, dur, inter, win, self._on_log_update)

    # ------------------------------------------------------------
    def _on_log_update(self, level, message):
        """采集状态更新"""
        self.log_box.append(f"{level} {message}")

    # ------------------------------------------------------------
    def show_plots(self):
        """显示采集结果的图像（弹窗形式）"""
        if not hasattr(self.acq_ctrl, "last_data") or self.acq_ctrl.last_data is None:
            self.log_box.append("[WARN] 没有可显示的数据，请先采集。")
            return

        data = self.acq_ctrl.last_data
        histData = np.transpose(data["data"], (2, 1, 0))

        plt.figure(figsize=(10,10))
        # === 帧数据 ===
        if self.show_frame.isChecked():
            ax = plt.subplot(221)
            # np.transpose(data["data"], (2, 1, 0))
            ax.imshow(histData.sum(axis=0), aspect="auto")
            ax.set_title(f"Frame data")

        # === Naive 重建 ===
        if self.show_recon.isChecked():
            pos_step = self.pos_step.value()
            rate = self.rate.value()
            cal_sel = (self.cal_start.value(), self.cal_end.value())
            pos = np.arange(histData.shape[2]) * pos_step

            pos_sel = np.where((cal_sel[0] <= pos) & (pos < cal_sel[1]))[0]
            cal_den = histData[:, :, pos_sel].sum(axis=2)
            cal_num = cal_den.mean(axis=1)[:, None]
            cal_num = np.where(cal_num == 0, 1, cal_num)
            cal_den = np.where(cal_den == 0, cal_num, cal_den)
            cal = (cal_num / cal_den)[:, :, None]
            img = (histData.astype(np.float64) * cal).sum(axis=0).T

            (x, y, img) = _show(img, pos, rate, log_en=False)

            ax = plt.subplot(222)
            ax.set_title("Naive Reconstruction")
            ax.imshow(img, extent=[x.min(), x.max(), y.min(), y.max()],
                       cmap="gray", origin="lower", aspect="equal")
            ax.set_xlabel("Width (mm)")
            ax.set_ylabel("Position (mm)")
        
        # === 3️⃣ Sum(Y) ===
        if self.show_sumy.isChecked():
            s, e = self.sumy_start.value(), self.sumy_end.value()
            ax = plt.subplot(223)
            y_data = data["data"].sum(axis=0)[:, s:e]
            ax.plot(np.arange(data["data"].sum(axis=0).shape[1])[s:e], y_data.T)
            ax.set_title(f"Sum(Y)  idx[{s}:{e}]")

        # === 4️⃣ TotalSum ===
        if self.show_totalsum.isChecked():
            s, e = self.tot_start.value(), self.tot_end.value()
            ax = plt.subplot(224)
            y_data = data["data"].sum(axis=0)[:, s:e].sum(axis=1)
            ax.plot(y_data.T)
            ax.set_title(f"Total Sum  idx[{s}:{e}]")
        
        plt.show()
        # plt.show(block=False)  # 非阻塞显示
        # # print("\n📊 图像已显示，按任意键退出窗口...")
        # input()  # 等待键盘输入
        # plt.close('all')