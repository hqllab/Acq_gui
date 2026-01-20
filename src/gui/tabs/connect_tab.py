# gui/tabs/connect_tab.py

import json
from turtle import title
from unicodedata import name
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QSettings

from .connect_tab_helper import create_detector_block, create_arm_blocks, create_exam_motor_blocks
from core.motor import MotorDriver
from core.detector_controller import DetectorController
from core.slz_controller import SLZWorkerThread
from gui.func import write_log


class ConnectTab(QWidget):
    """连接与参数设置界面（仅负责 UI）"""

    def __init__(self, log_box):
        super().__init__()
        # self.settings = QSettings("ScanGUI", "DetectorApp")
        self.exam_detector = DetectorController()
        self.exam_motor_driver = MotorDriver()
        
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
        
        # --- 创建设备块 ---
        exam_group_layout = QVBoxLayout()
        
        # 实验平台探测器ui
        (exam_detector_group, self.exam_detector_ip_edit, self.exam_detector_port_edit, self.exam_btn, 
         self.exam_detector_status_label, self.exam_get_info_btn, self.exam_laser_btn) = create_detector_block(
            "HD140探测器 (Exam)", "10.20.22.230", "7496"
        )
        exam_group_layout.addWidget(exam_detector_group)
        
        # 实验平台机械臂ui
        exam_motor_ui = create_exam_motor_blocks(
            "实验平台机械臂 (Robotic Arm)", "10.20.22.56", "19001"
        )
        
        # "group_box": group_box,
        # "ip_edit": ip_edit,
        # "port_edit": port_edit,
        # "connect_btn": connect_btn,
        # "status_label": status_label,
        # "pos_spin": pos_spin,
        # "speed_spin": speed_spin,
        # "move_btn": move_btn
        self.exam_ip_edit = exam_motor_ui["ip_edit"]
        self.exam_port_edit = exam_motor_ui["port_edit"]
        self.exam_connect_btn = exam_motor_ui["connect_btn"]
        self.exam_status_label = exam_motor_ui["status_label"]
        # self.exam_pos_spin = exam_motor_ui["pos_spin"]
        # self.exam_speed_spin = exam_motor_ui["speed_spin"]
        # self.exam_move_btn = exam_motor_ui["move_btn"]
        
        exam_group_layout.addWidget(exam_motor_ui["group_box"])
        main_layout.addLayout(exam_group_layout)
        
        
        # 2. 创建一个内部布局用于放置设备2：使用 QHBoxLayout (水平排列)
        bone_devices_layout = QHBoxLayout()
        bone_devices_layout.setSpacing(20)

        # --- 创建设备块 ---
        (cor_group, self.cor_ip_edit, self.cor_port_edit, self.cor_btn, 
         self.cor_status_label, self.cor_get_info_btn, self.cor_laser_btn) = create_detector_block(
            "正位探测器 (Coronal)", "10.20.77.2", "50077"
        )
        
        (sag_group, self.sag_ip_edit, self.sag_port_edit, self.sag_btn, 
         self.sag_status_label, self.sag_get_info_btn, self.sag_laser_btn) = create_detector_block(
            "侧位探测器 (Sagittal)", "10.20.99.2", "50099"
        )
         
         
        # 3. 将两个设备块加入 "devices_layout" (水平布局)
        bone_devices_layout.addWidget(cor_group)
        bone_devices_layout.addWidget(sag_group)

        # 4. 将 "devices_layout" 加入 "main_layout" (作为上半部分)
        main_layout.addLayout(bone_devices_layout)

        
        # 5. 机械臂 (新增模块)
        arm_group_layout = QVBoxLayout()
        arm_group, self.ip_edit, self.arm_connect_btn, self.arm_status_label, self.arm_pos_spin, self.arm_speed_spin, self.arm_move_btn, self.cmd_input, self.btn_send_cmd = create_arm_blocks("10.20.22.232")
        arm_group_layout.addWidget(arm_group) # 添加到同一排
        main_layout.addLayout(arm_group_layout)
        
        # 6. 留出空余部分
        main_layout.addStretch(1)  # ✅ 关键

        # 7. 应用总布局
        self.setLayout(main_layout)
        
    def bind_events(self):
        # 绑定事件，使用 lambda 将具体的控件传给处理函数
        self.exam_btn.clicked.connect(
            lambda: self.connect_device("exam")
        )
        self.exam_get_info_btn.clicked.connect(
            lambda: self.get_det_info("exam")
        )
        self.exam_laser_btn.clicked.connect(
            lambda: self.laser_control("exam")
        )
        
        self.exam_connect_btn.clicked.connect(
            lambda: self.connect_motor()
        )
        
        # self.cor_btn.clicked.connect(
        #     lambda: self.connect_motor()
        # )
        
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

    def connect_motor(self):
        """连接实验平台机械臂"""
        ip = self.exam_ip_edit.text().strip()
        port = int(self.exam_port_edit.text().strip())
        status_label = self.exam_status_label
        try:
            self.exam_motor_driver.connect(ip, port, status_label)
            write_log(self.log_box, "[INFO] 机械臂连接成功")
        except Exception as e:
            write_log(self.log_box, f"[ERROR] 连接机械臂失败: {e}")
        
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
        # self.arm_connect_btn.setText("断开 (停止线程)")
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
    def connect_device(self, device_type):
        print('11111111', device_type)
        if device_type == "exam":
            ip = self.exam_detector_ip_edit.text().strip()
            port = int(self.exam_detector_port_edit.text().strip())
            status_label = self.exam_detector_status_label
            print(ip, port, status_label)
            write_log(self.log_box, f"[INFO] EXAM 探测器: {ip}:{port} 正在连接 ...")
            self.exam_detector.connect(ip, port, status_label, self._on_connect_result)
        elif device_type == "cor":
            ip = self.cor_ip_edit.text().strip()
            port = int(self.cor_port_edit.text().strip())
            status_label = self.cor_status_label
            write_log(self.log_box, f"[INFO] 正位COR: {ip}:{port} 正在连接 ...")
            self.cor_detector.connect(ip, port, status_label, self._on_connect_result)
        elif device_type == "sag":
            ip = self.sag_ip_edit.text().strip()
            port = int(self.sag_port_edit.text().strip())
            status_label = self.sag_status_label
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
        if device_type == "exam":
            write_log(self.log_box, "[INFO] 正在读取[EXAM]状态...")
            self.exam_detector.get_status(self._on_status_result)
        elif device_type == "cor":
            write_log(self.log_box, "[INFO] 正在读取[正位COR]状态...")
            self.cor_detector.get_status(self._on_status_result)
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
        if device_type == "exam":
            self.exam_detector.laser_control(self._on_laser_control_result)
        elif device_type == "cor":
            self.cor_detector.laser_control(self._on_laser_control_result)
        elif device_type == "sag":
            self.sag_detector.laser_control(self._on_laser_control_result)
        else:
            write_log(self.log_box, f"[ERROR] 未知设备类型。")
            return
    
    def _on_laser_control_result(self, success, msg):
        """激光器控制结果回调"""
        if success:
            write_log(self.log_box, f"[INFO] {msg}")
        else:
            write_log(self.log_box, f"[ERROR] {msg}")
