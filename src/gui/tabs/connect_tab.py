# gui/tabs/connect_tab.py

import json
from turtle import title
from unicodedata import name
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QTextEdit, QLabel, QLineEdit,
    QDoubleSpinBox, QFrame
)
from PySide6.QtCore import Qt, QSettings
from core.detector_controller import DetectorController
from core.slz_controller import SLZWorkerThread
from gui.func import write_log


class ConnectTab(QWidget):
    """连接与参数设置界面（仅负责 UI）"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings("ScanGUI", "DetectorApp")
        self.cor_controller = DetectorController()
        self.sag_controller = DetectorController()
        self.arm_thread = None  # 机械臂控制器，稍后初始化
        self.initUI()
        self.bind_events()
        
    
    def _get_group_style(self):
        """统一获取 GroupBox 样式，保持与 ConnectTab 一致"""
        return "QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid gray; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }"
    
    def _create_device_block(self, title, ip_key, port_key, default_ip, default_port):
        """
        创建一个设备的完整控制块
        返回: (整体布局, IP输入框, 端口输入框, 连接按钮, 状态标签, Info按钮, 激光按钮, Clear按钮)
        """
        # --- 外层容器 (GroupBox) ---
        group_box = QGroupBox(title)
        # 给 GroupBox 加一点样式，让标题更明显
        group_box.setStyleSheet(self._get_group_style())
        
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
        ip_edit.setText(self.settings.value(ip_key, default_ip, type=str))
        
        port_label = QLabel("端口:")
        port_edit = QLineEdit()
        port_edit.setPlaceholderText("Port")
        port_edit.setFixedWidth(80)
        port_edit.setText(self.settings.value(port_key, default_port, type=str))

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
        clear_pos_btn = QPushButton("Clear Pos")
        clear_pos_btn.setEnabled(False)  # <--- 禁用：变灰，不可点击

        row4.addWidget(get_info_btn)
        row4.addWidget(laser_btn)
        row4.addWidget(clear_pos_btn)
        
        v_layout.addLayout(row4)

        # --- 完成 ---
        group_box.setLayout(v_layout)
        
        # 返回所有需要交互的控件，方便外部绑定事件
        return group_box, ip_edit, port_edit, connect_btn, status_label, get_info_btn, laser_btn, clear_pos_btn

    
    def _create_arm_block(self):
        """机械臂控制模块"""
        group_box = QGroupBox("机械臂 (Robotic Arm)")
        group_box.setStyleSheet(self._get_group_style())
        v_layout = QVBoxLayout()
        v_layout.setSpacing(10)
        v_layout.setContentsMargins(15, 25, 15, 15)

        # --- 第一行: 连接控制 ---
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("IP:"))
        # 默认 IP 与原脚本一致
        self.arm_ip_edit = QLineEdit("10.20.22.232") 
        self.arm_ip_edit.setFixedWidth(120)
        row1.addWidget(self.arm_ip_edit)
        
        row1.addStretch()
        
        # 这里的连接按钮，我们用命令行的 reconnect / disconnect 命令来实现
        self.arm_connect_btn = QPushButton("连接")
        self.arm_connect_btn.setFixedWidth(120) 
        
        self.arm_status_label = QLabel("未连接")
        self.arm_status_label.setAlignment(Qt.AlignCenter)
        self.arm_status_label.setStyleSheet("background-color: #ffe6e6; color: red; padding: 5px;")
        
        row1.addWidget(self.arm_connect_btn)
        v_layout.addLayout(row1)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        v_layout.addWidget(line)

        # --- 第二行: 移动参数 ---
        row2 = QHBoxLayout()
        
        self.arm_pos_spin = QDoubleSpinBox()
        self.arm_pos_spin.setRange(-5000, 18500) # 范围放大一点
        self.arm_pos_spin.setSuffix(" (0.1mm)") # 注意原脚本单位是 0.1mm
        self.arm_pos_spin.setDecimals(0)
        self.arm_pos_spin.setFixedWidth(180)
        
        self.arm_speed_spin = QDoubleSpinBox()
        self.arm_speed_spin.setRange(0, 2000)
        self.arm_speed_spin.setValue(1000)
        self.arm_speed_spin.setSuffix(" (0.1mm/s)")
        self.arm_speed_spin.setFixedWidth(180)
        
        row2.addWidget(QLabel("位置:"))
        row2.addWidget(self.arm_pos_spin)
        row2.addWidget(QLabel("速度:"))
        row2.addWidget(self.arm_speed_spin)
        row2.addStretch()
        
        self.arm_move_btn = QPushButton("移动(move)")
        self.arm_move_btn.setEnabled(False) # 默认开启，是否成功由 cmd2 内部逻辑决定
        
        row2.addWidget(self.arm_move_btn)
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
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("在此输入原始 cmd2 命令，例如: move 11000 2000")
        self.btn_send_cmd = QPushButton("发送")
        self.btn_send_cmd.setEnabled(False)  # 默认禁用，连接后启用
        
        row4.addWidget(self.cmd_input)
        row4.addWidget(self.btn_send_cmd)
        v_layout.addLayout(row4)

        group_box.setLayout(v_layout)
        return group_box
    
    def initUI(self):
        # 1. 创建总布局：使用 QVBoxLayout (垂直排列)
        #    这样所有的东西是 上-下 结构的
        main_layout = QVBoxLayout() 
        
        # 2. 创建一个内部布局用于放置设备：使用 QHBoxLayout (水平排列)
        #    这样两个设备是 左-右 结构的
        devices_layout = QHBoxLayout()
        devices_layout.setSpacing(20)

        # --- 创建设备块 ---
        (cor_group, self.cor_ip_edit, self.cor_port_edit, self.cor_btn, 
         self.cor_status_label, self.cor_get_info_btn, self.cor_laser_btn, self.cor_clear_btn) = self._create_device_block(
            "正位探测器 (Coronal)", "cor_ip", "cor_port", "10.20.77.2", "50077"
        )
        
        (sag_group, self.sag_ip_edit, self.sag_port_edit, self.sag_btn, 
         self.sag_status_label, self.sag_get_info_btn, self.sag_laser_btn, self.sag_clear_btn) = self._create_device_block(
            "侧位探测器 (Sagittal)", "sag_ip", "sag_port", "10.20.99.2", "50099"
        )
        
        # 3. 将两个设备块加入 "devices_layout" (水平布局)
        devices_layout.addWidget(cor_group)
        devices_layout.addWidget(sag_group)

        # 4. 将 "devices_layout" 加入 "main_layout" (作为上半部分)
        main_layout.addLayout(devices_layout)

        
        # 3. 机械臂 (新增模块)
        arm_group_layout = QVBoxLayout()
        arm_group = self._create_arm_block()
        arm_group_layout.addWidget(arm_group) # 添加到同一排
        main_layout.addLayout(arm_group_layout)
        
        
        # 5. === 日志框 (作为下半部分) ===
        log_group = QGroupBox("输出日志")
        log_group.setStyleSheet(self._get_group_style())
        
        # 创建一个垂直布局给 GroupBox 内部使用
        log_inner_layout = QVBoxLayout()
        log_inner_layout.setContentsMargins(10, 25, 10, 10) # 上边距留大一点给标题

        self.log_box = QTextEdit()
        self.log_box.setPlaceholderText("输出日志...")
        self.log_box.setReadOnly(True)
        
        log_inner_layout.addWidget(self.log_box)
        
        # 将内部布局应用到 GroupBox
        log_group.setLayout(log_inner_layout)

        # 6. 将 GroupBox 加入主布局，并设置 stretch=1 (让它占据剩余所有垂直空间)
        main_layout.addWidget(log_group, stretch=1)

        # 7. 应用总布局
        self.setLayout(main_layout)
        
    def bind_events(self):
        # 绑定事件，使用 lambda 将具体的控件传给处理函数
        self.sag_btn.clicked.connect(
            lambda: self.connect_device("sag")
        )
        self.cor_btn.clicked.connect(
            lambda: self.connect_device("cor")
        )
        
        self.cor_get_info_btn.clicked.connect(
            lambda: self.get_det_info("cor")
        )
        self.sag_get_info_btn.clicked.connect(
            lambda: self.get_det_info("sag")
        )
        
        self.cor_laser_btn.clicked.connect(
            lambda: self.laser_control("cor")
        )
        self.sag_laser_btn.clicked.connect(
            lambda: self.laser_control("sag")
        )
        
        self.arm_connect_btn.clicked.connect(
            lambda: self.toggle_arm_thread()
        )
        
        # 2. 移动指令
        self.arm_move_btn.clicked.connect(self.cmd_move)
        
        # 3. 其他指令
        # self.arm_reset_btn.clicked.connect(lambda: self.send_cmd("reset_motor_error"))
    
    def shutdown(self):
        if self.arm_thread and self.arm_thread.isRunning():
            write_log(self.log_box, "[GUI] 正在关闭机械臂线程...")
            self.arm_thread.stop()
            self.arm_thread.wait()
            self.arm_thread.deleteLater()
            self.arm_thread = None

        
    def toggle_arm_thread(self):
        """处理 开启/关闭 线程"""
        # 如果线程存在且正在运行 -> 停止它
        if self.arm_thread and self.arm_thread.isRunning():
            write_log(self.log_box, "[INFO] 机械臂已连接， 请勿重复连接！")
            
        else:
            # 启动线程
            write_log(self.log_box, "[GUI] 正在启动机械臂线程...")
            self.arm_thread = SLZWorkerThread()
            
            # 【绑定信号】：把线程里的日志，打印到 log_box
            self.arm_thread.sig_log.connect(lambda msg: write_log(self.log_box, msg))
            
            # 启动！
            self.arm_thread.start()
            
            # 更新 UI
            # self.arm_connect_btn.setText("断开 (停止线程)")
            self.arm_status_label.setText("已连接")
            self.arm_status_label.setStyleSheet("background-color: #d4edda; color: green;")
            self.arm_move_btn.setEnabled(True)
            self.btn_send_cmd.setEnabled(True)
            
            # 注意：真实的连接是在线程内部初始化的，
            # 如果你想支持动态 IP，需要在 start() 之前把 IP 传给线程，
            # 或者 send_cmd("reconnect")

    def send_cmd(self, cmd_str):
        """发送指令的通用方法"""
        if self.arm_thread and self.arm_thread.isRunning():
            self.arm_thread.send_command(cmd_str)
        else:
            write_log(self.log_box, "[ERROR] 线程未运行，无法发送指令。")

    def cmd_move(self):
        """拼接 move 参数并发送"""
        pos = int(self.arm_pos_spin.value())
        speed = int(self.arm_speed_spin.value())
        # 发送字符串命令，就像你在 cmd 里面敲的一样
        self.send_cmd(f"move {pos} {speed}")
    
    # ---------------------------------------------------------
    def connect_device(self, device_type):
        if device_type == "cor":
            ip = self.cor_ip_edit.text().strip()
            port = int(self.cor_port_edit.text().strip())
            status_label = self.cor_status_label
            if not ip:
                write_log(self.log_box, "[ERROR] [正位COR网口] 地址不能为空。")
                return
            self.settings.setValue(f"last_cor_ip", ip)
            self.settings.sync()
            write_log(self.log_box, f"[INFO] 正位COR: {ip}:{port} 正在连接 ...")
            self.cor_controller.connect(ip, port, status_label, self._on_connect_result)
            

        elif device_type == "sag":
            ip = self.sag_ip_edit.text().strip()
            port = int(self.sag_port_edit.text().strip())
            status_label = self.sag_status_label
            if not ip:
                write_log(self.log_box, "[ERROR] [侧位网口] 地址不能为空。")
                return
            self.settings.setValue(f"last_sag_ip", ip)
            self.settings.sync()
            write_log(self.log_box, f"[INFO] 侧位SAG: {ip}:{port} 正在连接 ...")
            self.sag_controller.connect(ip, port, status_label, self._on_connect_result)
        else:
            write_log(self.log_box, f"[ERROR] 未知设备类型。")
            return

    def _on_connect_result(self, success, status_label, msg):
        if success:
            text = "已连接"
            # 绿色方案: 浅绿背景 + 深绿文字
            style = "background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; padding: 5px; border-radius: 3px; font-weight: bold;"
        else:
            text = "离线模式"
            # 橙色方案: 浅橙背景 + 深橙/褐文字
            style = "background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; padding: 5px; border-radius: 3px; font-weight: bold;"

        status_label.setText(text)
        status_label.setStyleSheet(style)
        
        # 记录日志
        write_log(self.log_box, f"[{'INFO' if success else 'ERROR'}] {msg}")

    # ---------------------------------------------------------
    def get_det_info(self, device_type):
        if device_type == "cor":
            write_log(self.log_box, "[INFO] 正在读取[正位COR]状态...")
            self.cor_controller.get_status(self._on_status_result)
        elif device_type == "sag":
            write_log(self.log_box, "[INFO] 正在读取[侧位SAG]状态...")
            self.sag_controller.get_status(self._on_status_result)
        else:
            write_log(self.log_box, f"[ERROR] 未知设备类型。")
            return

    def _on_status_result(self, success, result):
        """状态结果回调"""
        if success:
            # 在日志框中逐行输出状态
            write_log(self.log_box, "[INFO] 状态更新完成。")
            write_log(self.log_box, "[INFO] 状态信息：")
            for k, v in result.items():
                write_log(self.log_box, f"  {k}: {json.dumps(v, indent=2, ensure_ascii=False)}")
        else:
            write_log(self.log_box, f"[ERROR] 获取状态失败：{result}")

    def laser_control(self, device_type):
        if device_type == "cor":
            self.cor_controller.laser_control(self._on_laser_control_result)
        elif device_type == "sag":
            self.sag_controller.laser_control(self._on_laser_control_result)
        else:
            write_log(self.log_box, f"[ERROR] 未知设备类型。")
            return
    
    def _on_laser_control_result(self, success, msg):
        """激光器控制结果回调"""
        if success:
            write_log(self.log_box, f"[INFO] {msg}")
        else:
            write_log(self.log_box, f"[ERROR] {msg}")
