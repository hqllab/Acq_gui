# gui/tabs/acquire_tab.py

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QTextEdit, QLabel, QRadioButton, QButtonGroup,
    QDoubleSpinBox, QSpinBox, QFrame, QLineEdit, 
    QPushButton, QFileDialog
)
from PySide6.QtCore import Qt, QSettings
from gui.func import write_log
import time

class AcquireTab(QWidget):
    """采集参数设置与控制界面"""

    def __init__(self, cor_ctrl, sag_ctrl, arm_thread, log_box):
        super().__init__()
        self.settings = QSettings("ScanGUI", "DetectorApp")
        self.cor_ctrl = cor_ctrl
        self.sag_ctrl = sag_ctrl
        self.arm_thread = arm_thread
        self.log_box = log_box
        
        self.initUI()
        self.bind_events()
        # 初始化界面数值逻辑
        self.update_file_preview()

    def _get_group_style(self):
        """主模块样式"""
        return "QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid gray; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }"

    def _get_sub_group_style(self):
        """内部子模块样式"""
        return "QGroupBox { font-weight: normal; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; margin-top: 8px; background-color: #f9f9f9; } QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 2px; }"

    def _create_motion_block(self):
        """1. 运动控制模块"""
        group_box = QGroupBox("运动参数")
        group_box.setStyleSheet(self._get_group_style())
        main_v_layout = QVBoxLayout()
        main_v_layout.setContentsMargins(15, 25, 15, 15)
        
        controls_h_layout = QHBoxLayout()
        def create_double_spin(val, unit):
            spin = QDoubleSpinBox()
            spin.setRange(0, 2000)
            spin.setDecimals(1)
            spin.setValue(val)
            spin.setSuffix(f" {unit}")
            return spin

        self.start_pos = create_double_spin(0.0, "mm")
        self.end_pos = create_double_spin(100.0, "mm")
        self.speed = create_double_spin(10.0, "mm/s")

        controls_h_layout.addWidget(QLabel("起始位置:"))
        controls_h_layout.addWidget(self.start_pos)
        controls_h_layout.addWidget(QLabel("终点位置:"))
        controls_h_layout.addWidget(self.end_pos)
        controls_h_layout.addWidget(QLabel("运动速度:"))
        controls_h_layout.addWidget(self.speed)
        controls_h_layout.addStretch()

        note_label = QLabel("※ 备注: 位置表示距离顶端的距离")
        note_label.setStyleSheet("color: #666666; font-size: 12px; font-style: italic;")

        main_v_layout.addLayout(controls_h_layout)
        main_v_layout.addWidget(note_label)
        group_box.setLayout(main_v_layout)
        return group_box

    def _create_channel_panel(self, title):
        """创建采集通道面板（正位/侧位）"""
        main_panel = QGroupBox(title)
        main_panel.setStyleSheet(self._get_group_style())
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 25, 10, 10)
        layout.setSpacing(12)

        # --- 1. 球管控制 ---
        tube_group = QGroupBox("球管控制")
        tube_group.setStyleSheet(self._get_sub_group_style())
        tube_layout = QHBoxLayout()
        kv_spin = QSpinBox(); kv_spin.setRange(0, 130); kv_spin.setSuffix(" kV")
        ma_spin = QSpinBox(); ma_spin.setRange(0, 200); ma_spin.setSuffix(" mA")
        tube_layout.addWidget(QLabel("电压:"))
        tube_layout.addWidget(kv_spin)
        tube_layout.addWidget(QLabel("电流:"))
        tube_layout.addWidget(ma_spin)
        tube_group.setLayout(tube_layout)

        # --- 2. 采集控制 ---
        acq_group = QGroupBox("采集控制")
        acq_group.setStyleSheet(self._get_sub_group_style())
        acq_v_layout = QVBoxLayout()
        acq_v_layout.setSpacing(5)

        # acq_v_layout.addWidget(QLabel("数据模式:"))
        # data_opt_row = QHBoxLayout()
        # data_opt_row.addSpacing(25)
        # radio_spectral = QRadioButton("能谱")
        # radio_binned = QRadioButton("合并能窗")
        # radio_spectral.setChecked(True)
        # data_group = QButtonGroup(main_panel)
        # data_group.addButton(radio_spectral); data_group.addButton(radio_binned)
        # data_opt_row.addWidget(radio_spectral); data_opt_row.addWidget(radio_binned); data_opt_row.addStretch()
        # acq_v_layout.addLayout(data_opt_row)# 数据模式选择
        acq_v_layout.addWidget(QLabel("数据模式:"))
        data_opt_row = QHBoxLayout()
        data_opt_row.addSpacing(25)

        radio_spectral = QRadioButton("能谱")
        radio_binned = QRadioButton("合并能窗")
        radio_spectral.setChecked(True)

        data_group = QButtonGroup(main_panel)
        data_group.addButton(radio_spectral)
        data_group.addButton(radio_binned)

        data_opt_row.addWidget(radio_spectral)
        data_opt_row.addWidget(radio_binned)
        data_opt_row.addStretch()
        acq_v_layout.addLayout(data_opt_row)

        # -----------------------
        # 能谱范围 (上下限)
        # -----------------------
        spectral_group = QGroupBox("能谱范围")
        spectral_layout = QHBoxLayout(spectral_group)
        spectral_layout.addWidget(QLabel("下限:"))
        spectral_min = QSpinBox()
        spectral_min.setRange(0, 120)
        spectral_layout.addWidget(spectral_min)
        spectral_layout.addWidget(QLabel("上限:"))
        spectral_max = QSpinBox()
        spectral_max.setRange(0, 120)
        spectral_layout.addWidget(spectral_max)
        acq_v_layout.addWidget(spectral_group)

        # -----------------------
        # 合并能窗范围 (四个上下限)
        # -----------------------
        binned_group = QGroupBox("合并能窗范围")
        binned_layout = QVBoxLayout(binned_group)
        binned_spinboxes = []
        for i in range(4):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"窗{i+1}下限:"))
            min_spin = QSpinBox()
            min_spin.setRange(0, 120)
            row.addWidget(min_spin)
            row.addWidget(QLabel(f"窗{i+1}上限:"))
            max_spin = QSpinBox()
            max_spin.setRange(0, 120)
            row.addWidget(max_spin)
            binned_layout.addLayout(row)
            binned_spinboxes.append((min_spin, max_spin))
        acq_v_layout.addWidget(binned_group)

        # 默认显示能谱，隐藏合并能窗
        spectral_group.setVisible(True)
        binned_group.setVisible(False)
        
        def update_mode():
            if radio_spectral.isChecked():
                spectral_group.setVisible(True)
                binned_group.setVisible(False)
            else:
                spectral_group.setVisible(False)
                binned_group.setVisible(True)
        
        radio_spectral.toggled.connect(update_mode)
        radio_binned.toggled.connect(update_mode)

        acq_v_layout.addWidget(QLabel("采集模式:"))
        mode_opt_row = QHBoxLayout()
        mode_opt_row.addSpacing(25)
        radio_sync = QRadioButton("运动同步"); radio_fixed = QRadioButton("固定时长")
        radio_sync.setChecked(True)
        fixed_duration_spin = QDoubleSpinBox()
        fixed_duration_spin.setRange(0.1, 100.0); fixed_duration_spin.setSuffix(" s")
        fixed_duration_spin.setValue(10.0); fixed_duration_spin.setFixedWidth(90); fixed_duration_spin.setEnabled(False) 
        mode_group = QButtonGroup(main_panel)
        mode_group.addButton(radio_sync); mode_group.addButton(radio_fixed)
        mode_opt_row.addWidget(radio_sync); mode_opt_row.addSpacing(15)
        mode_opt_row.addWidget(radio_fixed); mode_opt_row.addWidget(fixed_duration_spin); mode_opt_row.addStretch()
        acq_v_layout.addLayout(mode_opt_row)

        time_row = QHBoxLayout()
        time_spin = QDoubleSpinBox()
        time_spin.setRange(0.5, 100.0); time_spin.setSuffix(" ms"); time_spin.setValue(4.0)
        time_row.addWidget(QLabel("FrameTime:"))
        time_row.addWidget(time_spin); time_row.addStretch()
        acq_v_layout.addLayout(time_row)
        acq_group.setLayout(acq_v_layout)

        # --- 3. 重建参数 ---
        recon_group = QGroupBox("重建参数")
        recon_group.setStyleSheet(self._get_sub_group_style())
        recon_v_layout = QVBoxLayout()
        sid_spin = QDoubleSpinBox(); sid_spin.setRange(0, 5000); sid_spin.setSuffix(" mm")
        sdd_spin = QDoubleSpinBox(); sdd_spin.setRange(0, 5000); sdd_spin.setSuffix(" mm")
        sid_row = QHBoxLayout(); sid_row.addWidget(QLabel("SID:")); sid_row.addWidget(sid_spin); sid_row.addStretch()
        sdd_row = QHBoxLayout(); sdd_row.addWidget(QLabel("SDD:")); sdd_row.addWidget(sdd_spin); sdd_row.addStretch()
        recon_v_layout.addLayout(sid_row); recon_v_layout.addLayout(sdd_row)
        recon_group.setLayout(recon_v_layout)

        layout.addWidget(tube_group); layout.addWidget(acq_group); layout.addWidget(recon_group); layout.addStretch()
        main_panel.setLayout(layout)
        
        return {
            "panel": main_panel, "kv": kv_spin, "ma": ma_spin,
            "radio_spectral": radio_spectral, "radio_binned": radio_binned,
            "spectral": (spectral_min, spectral_max),
            "binned_spinboxes": binned_spinboxes,
            "radio_sync": radio_sync, "radio_fixed": radio_fixed,
            "fixed_duration": fixed_duration_spin, "time": time_spin, 
            "sid": sid_spin, "sdd": sdd_spin
        }

    def _create_execution_block(self):
        """3. 采集执行与保存模块"""
        group_box = QGroupBox("采集执行控制")
        group_box.setStyleSheet(self._get_group_style())
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 25, 15, 15)

        # 保存目录
        row_dir = QHBoxLayout()
        row_dir.addWidget(QLabel("保存目录:"))
        self.dir_edit = QLineEdit(os.getcwd())
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setFixedWidth(70)
        row_dir.addWidget(self.dir_edit)
        row_dir.addWidget(self.browse_btn)
        layout.addLayout(row_dir)

        # 文件前缀
        row_prefix = QHBoxLayout()
        row_prefix.addWidget(QLabel("文件前缀:"))
        self.prefix_edit = QLineEdit("ScanTask_001")
        row_prefix.addWidget(self.prefix_edit)
        row_prefix.addStretch()
        layout.addLayout(row_prefix)

        # 路径预览
        preview_box = QFrame()
        preview_box.setStyleSheet("background-color: #f4f4f4; border: 1px dashed #bbb; border-radius: 4px;")
        preview_v = QVBoxLayout(preview_box)
        self.cor_preview_label = QLabel("正位路径: -")
        self.sag_preview_label = QLabel("侧位路径: -")
        # 使用等宽字体方便阅读路径
        preview_style = "color: #2c3e50; font-family: 'Consolas', monospace; font-size: 11px;"
        self.cor_preview_label.setStyleSheet(preview_style)
        self.sag_preview_label.setStyleSheet(preview_style)
        preview_v.addWidget(self.cor_preview_label)
        preview_v.addWidget(self.sag_preview_label)
        layout.addWidget(preview_box)

        # 采集按钮
        self.start_btn = QPushButton("开始采集 (Start Acquisition)")
        self.start_btn.setFixedHeight(45)
        self.start_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 5px; }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:pressed { background-color: #1e8449; }
        """)
        layout.addWidget(self.start_btn)

        group_box.setLayout(layout)
        return group_box

    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # 1. 运动控制
        main_layout.addWidget(self._create_motion_block())

        # 2. 正位与侧位通道
        channels_layout = QHBoxLayout()
        self.cor_ui = self._create_channel_panel("正位 (COR)")
        self.sag_ui = self._create_channel_panel("侧位 (SAG)")
        channels_layout.addWidget(self.cor_ui["panel"])
        channels_layout.addWidget(self.sag_ui["panel"])
        main_layout.addLayout(channels_layout)
        
        # 3. 采集执行模块
        main_layout.addWidget(self._create_execution_block())

        # # 4. 系统日志
        # log_group = QGroupBox("系统日志")
        # log_group.setStyleSheet(self._get_group_style())
        # log_v = QVBoxLayout()
        # # self.log_box = QTextEdit()
        # # self.log_box.setReadOnly(True)
        # log_v.addWidget(self.log_box)
        # log_group.setLayout(log_v)
        # main_layout.addWidget(log_group, stretch=1)

    def select_directory(self):
        """选择文件夹"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.dir_edit.text())
        if dir_path:
            self.dir_edit.setText(dir_path)

    def _update_frametime_range(self, ui_dict):
        """根据能谱/合并能窗模式切换 FrameTime 范围"""
        is_spectral = ui_dict["radio_spectral"].isChecked()
        if is_spectral:
            # 能谱模式: 4.0ms - 100ms
            ui_dict["time"].setMinimum(4.0)
            if ui_dict["time"].value() < 4.0:
                ui_dict["time"].setValue(4.0)
        else:
            # 合并能窗: 0.5ms - 100ms
            ui_dict["time"].setMinimum(0.5)

    def update_file_preview(self):
        """实时更新文件路径预览"""
        save_dir = self.dir_edit.text()
        prefix = self.prefix_edit.text()
        speed = self.speed.value()

        def generate_path(ui, suffix):
            # 逻辑：能谱 -> cali, 合并能窗 -> recon
            mode_tag = "cali" if ui["radio_spectral"].isChecked() else "recon"
            filename = (f"{prefix}_{speed}mmps_{ui['kv'].value()}kv_{ui['ma'].value()}ma_"
                        f"{mode_tag}_{ui['time'].value()}ms_{ui['sid'].value()}mm_{suffix}.mat")
            return os.path.join(save_dir, filename)

        self.cor_save_path = generate_path(self.cor_ui, "cor")
        self.sag_save_path = generate_path(self.sag_ui, "sag")
        
        self.cor_preview_label.setText(f"正位路径: {self.cor_save_path}")
        self.sag_preview_label.setText(f"侧位路径: {self.sag_save_path}")

    def bind_events(self):
        """绑定 UI 事件"""
        # 1. 目录浏览
        self.browse_btn.clicked.connect(self.select_directory)

        # 2. 采集模式联动 (固定时长输入框开关)
        self.cor_ui["radio_fixed"].toggled.connect(lambda checked: self.cor_ui["fixed_duration"].setEnabled(checked))
        self.sag_ui["radio_fixed"].toggled.connect(lambda checked: self.sag_ui["fixed_duration"].setEnabled(checked))

        # 3. 数据模式联动 (FrameTime 范围限制)
        self.cor_ui["radio_spectral"].toggled.connect(lambda: self._update_frametime_range(self.cor_ui))
        self.sag_ui["radio_spectral"].toggled.connect(lambda: self._update_frametime_range(self.sag_ui))

        # 4. 路径预览联动 (所有相关控件变化时触发预览更新)
        # 基础信息
        self.dir_edit.textChanged.connect(self.update_file_preview)
        self.prefix_edit.textChanged.connect(self.update_file_preview)
        self.speed.valueChanged.connect(self.update_file_preview)
        
        # 通道参数
        for ui in [self.cor_ui, self.sag_ui]:
            ui["kv"].valueChanged.connect(self.update_file_preview)
            ui["ma"].valueChanged.connect(self.update_file_preview)
            ui["time"].valueChanged.connect(self.update_file_preview)
            ui["sid"].valueChanged.connect(self.update_file_preview)
            ui["radio_spectral"].toggled.connect(self.update_file_preview)

        # 5. 初始化参数默认值
        for ui in [self.cor_ui, self.sag_ui]:
            ui["kv"].setValue(80)
            ui["ma"].setValue(10)
            ui["sid"].setValue(1000)
            ui["sdd"].setValue(1400)
            self._update_frametime_range(ui) # 初始化范围限制
        
        # 6. 绑定采集
        self.start_btn.clicked.connect(self.start_acq_pipeline)
        
    def start_acq_pipeline(self):
        if self.cor_ctrl is None or self.cor_ctrl.det is None or self.cor_ctrl.offline:
            write_log(self.log_box, "[Error] 错误：未连接正位[COR]探测器，无法采集！")
            return
        
        if self.sag_ctrl is None or self.sag_ctrl.det is None or self.sag_ctrl.offline:
            write_log(self.log_box, "[Error] 错误：未连接侧位[SAG]探测器，无法采集！")
            return
        
        if self.arm_thread is None or not self.arm_thread.isRunning():
            write_log(self.log_box, "[Error] 错误：机械臂未连接，无法采集！")
            return
        
        write_log(self.log_box, "[Info] 开始采集...")
        
        # 第一步, 生成script.txt 文件, 设置 机械臂参数 和 电压电流参数
        cmds = []
        cmds.append(f"exit_exposure_mode")
        cmds.append(f"allow_exposure 1")
        # cmds.append(f"set_max_exposure_time 0 9000")
        # cmds.append(f"set_max_exposure_time 1 9000")
        
        # 球管B -> 正位
        cmds.append(f"set_voltage 0 {self.sag_ui['kv'].value()}")   
        cmds.append(f"set_current 0 {self.sag_ui['ma'].value()}")
        # 球管A -> 侧位
        cmds.append(f"set_voltage 1 {self.cor_ui['kv'].value()}")
        cmds.append(f"set_current 1 {self.cor_ui['ma'].value()}")
        
        # 机械臂位置
        cmds.append(f"move {int(self.start_pos.value()*10)} {2000}")
        cmds.append(f"set_exposure_pos {int(self.end_pos.value()*10)} {int(self.speed.value()*10)}")
        cmds.append(f"enter_exposure_mode")
        
        for cmd in cmds:
            self.arm_thread.send_command(cmd)
            time.sleep(0.05)
            
            if "move" in cmd:
                time.sleep(0.4)
                
            write_log(self.log_box, f"[Info] 发送指令: {cmd}")
        
        cor_acq_mode = "spectral" if self.cor_ui["radio_spectral"].isChecked() else "binned"
        cor_win_range = []
        if cor_acq_mode == "spectral":
            cor_win_range = (self.cor_ui["spectral_min"].value(), self.cor_ui["spectral_max"].value())
        else:
            for min_spin, max_spin in self.cor_ui["binned_spinboxes"]:
                cor_win_range.append( (min_spin.value(), max_spin.value()) )
        if os.path.exists(self.cor_save_path):
            write_log(self.log_box, f"[Error]: {self.cor_save_path} 文件已存在！")
            return
        self.cor_ctrl.start_acquire(
            acq_mode = cor_acq_mode,
            win_range = cor_win_range,
            time = self.cor_ui["time"].value(),
            interval = self.cor_ui["interval"].value(),
            filepath = self.cor_save_path,
        )
        
        sag_acq_mode = "spectral" if self.sag_ui["radio_spectral"].isChecked() else "binned"
        sag_win_range = []
        if sag_acq_mode == "spectral":
            sag_win_range = (self.sag_ui["spectral_min"].value(), self.sag_ui["spectral_max"].value())
        else:
            for min_spin, max_spin in self.sag_ui["binned_spinboxes"]:
                sag_win_range.append( (min_spin.value(), max_spin.value()) )
        if os.path.exists(self.sag_save_path):
            write_log(self.log_box, f"[Error]: {self.sag_save_path} 文件已存在！")
            return
        self.sag_ctrl.start_acquire(
            acq_mode = sag_acq_mode,
            win_range = sag_win_range,
            time = self.sag_ui["time"].value(),
            interval = self.sag_ui["interval"].value(),
            filepath = self.sag_save_path,
        )
        
        
        