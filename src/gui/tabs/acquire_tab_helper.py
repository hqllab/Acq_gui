import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QTextEdit, QLabel, QRadioButton, QButtonGroup,
    QDoubleSpinBox, QSpinBox, QFrame, QLineEdit, 
    QPushButton, QFileDialog
)

def get_group_style():
    return "QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid gray; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }"

def get_sub_group_style():
    """内部子模块样式"""
    return "QGroupBox { font-weight: normal; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; margin-top: 8px; background-color: #f9f9f9; } QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 2px; }"

def create_motion_block():
    """1. 运动控制模块"""
    group_box = QGroupBox("运动参数")
    group_box.setStyleSheet(get_group_style())
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

    start_pos = create_double_spin(0.0, "mm")
    end_pos = create_double_spin(100.0, "mm")
    speed = create_double_spin(100.0, "mm/s")

    controls_h_layout.addWidget(QLabel("起始位置:"))
    controls_h_layout.addWidget(start_pos)
    controls_h_layout.addWidget(QLabel("终点位置:"))
    controls_h_layout.addWidget(end_pos)
    controls_h_layout.addWidget(QLabel("运动速度:"))
    controls_h_layout.addWidget(speed)
    controls_h_layout.addStretch()

    note_label = QLabel("※ 备注: 位置表示距离顶端的距离")
    note_label.setStyleSheet("color: #666666; font-size: 12px; font-style: italic;")

    main_v_layout.addLayout(controls_h_layout)
    main_v_layout.addWidget(note_label)
    group_box.setLayout(main_v_layout)
    # return group_box, start_pos, end_pos, speed

    return {
        "group_box": group_box,
        "start_pos": start_pos,
        "end_pos": end_pos,
        "speed": speed,
    }

def create_channel_panel(title):
    """创建采集通道面板（正位/侧位）"""
    main_panel = QGroupBox(title)
    main_panel.setStyleSheet(get_group_style())
    layout = QVBoxLayout()
    layout.setContentsMargins(10, 25, 10, 10)
    layout.setSpacing(12)

    # --- 1. 球管控制 ---
    tube_group = QGroupBox("球管控制")
    tube_group.setStyleSheet(get_sub_group_style())
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
    acq_group.setStyleSheet(get_sub_group_style())
    acq_v_layout = QVBoxLayout()
    acq_v_layout.setSpacing(5)

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
    spectral_max.setValue(100)
    spectral_layout.addWidget(spectral_max)
    acq_v_layout.addWidget(spectral_group)

    # -----------------------
    # 合并能窗范围 (四个上下限)
    # -----------------------
    binned_group = QGroupBox("合并能窗范围")
    binned_layout = QVBoxLayout(binned_group)
    binned_spinboxes = []
    default_win = [
        [0, 30],
        [40, 80],
        [15, 60],
        [0, 100]
    ]
    for i, win in enumerate(default_win):
        row = QHBoxLayout()
        row.addWidget(QLabel(f"窗{i+1}下限:"))
        min_spin = QSpinBox()
        min_spin.setRange(0, 120)
        min_spin.setValue(win[0])
        row.addWidget(min_spin)
        row.addWidget(QLabel(f"窗{i+1}上限:"))
        max_spin = QSpinBox()
        max_spin.setRange(0, 120)
        max_spin.setValue(win[1])
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
    radio_sync = QRadioButton("运动同步"); 
    radio_fixed = QRadioButton("固定时长"); 
    # radio_sync.setEnabled(False) 
    # radio_sync.setChecked(True)
    fixed_duration_spin = QDoubleSpinBox()
    fixed_duration_spin.setRange(0.1, 100.0); fixed_duration_spin.setSuffix(" s")
    fixed_duration_spin.setValue(6.0); fixed_duration_spin.setFixedWidth(90); 
    radio_fixed.setChecked(True)
    
    mode_group = QButtonGroup(main_panel)
    mode_group.addButton(radio_sync)
    mode_group.addButton(radio_fixed)
    mode_opt_row.addWidget(radio_sync); mode_opt_row.addSpacing(15)
    mode_opt_row.addWidget(radio_fixed); mode_opt_row.addWidget(fixed_duration_spin); mode_opt_row.addStretch()
    acq_v_layout.addLayout(mode_opt_row)

    time_row = QHBoxLayout()
    time_spin = QDoubleSpinBox()
    time_spin.setRange(0.5, 100.0); time_spin.setSuffix(" ms"); time_spin.setValue(10.0)
    time_row.addWidget(QLabel("FrameTime:"))
    time_row.addWidget(time_spin); time_row.addStretch()
    acq_v_layout.addLayout(time_row)
    acq_group.setLayout(acq_v_layout)

    # --- 3. 重建参数 ---
    recon_group = QGroupBox("重建参数")
    recon_group.setStyleSheet(get_sub_group_style())
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
        "radio_sync": radio_sync, 
        "radio_fixed": radio_fixed,
        "fixed_duration": fixed_duration_spin, "frame_time": time_spin, 
        "sid": sid_spin, "sdd": sdd_spin
    }


