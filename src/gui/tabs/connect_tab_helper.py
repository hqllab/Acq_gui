'''
Author: LiuSheng
Date: 2026-01-13 11:46:57
LastEditTime: 2026-01-16 12:12:04
Description: 
'''
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QDoubleSpinBox

def get_group_style():
    return "QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid gray; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }"


def create_detector_block(title, ip, port):
    # --- 外层容器 (GroupBox) ---
        group_box = QGroupBox(title)
        # 给 GroupBox 加一点样式，让标题更明显
        group_box.setStyleSheet(get_group_style())
        
        # 垂直布局，用于垂直排列 4 行内容
        v_layout = QVBoxLayout()
        v_layout.setSpacing(10) # 行间距
        v_layout.setContentsMargins(15, 25, 15, 15) # 设置边距，上方留出标题位置

        # ====================
        # 第一行: IP 和 Port
        # ====================
        row1 = QHBoxLayout()
        
        ip_label = QLabel("网口IP:")
        ip_edit = QLineEdit()
        ip_edit.setPlaceholderText("IP")
        ip_edit.setText(ip)
        
        port_label = QLabel("端口:")
        port_edit = QLineEdit()
        port_edit.setPlaceholderText("Port")
        port_edit.setFixedWidth(80)
        port_edit.setText(port)

        row1.addWidget(ip_label)
        row1.addWidget(ip_edit)
        row1.addSpacing(20) # 增加间距
        row1.addWidget(port_label)
        row1.addWidget(port_edit)
        
        v_layout.addLayout(row1)

        # ====================
        # 第二行: 连接 和 状态
        # ====================
        row2 = QHBoxLayout()

        connect_btn = QPushButton("连接")
        connect_btn.setMinimumHeight(30) # 按钮稍微高一点
        
        status_label = QLabel("未连接")
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("background-color: #ffe6e6; color: red; padding: 5px;")
        
        row2.addWidget(connect_btn)
        row2.addWidget(status_label)
        
        v_layout.addLayout(row2)

        # ====================
        # 第三行: 功能 (示例)
        # ====================
        row3 = QHBoxLayout()
        func_label = QLabel("功能区域 (预留):")
        # 这里可以放你以后需要的其他功能，暂时放个占位
        # func_btn_example = QPushButton("功能测试")
        
        row3.addWidget(func_label)
        # row3.addWidget(func_btn_example)
        
        v_layout.addLayout(row3)

        # ====================
        # 第四行: 具体指令 (Info, 激光, Clear)
        # ====================
        row4 = QHBoxLayout()
        
        get_info_btn = QPushButton("查询 Info")
        laser_btn = QPushButton("激光控制")
        # clear_pos_btn = QPushButton("Clear Pos")
        # clear_pos_btn.setEnabled(False)  # <--- 禁用：变灰，不可点击

        row4.addWidget(get_info_btn)
        row4.addWidget(laser_btn)
        # row4.addWidget(clear_pos_btn)
        
        v_layout.addLayout(row4)

        # --- 完成 ---
        group_box.setLayout(v_layout)
        
        # 返回所有需要交互的控件，方便外部绑定事件
        return group_box, ip_edit, port_edit, connect_btn, status_label, get_info_btn, laser_btn
    
def create_arm_blocks(ip, ):
    """机械臂控制模块"""
    group_box = QGroupBox("机械臂 (Robotic Arm)")
    group_box.setStyleSheet(get_group_style())
    v_layout = QVBoxLayout()
    v_layout.setSpacing(10)
    v_layout.setContentsMargins(15, 25, 15, 15)

    # --- 第一行: 连接控制 ---
    row1 = QHBoxLayout()
    row1.addWidget(QLabel("IP:"))
    # 默认 IP 与原脚本一致
    ip_edit = QLineEdit(ip) 
    ip_edit.setFixedWidth(120)
    row1.addWidget(ip_edit)
    
    row1.addStretch()
    
    connect_btn = QPushButton("连接")
    connect_btn.setMinimumHeight(30) # 按钮稍微高一点
    connect_btn.setFixedWidth(120) 
    
    status_label = QLabel("未连接")
    status_label.setAlignment(Qt.AlignCenter)
    status_label.setStyleSheet("background-color: #ffe6e6; color: red; padding: 5px;")


    row1.addWidget(connect_btn)
    row1.addWidget(status_label)
    v_layout.addLayout(row1)

    # 分割线
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    v_layout.addWidget(line)

    # --- 第二行: 移动参数 ---
    row2 = QHBoxLayout()
    
    pos_spin = QDoubleSpinBox()
    pos_spin.setRange(-5000, 18500) # 范围放大一点
    pos_spin.setSuffix(" (0.1mm)") # 注意原脚本单位是 0.1mm
    pos_spin.setDecimals(0)
    pos_spin.setFixedWidth(180)
    
    speed_spin = QDoubleSpinBox()
    speed_spin.setRange(0, 2000)
    speed_spin.setValue(1000)
    speed_spin.setSuffix(" (0.1mm/s)")
    speed_spin.setFixedWidth(180)
    
    row2.addWidget(QLabel("位置:"))
    row2.addWidget(pos_spin)
    row2.addWidget(QLabel("速度:"))
    row2.addWidget(speed_spin)
    row2.addStretch()
    
    move_btn = QPushButton("移动(move)")
    move_btn.setEnabled(False) # 默认开启，是否成功由 cmd2 内部逻辑决定
    
    row2.addWidget(move_btn)
    v_layout.addLayout(row2)

    row3 = QHBoxLayout()
    note_label = QLabel("※ 备注: 位置表示距离顶端的距离(单位 0.1mm)")
    note_label.setStyleSheet("color: #666666; font-size: 12px; font-style: italic;")
    row3.addWidget(note_label)
    v_layout.addLayout(row3)
    
    line2 = QFrame()
    line2.setFrameShape(QFrame.HLine)
    line2.setFrameShadow(QFrame.Sunken)
    v_layout.addWidget(line2)

    # --- 第四行: 手动输入命令 (高级功能) ---
    row4 = QHBoxLayout()
    cmd_input = QLineEdit()
    cmd_input.setPlaceholderText("在此输入原始 cmd2 命令，例如: move 11000 2000")
    btn_send_cmd = QPushButton("发送")
    btn_send_cmd.setEnabled(False)  # 默认禁用，连接后启用
    
    row4.addWidget(cmd_input)   
    row4.addWidget(btn_send_cmd)
    v_layout.addLayout(row4)

    group_box.setLayout(v_layout)
    return group_box, ip_edit, connect_btn, status_label, pos_spin, speed_spin, move_btn, cmd_input, btn_send_cmd


