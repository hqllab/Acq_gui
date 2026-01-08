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
import h5py
from core.func import shift_data


class CaliAcquireTab(QWidget):
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
        grid.addWidget(QLabel("采集时长 (s)"), row, 0)
        self.duration = QSpinBox(); self.duration.setRange(1, 999); self.duration.setValue(8); self.duration.setFixedWidth(w_input)
        grid.addWidget(self.duration, row, 1)

        row += 1
        grid.addWidget(QLabel("采样间隔 (ms)"), row, 0)
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
        grid.addWidget(QLabel("保存文件目录"), row, 0)
        self.dir_edit = QLineEdit(os.path.join(os.getcwd(), "AcqData"))
        self.dir_edit.setFixedWidth(260)
        self.dir_btn = QPushButton("选择目录"); self.dir_btn.setFixedWidth(80)
        hb_dir = QHBoxLayout()
        hb_dir.addWidget(self.dir_edit); hb_dir.addWidget(self.dir_btn)
        grid.addLayout(hb_dir, row, 1)
        layout.addLayout(grid)
        
        # === 命名提示 ===
        row += 1
        tip = QLabel("推荐命名包含：电压 / 电流 / 扫描速度 SO/SD 等关键信息")
        tip.setStyleSheet("color: gray; font-size: 11px;")
        grid.addWidget(tip, row, 0, 1, 2)   # 跨两列显示
        
        # === 自定义名称 ===
        row += 1
        grid.addWidget(QLabel("前缀名"), row, 0)
        self.name = QLineEdit("xxkeV_xxmA_xxmmps_xxso_testxx")
        grid.addWidget(self.name, row, 1)

        row += 1
        grid.addWidget(QLabel("当前文件名"), row, 0)
        self.filename_label = QLabel("")
        self.filename_label.setStyleSheet("color: blue;")   # 可改颜色
        grid.addWidget(self.filename_label, row, 1)
        
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
        plot_layout.addWidget(self.show_frame, 0, 0)

        # ================= Naive Recon 参数区 =================

        # 勾选框
        self.show_recon = QCheckBox("Naive Recon")
        self.show_recon.setChecked(True)

        # pixel_shift
        self.pixel_shift = QSpinBox()
        self.pixel_shift.setRange(-1000, 1000)
        self.pixel_shift.setValue(13)
        self.pixel_shift.setSingleStep(1)
        self.pixel_shift.setKeyboardTracking(False)

        # norm range
        self.norm_start = QSpinBox()
        self.norm_start.setRange(0, 2048)
        self.norm_start.setValue(0)

        self.norm_end = QSpinBox()
        self.norm_end.setRange(0, 2048)
        self.norm_end.setValue(0)

        # 布局
        recon_grid = QGridLayout()
        recon_grid.setHorizontalSpacing(8)
        recon_grid.setVerticalSpacing(2)
        recon_grid.setContentsMargins(5, 2, 5, 2)

        # 一行布局：Naive Recon | pixel_shift | norm_start ~ norm_end
        recon_grid.addWidget(self.show_recon, 0, 0, 1, 2)
        recon_grid.addWidget(QLabel("pixel_shift(px):"), 0, 2)
        recon_grid.addWidget(self.pixel_shift, 0, 3)

        recon_grid.addWidget(QLabel("board norm idx:"), 0, 4)
        recon_grid.addWidget(self.norm_start, 0, 5)
        recon_grid.addWidget(QLabel("~"), 0, 6)
        recon_grid.addWidget(self.norm_end, 0, 7)

        # 加入绘图区（注意列宽要 >= 8）
        plot_layout.addLayout(recon_grid, 1, 0, 1, 8)

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

        self.name.textChanged.connect(self._update_filename)
        self.duration.valueChanged.connect(self._update_filename)
        self.interval.valueChanged.connect(self._update_filename)
        
        self.dir_edit.textChanged.connect(self._update_filename)
        # 初始化显示
        self._update_filename()
        
        
    def _update_filename(self):
        name = self.name.text().strip()
        dur = self.duration.value()
        inter = self.interval.value()

        if not name:
            filename = "(未命名)"
        else:
            filename = f"{name}_{dur}s_{inter}ms_cali.mat"

        self.filename_label.setText(filename)
    
    # ------------------------------------------------------------
    def select_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存路径")
        if folder:
            self.dir_edit.setText(folder)
            self.log_box.append(f"[INFO] 保存路径：{folder}")
            self._update_filename()   # ✅ 强制刷新路径关联状态

    # ------------------------------------------------------------
    def start_acquisition(self):
        if self.det_ctrl is None or self.det_ctrl.offline:
            self.log_box.append("[ERROR] 当前未连接探测器，请先在“连接”界面建立连接。")
            return

        # --- 参数 ---
        save_dir = self.dir_edit.text().strip()
        os.makedirs(save_dir, exist_ok=True)

        # --- 文件名 ---
        file_name = self.filename_label.text().strip()
        file_path = os.path.join(save_dir, file_name)

        # --- 文件存在检查 ---
        if os.path.exists(file_path):
            self.log_box.append(f"[WARN] 文件 {file_name} 已存在，采集终止。")
            return

        dur = self.duration.value()
        inter = self.interval.value()
        win = (self.win_id.value(), self.win_low.value(), self.win_high.value())
        # --- 采集 ---
        self.log_box.append(f"[INFO] 开始采集：{file_name}")
        self.acq_ctrl.acquire(file_path, dur, inter, win, self._on_log_update)

    # ------------------------------------------------------------
    def _on_log_update(self, level, message):
        """采集状态更新"""
        self.log_box.append(f"{level} {message}")

    # ------------------------------------------------------------
    def show_plots(self):
        """从磁盘读取文件并显示图像"""
        save_dir = self.dir_edit.text().strip()
        filename = self.filename_label.text().strip()
        file_path = os.path.join(save_dir, filename)

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "文件不存在", f"未找到数据文件:\n{file_path}")
            return

        
        from core.func import load_mat_from_file
        raw_pos, raw_data = load_mat_from_file(file_path)

        plt.figure(figsize=(10,10))
        # === 帧数据 ===
        if self.show_frame.isChecked():
            ax = plt.subplot(221)
            raw_recon = raw_data.sum(axis=2)
            im = ax.imshow(raw_recon.T, aspect="auto", cmap="gray")
            plt.colorbar(im, ax=ax)
            ax.set_title(f"Frame data")

        # === Naive 重建 ===
        if self.show_recon.isChecked():
            raw_recon = raw_data.sum(axis=2)
            offset_pixel = self.pixel_shift.value()
            
            # from xray.func.preprocess import shift_data
            shifted_recon = shift_data(raw_recon, offset_pixel=offset_pixel)
            
            norm_start = self.norm_start.value()
            norm_end = self.norm_end.value()
            if norm_start == 0 or norm_end == 0:
                normed_recon = shifted_recon
            else:
                norm_factors = shifted_recon[norm_start:norm_end].mean()/shifted_recon[norm_start:norm_end].mean(axis=0)
                normed_recon = shifted_recon * norm_factors
            ax = plt.subplot(222)
            ax.set_title("Naive Reconstruction")
            im = ax.imshow(normed_recon.T, cmap="gray", aspect="auto")
            plt.colorbar(im, ax=ax)
            ax.set_xlabel("Frame Index")
            ax.set_ylabel("Pixel Index")
        
        # === 3️⃣ Sum(Y) ===
        if self.show_sumy.isChecked():
            s, e = self.sumy_start.value(), self.sumy_end.value()
            y_data = raw_data.sum(axis=0)[:, s:e]
            
            ax = plt.subplot(223)
            ax.plot(y_data.T)
            ax.set_title(f"Sum(Y)  idx[{s}:{e}]")

        # === 4️⃣ TotalSum ===
        if self.show_totalsum.isChecked():
            y_data = raw_data.sum(axis=(0,2))
            
            ax = plt.subplot(224)
            ax.plot(y_data)
            ax.set_title(f"Total Sum")
        
        plt.show()