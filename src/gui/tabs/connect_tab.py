# gui/tabs/connect_tab.py

import json
from turtle import title
from unicodedata import name
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QSettings

from .connect_tab_helper import create_detector_block, create_arm_blocks, create_exam_arm_block
from core.motor import MotorDriver
from core.detector_controller import DetectorController
from core.slz_controller import SLZWorkerThread
from gui.func import write_log


class ConnectTab(QWidget):
    """连接与参数设置界面（仅负责 UI）"""

    def __init__(self, log_box):
        super().__init__()
        # self.settings = QSettings("ScanGUI", "DetectorApp")
        
        # 实验平台
        self.exam_detector = DetectorController()
        self.exam_motor_driver = MotorDriver()
        
        # 骨密度平台
        self.cor_detector = DetectorController()
        self.sag_detector = DetectorController()
        self.arm_thread = SLZWorkerThread()
        
        self.log_box = log_box
        
        self.initUI()
        self.bind_events()

    def initUI(self):
        # 1. 创建总布局：使用 QVBoxLayout (垂直排列)
        #    这样所有的东西是 上-下 结构的
        main_layout = QVBoxLayout() 
        
        # 实验平台布局
        # 1. 探测器 + 机械臂控制
        exam_group_layout = QVBoxLayout()
        
        # 实验平台探测器ui
        self.exam_detector_ui = create_detector_block(
            "HD140探测器 (Exam)", "10.20.22.230", "7496"
        )
        exam_group_layout.addWidget(self.exam_detector_ui["group_box"])
        
        # 实验平台机械臂ui
        self.exam_arm_ui = create_exam_arm_block(
            "实验平台机械臂 (Robotic Arm)", "10.20.22.56", "19001"
        )
        exam_group_layout.addWidget(self.exam_arm_ui["group_box"])
        main_layout.addLayout(exam_group_layout)
        
        
        # 2. 创建一个内部布局用于骨密度平台：使用 QHBoxLayout (水平排列)
        bone_detector_layout = QHBoxLayout()
        bone_detector_layout.setSpacing(20)

        # --- 创建设备块 ---
        self.cor_detector_ui = create_detector_block(
            "正位探测器 (Coronal)", "10.20.77.2", "50077"
        )
        # 侧位探测器ui
        self.sag_detector_ui = create_detector_block(
            "侧位探测器 (Sagittal)", "10.20.99.2", "50099"
        )
        # 将两个设备块加入 "devices_layout" (水平布局)
        bone_detector_layout.addWidget(self.cor_detector_ui["group_box"])
        bone_detector_layout.addWidget(self.sag_detector_ui["group_box"])

        # 将 "devices_layout" 加入 "main_layout" (作为上半部分)
        main_layout.addLayout(bone_detector_layout)

        # 5. 机械臂 (新增模块)
        arm_group_layout = QVBoxLayout()
        self.bone_arm_ui = create_arm_blocks("10.20.22.232")
        arm_group_layout.addWidget(self.bone_arm_ui["group_box"]) # 添加到同一排
        main_layout.addLayout(arm_group_layout)
        
        # 6. 留出空余部分
        main_layout.addStretch(1)  # ✅ 关键

        # 7. 应用总布局
        self.setLayout(main_layout)
        
    def bind_events(self):
        # 绑定事件，使用 lambda 将具体的控件传给处理函数
        self.exam_detector_ui["connect_btn"].clicked.connect(
            lambda: self.connect_device('exam')
        )
        self.exam_detector_ui["get_info_btn"].clicked.connect(
            lambda: self.get_det_info('exam')
        )
        self.exam_detector_ui["laser_btn"].clicked.connect(
            lambda: self.laser_control('exam')
        )
        self.exam_arm_ui["connect_btn"].clicked.connect(
            lambda: self.connect_motor()
        )
        
        # 正位探测器
        self.cor_detector_ui["connect_btn"].clicked.connect(
            lambda: self.connect_device('cor')
        )
        self.cor_detector_ui["get_info_btn"].clicked.connect(
            lambda: self.get_det_info('cor')
        )
        self.cor_detector_ui["laser_btn"].clicked.connect(
            lambda: self.laser_control('cor')
        )
        # 侧位探测器
        self.sag_detector_ui["connect_btn"].clicked.connect(
            lambda: self.connect_device('sag')
        )
        self.sag_detector_ui["laser_btn"].clicked.connect(
            lambda: self.laser_control('sag')
        )
        self.sag_detector_ui["get_info_btn"].clicked.connect(
            lambda: self.get_det_info('sag')
        )
        
        # 机械臂连接
        self.bone_arm_ui["connect_btn"].clicked.connect(
            lambda: self.toggle_arm_thread()
        )
        
        # 2. 移动指令
        self.bone_arm_ui["move_btn"].clicked.connect(self.cmd_move)

    def connect_motor(self):
        """连接实验平台机械臂"""
        ip = self.exam_arm_ui["ip_edit"].text().strip()
        port = int(self.exam_arm_ui["port_edit"].text().strip())
        status_label = self.exam_arm_ui["status_label"]
        try:
            write_log(self.log_box, f"[INFO] 正在连接 {ip}:{port} 机械臂...")
            self.exam_motor_driver.connect(ip, port, status_label, self._connect_exam_arm_result)
            write_log(self.log_box, "[INFO] 机械臂连接成功")
        except Exception as e:
            write_log(self.log_box, f"[ERROR] 连接机械臂失败: {e}")
    
    def _connect_exam_arm_result(self, success, status_label, msg):
        """机械臂连接结果回调"""
        if success:
            text = "已连接"
            # 绿色方案: 浅绿背景 + 深绿文字
            style = "background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; padding: 5px; border-radius: 3px; font-weight: bold;"
            status_label.setText(text)
            status_label.setStyleSheet(style)
            write_log(self.log_box, "[INFO] 机械臂连接成功")
        else:
            text = "离线模式"
            style = "background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; padding: 5px; border-radius: 3px; font-weight: bold;"
            status_label.setText(text)
            status_label.setStyleSheet(style)
            write_log(self.log_box, f"[ERROR] 连接机械臂失败: {msg}")
                      
    def toggle_arm_thread(self):
        """开启 线程"""
        # 如果线程存在且正在运行 -> 停止它
        if self.arm_thread and self.arm_thread.isRunning():
            write_log(self.log_box, "[INFO] 机械臂已连接， 请勿重复连接！")
        else:
            # 启动线程
            write_log(self.log_box, "[INFO] 正在启动机械臂线程...")
            
            # 【绑定信号】：把线程里的日志，打印到 log_box
            self.arm_thread.sig_log.connect(lambda msg: write_log(self.log_box, msg))
            
            # 启动！
            self.arm_thread.start()
            
        # 更新 UI
        self.arm_status_label.setText("已连接")
        self.arm_status_label.setStyleSheet("background-color: #d4edda; color: green;")
        self.arm_move_btn.setEnabled(True)
        self.btn_send_cmd.setEnabled(True)
        

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
    def connect_device(self, detector_type):
        try:
            if detector_type == 'exam':
                detector_ui = self.exam_detector_ui
                detector = self.exam_detector
            elif detector_type == 'cor':
                detector_ui = self.cor_detector_ui
                detector = self.cor_detector
            elif detector_type == 'sag':
                detector_ui = self.sag_detector_ui
                detector = self.sag_detector
            else:
                write_log(self.log_box, f"[ERROR] 未知的探测器类型: {detector_type}")
                return
            ip = detector_ui["ip_edit"].text().strip()
            port = int(detector_ui["port_edit"].text().strip())
            status_label = detector_ui["status_label"]
            write_log(self.log_box, f"[INFO] 探测器: {ip}:{port} 正在连接 ...")
            detector.connect(ip, port, status_label, self._on_connect_result)
        except Exception as e:
            write_log(self.log_box, f"[ERROR] 连接探测器失败: {e}")

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
    def get_det_info(self, detector_type):
        try:
            if detector_type == 'exam':
                detector_ui = self.exam_detector_ui
                detector = self.exam_detector
            elif detector_type == 'cor':
                detector_ui = self.cor_detector_ui
                detector = self.cor_detector
            elif detector_type == 'sag':
                detector_ui = self.sag_detector_ui
                detector = self.sag_detector
            else:
                write_log(self.log_box, f"[ERROR] 未知的探测器类型: {detector_type}")
                return
            
            ip = detector_ui["ip_edit"].text().strip()
            port = int(detector_ui["port_edit"].text().strip())
            write_log(self.log_box, f"[INFO] 正在读取 {ip}:{port} 状态...")
            detector.get_status(self._on_status_result)
        except Exception as e:
            write_log(self.log_box, f"[ERROR] 获取状态失败: {e}")

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

    def laser_control(self, detector_type):
        try:
            if detector_type == 'exam':
                detector_ui = self.exam_detector_ui
                detector = self.exam_detector
            elif detector_type == 'cor':
                detector_ui = self.cor_detector_ui
                detector = self.cor_detector
            elif detector_type == 'sag':
                detector_ui = self.sag_detector_ui
                detector = self.sag_detector
            else:
                write_log(self.log_box, f"[ERROR] 未知的探测器类型: {detector_type}")
                return
            ip = detector_ui["ip_edit"].text().strip()
            port = int(detector_ui["port_edit"].text().strip())
            write_log(self.log_box, f"[INFO] 正在控制 {ip}:{port} 激光器...")
            detector.laser_control(self._on_laser_control_result)
        except Exception as e:
            write_log(self.log_box, f"[ERROR] 控制激光器失败: {e}")
    
    def _on_laser_control_result(self, success, msg):
        """激光器控制结果回调"""
        if success:
            write_log(self.log_box, f"[INFO] {msg}")
        else:
            write_log(self.log_box, f"[ERROR] {msg}")