def create_exam_motor_blocks(title, ip, port):
    """机械臂控制模块"""
    group_box = QGroupBox(title)
    group_box.setStyleSheet(get_group_style())
    v_layout = QVBoxLayout()
    v_layout.setSpacing(10)
    v_layout.setContentsMargins(15, 25, 15, 15)

    # --- 第一行: 连接控制 ---
    row1 = QHBoxLayout()
    row1.addWidget(QLabel("IP:"))
    # 默认 IP 与原脚本一致
    ip_edit = QLineEdit(ip) 
    ip_edit.setFixedWidth(120)
    row1.addWidget(ip_edit)
    
    row1.addWidget(QLabel("Port:"))
    port_edit = QLineEdit(port) 
    port_edit.setFixedWidth(120)
    row1.addWidget(port_edit)
    
    row1.addStretch()
    
    connect_btn = QPushButton("连接")
    connect_btn.setMinimumHeight(30) # 按钮稍微高一点
    connect_btn.setFixedWidth(120) 
    
    status_label = QLabel("未连接")
    status_label.setAlignment(Qt.AlignCenter)
    status_label.setStyleSheet("background-color: #ffe6e6; color: red; padding: 5px;")


    row1.addWidget(connect_btn)
    row1.addWidget(status_label)
    v_layout.addLayout(row1)

    # 分割线
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    v_layout.addWidget(line)

    # --- 第二行: 移动参数 ---
    row2 = QHBoxLayout()
    
    pos_spin = QDoubleSpinBox()
    pos_spin.setRange(-5000, 18500) # 范围放大一点
    pos_spin.setSuffix(" (0.1mm)") # 注意原脚本单位是 0.1mm
    pos_spin.setDecimals(0)
    pos_spin.setFixedWidth(180)
    
    speed_spin = QDoubleSpinBox()
    speed_spin.setRange(0, 2000)
    speed_spin.setValue(1000)
    speed_spin.setSuffix(" (0.1mm/s)")
    speed_spin.setFixedWidth(180)
    
    row2.addWidget(QLabel("位置:"))
    row2.addWidget(pos_spin)
    row2.addWidget(QLabel("速度:"))
    row2.addWidget(speed_spin)
    row2.addStretch()
    
    move_btn = QPushButton("移动(move)")
    move_btn.setEnabled(False) # 默认开启，是否成功由 cmd2 内部逻辑决定
    
    row2.addWidget(move_btn)
    v_layout.addLayout(row2)

    row3 = QHBoxLayout()
    note_label = QLabel("※ 备注: 位置表示距离顶端的距离(单位 0.1mm)")
    note_label.setStyleSheet("color: #666666; font-size: 12px; font-style: italic;")
    row3.addWidget(note_label)
    v_layout.addLayout(row3)
    
    line2 = QFrame()
    line2.setFrameShape(QFrame.HLine)
    line2.setFrameShadow(QFrame.Sunken)
    v_layout.addWidget(line2)


    group_box.setLayout(v_layout)
    return {
        "group_box": group_box,
        "ip_edit": ip_edit,
        "port_edit": port_edit,
        "connect_btn": connect_btn,
        "status_label": status_label,
        "pos_spin": pos_spin,
        "speed_spin": speed_spin,
        "move_btn": move_btn
    }