def create_execution_block():
    """3. 采集执行与保存模块"""
    group_box = QGroupBox("采集执行控制")
    group_box.setStyleSheet(get_group_style())
    layout = QVBoxLayout()
    layout.setContentsMargins(15, 25, 15, 15)

    # 保存目录
    row_dir = QHBoxLayout()
    row_dir.addWidget(QLabel("保存目录:"))
    dir_edit = QLineEdit(os.getcwd())
    browse_btn = QPushButton("浏览...")
    browse_btn.setFixedWidth(70)
    row_dir.addWidget(dir_edit)
    row_dir.addWidget(browse_btn)
    layout.addLayout(row_dir)

    # 文件前缀
    row_prefix = QHBoxLayout()
    row_prefix.addWidget(QLabel("文件前缀:"))
    prefix_edit = QLineEdit("ScanTask_001")
    row_prefix.addWidget(prefix_edit)
    row_prefix.addStretch()
    layout.addLayout(row_prefix)

    # 路径预览
    preview_box = QFrame()
    preview_box.setStyleSheet("background-color: #f4f4f4; border: 1px dashed #bbb; border-radius: 4px;")
    preview_v = QVBoxLayout(preview_box)
    cor_preview_label = QLabel("正位路径: -")
    sag_preview_label = QLabel("侧位路径: -")
    # 使用等宽字体方便阅读路径
    preview_style = "color: #2c3e50; font-family: 'Consolas', monospace; font-size: 11px;"
    cor_preview_label.setStyleSheet(preview_style)
    sag_preview_label.setStyleSheet(preview_style)
    preview_v.addWidget(cor_preview_label)
    preview_v.addWidget(sag_preview_label)
    layout.addWidget(preview_box)

    # 发送球管参数按钮
    init_btn = QPushButton("设置采集范围&球管参数")
    init_btn.setFixedHeight(45)
    init_btn.setStyleSheet("""
        QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 5px; }
        QPushButton:hover { background-color: #2ecc71; }
        QPushButton:pressed { background-color: #1e8449; }
    """)
    layout.addWidget(init_btn)

    # 采集按钮
    start_btn = QPushButton("开始采集 (Start Acquisition)")
    start_btn.setFixedHeight(45)
    start_btn.setStyleSheet("""
        QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 5px; }
        QPushButton:hover { background-color: #2ecc71; }
        QPushButton:pressed { background-color: #1e8449; }
    """)
    layout.addWidget(start_btn)

    group_box.setLayout(layout)
    return {
        "group_box": group_box,
        "init_btn": init_btn,
        "start_btn": start_btn,
        "browse_btn": browse_btn,
        "dir_edit": dir_edit,
        "prefix_edit": prefix_edit,
        "cor_preview_label": cor_preview_label,
        "sag_preview_label": sag_preview_label,
    }


def create_execution_block_exam():
    """3. 采集执行与保存模块"""
    group_box = QGroupBox("采集执行控制")
    group_box.setStyleSheet(get_group_style())
    layout = QVBoxLayout()
    layout.setContentsMargins(15, 25, 15, 15)

    # 保存目录
    row_dir = QHBoxLayout()
    row_dir.addWidget(QLabel("保存目录:"))
    dir_edit = QLineEdit(os.getcwd())
    browse_btn = QPushButton("浏览...")
    browse_btn.setFixedWidth(70)
    row_dir.addWidget(dir_edit)
    row_dir.addWidget(browse_btn)
    layout.addLayout(row_dir)

    # 文件前缀
    row_prefix = QHBoxLayout()
    row_prefix.addWidget(QLabel("文件前缀:"))
    prefix_edit = QLineEdit("ScanTask_001")
    row_prefix.addWidget(prefix_edit)
    row_prefix.addStretch()
    layout.addLayout(row_prefix)

    # 路径预览
    preview_box = QFrame()
    preview_box.setStyleSheet("background-color: #f4f4f4; border: 1px dashed #bbb; border-radius: 4px;")
    preview_v = QVBoxLayout(preview_box)
    cor_preview_label = QLabel("正位路径: -")
    sag_preview_label = QLabel("侧位路径: -")
    # 使用等宽字体方便阅读路径
    preview_style = "color: #2c3e50; font-family: 'Consolas', monospace; font-size: 11px;"
    cor_preview_label.setStyleSheet(preview_style)
    sag_preview_label.setStyleSheet(preview_style)
    preview_v.addWidget(cor_preview_label)
    preview_v.addWidget(sag_preview_label)
    layout.addWidget(preview_box)

    # # 发送球管参数按钮
    # init_btn = QPushButton("设置采集范围&球管参数")
    # init_btn.setFixedHeight(45)
    # init_btn.setStyleSheet("""
    #     QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 5px; }
    #     QPushButton:hover { background-color: #2ecc71; }
    #     QPushButton:pressed { background-color: #1e8449; }
    # """)
    # layout.addWidget(init_btn)

    # 采集按钮
    start_btn = QPushButton("开始采集 (Start Acquisition)")
    start_btn.setFixedHeight(45)
    start_btn.setStyleSheet("""
        QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 5px; }
        QPushButton:hover { background-color: #2ecc71; }
        QPushButton:pressed { background-color: #1e8449; }
    """)
    layout.addWidget(start_btn)

    group_box.setLayout(layout)
    return {
        "group_box": group_box,
        # "init_btn": init_btn,
        "start_btn": start_btn,
        "browse_btn": browse_btn,
        "dir_edit": dir_edit,
        "prefix_edit": prefix_edit,
        "cor_preview_label": cor_preview_label,
        "sag_preview_label": sag_preview_label,
    }