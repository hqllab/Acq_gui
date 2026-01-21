# gui/tabs/acquire_tab.py

import os
from core.motor import control_motor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QTextEdit, QLabel, QRadioButton, QButtonGroup,
    QDoubleSpinBox, QSpinBox, QFrame, QLineEdit, 
    QPushButton, QFileDialog
)
from PySide6.QtCore import Qt, QSettings

from .acquire_tab_helper import create_motion_block, create_tube_panel, create_execution_block_exam
from gui.func import write_log
from gui.tabs.connect_tab import ConnectTab
import threading
from core.motor import MotorDriver

class ExamAcquireTab(QWidget):
    """采集参数设置与控制界面"""

    def __init__(self, connect_tab_instance: ConnectTab, log_box):
        super().__init__()
        self.settings = QSettings("Vplus", "ScanGui")
        
        self.detector = connect_tab_instance.exam_detector
        self.motor_driver = connect_tab_instance.exam_motor_driver
        self.log_box = log_box

        self.initUI()
        self.bind_events()
        self.update_file_preview()
        self.load_settings()
        
    def load_settings(self):
        """加载采集参数设置"""
        # 加载运动控制参数
        self.arm_ui["start_pos"].setValue(self.settings.value("exam_acquire/start_pos", 0.0, float))
        self.arm_ui["end_pos"].setValue(self.settings.value("exam_acquire/end_pos", 100.0, float))
        self.arm_ui["speed"].setValue(self.settings.value("exam_acquire/speed", 100.0, float))
        
        # 加载球管采集参数
        self.detector_ui["kv"].setValue(self.settings.value("exam_acquire/kv", 75, int))
        self.detector_ui["ma"].setValue(self.settings.value("exam_acquire/ma", 2.0, float))
        self.detector_ui["radio_spectral"].setChecked(self.settings.value("exam_acquire/is_spectral", True, bool))
        self.detector_ui["radio_binned"].setChecked(self.settings.value("exam_acquire/is_binned", False, bool))
        self.detector_ui["spectral"][0].setValue(self.settings.value("exam_acquire/spectral_0", 0, int))
        self.detector_ui["spectral"][1].setValue(self.settings.value("exam_acquire/spectral_1", 120, int))
        default_win = [
            [0, 30],
            [40, 80],
            [15, 60],
            [0, 100]
        ]
        for i, win in enumerate(default_win):
            self.detector_ui[f"binned_spinboxes"][i][0].setValue(self.settings.value(f"exam_acquire/binned_spinboxes_{i}0", win[0], int))
            self.detector_ui[f"binned_spinboxes"][i][1].setValue(self.settings.value(f"exam_acquire/binned_spinboxes_{i}1", win[1], int))
        self.detector_ui["radio_sync"].setChecked(self.settings.value("exam_acquire/is_sync", True, bool))
        self.detector_ui["radio_fixed"].setChecked(self.settings.value("exam_acquire/is_fixed", False, bool))
        self.detector_ui["fixed_time"].setValue(self.settings.value("exam_acquire/fixed_time", 5.0, float))
        self.detector_ui["frame_time"].setValue(self.settings.value("exam_acquire/frame_time", 2.0, float))
        self.detector_ui["sid"].setValue(self.settings.value("exam_acquire/sid", 610.0, float))
        self.detector_ui["sdd"].setValue(self.settings.value("exam_acquire/sdd", 670, float))
        self._update_frametime_range(self.detector_ui)  # 根据模式更新范围
        
        # 数据保存目录
        self.acq_ui["dir_edit"].setText(self.settings.value("exam_acquire/dir", os.path.expanduser("~"), str))
        self.acq_ui["prefix_edit"].setText(self.settings.value("exam_acquire/prefix", "exam", str))
        self.update_file_preview()

    
    def save_settings(self):
        # 保存运动控制参数
        self.settings.setValue("exam_acquire/start_pos", self.arm_ui["start_pos"].value())
        self.settings.setValue("exam_acquire/end_pos", self.arm_ui["end_pos"].value())
        self.settings.setValue("exam_acquire/speed", self.arm_ui["speed"].value())
        # 保存球管采集参数
        self.settings.setValue("exam_acquire/kv", self.detector_ui["kv"].value())
        self.settings.setValue("exam_acquire/ma", self.detector_ui["ma"].value())
        self.settings.setValue("exam_acquire/is_spectral", self.detector_ui["radio_spectral"].isChecked())
        self.settings.setValue("exam_acquire/is_binned", self.detector_ui["radio_binned"].isChecked())
        self.settings.setValue("exam_acquire/spectral_0", self.detector_ui["spectral"][0].value())
        self.settings.setValue("exam_acquire/spectral_1", self.detector_ui["spectral"][1].value())
        for i, win in enumerate(self.detector_ui["binned_spinboxes"]):
            self.settings.setValue(f"exam_acquire/binned_spinboxes_{i}0", win[0].value())
            self.settings.setValue(f"exam_acquire/binned_spinboxes_{i}1", win[1].value())
        self.settings.setValue("exam_acquire/is_sync", self.detector_ui["radio_sync"].isChecked())
        self.settings.setValue("exam_acquire/is_fixed", self.detector_ui["radio_fixed"].isChecked())
        self.settings.setValue("exam_acquire/fixed_time", self.detector_ui["fixed_time"].value())
        self.settings.setValue("exam_acquire/frame_time", self.detector_ui["frame_time"].value())
        self.settings.setValue("exam_acquire/sid", self.detector_ui["sid"].value())
        self.settings.setValue("exam_acquire/sdd", self.detector_ui["sdd"].value())
        # 数据保存目录
        self.settings.setValue("exam_acquire/dir", self.acq_ui["dir_edit"].text())
        self.settings.setValue("exam_acquire/prefix", self.acq_ui["prefix_edit"].text())
        
        print("ACQUIRE Settings saved successfully.")
        
    
    def closeEvent(self, event):
        """窗口关闭时断开连接"""
        if self.motor_driver:
            self.motor_driver.close()
        self.save_settings()
        super().closeEvent(event)

    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # 1. 运动控制
        self.arm_ui = create_motion_block()
        main_layout.addWidget(self.arm_ui["group_box"])

        # 2. 正位与侧位通道
        channels_layout = QHBoxLayout()
        self.detector_ui = create_tube_panel("探测器")
        channels_layout.addWidget(self.detector_ui["panel"])
        main_layout.addLayout(channels_layout)
        
        # 3. 采集执行模块
        self.acq_ui = create_execution_block_exam()
        main_layout.addWidget(self.acq_ui["group_box"])

    def select_directory(self):
        """选择文件夹"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.acq_ui["dir_edit"].text())
        if dir_path:
            self.acq_ui["dir_edit"].setText(dir_path)

    def _update_frametime_range(self, ui_dict):
        """根据能谱/合并能窗模式切换 FrameTime 范围"""
        is_spectral = ui_dict["radio_spectral"].isChecked()
        if is_spectral:
            # 能谱模式: 4.0ms - 100ms
            ui_dict["frame_time"].setMinimum(0.5)
            if ui_dict["frame_time"].value() < 0.5:
                ui_dict["frame_time"].setValue(0.5)
        else:
            # 合并能窗: 0.5ms - 100ms
            ui_dict["frame_time"].setMinimum(0.5)

    def update_file_preview(self):
        """实时更新文件路径预览"""
        save_dir = self.acq_ui["dir_edit"].text()
        prefix = self.acq_ui["prefix_edit"].text()
        speed = round(self.arm_ui["speed"].value(), 2)
        
        voltage = int(self.detector_ui["kv"].value())
        current = round(self.detector_ui["ma"].value(), 2)
        frame_time = round(self.detector_ui['frame_time'].value(), 2)
        sid = int(self.detector_ui["sid"].value())
        sdd = int(self.detector_ui["sdd"].value())
        

        def generate_path(suffix):
            # 逻辑：能谱 -> cali, 合并能窗 -> recon
            mode_tag = "cali" if self.detector_ui["radio_spectral"].isChecked() else "recon"
            filename = (f"{prefix}_{speed}mmps_{voltage}kv_{current}ma_"
                        f"{frame_time}mspf_sid{sid}_sdd{sdd}_{mode_tag}_{suffix}.mat")
            return os.path.join(save_dir, filename)

        self.save_path = generate_path("exam")
        
        self.acq_ui["preview_label"].setText(f"保存路径: {self.save_path}")

    def bind_events(self):
        """绑定 UI 事件"""
        # 1. 目录浏览
        self.acq_ui["browse_btn"].clicked.connect(self.select_directory)

        # 2. 采集模式联动 (固定时长输入框开关)
        self.detector_ui["radio_fixed"].toggled.connect(lambda checked: self.detector_ui["fixed_time"].setEnabled(checked))

        # 3. 数据模式联动 (FrameTime 范围限制)
        self.detector_ui["radio_spectral"].toggled.connect(lambda: self._update_frametime_range(self.detector_ui))

        # 4. 路径预览联动 (所有相关控件变化时触发预览更新)
        # 基础信息
        self.acq_ui["dir_edit"].textChanged.connect(self.update_file_preview)
        self.acq_ui["prefix_edit"].textChanged.connect(self.update_file_preview)
        self.arm_ui["speed"].textChanged.connect(self.update_file_preview)
        
        # 通道参数
        for ui in [self.detector_ui]:
            ui["kv"].valueChanged.connect(self.update_file_preview)
            ui["ma"].valueChanged.connect(self.update_file_preview)
            ui["frame_time"].valueChanged.connect(self.update_file_preview)
            ui["sid"].valueChanged.connect(self.update_file_preview)
            ui["radio_spectral"].toggled.connect(self.update_file_preview)

        # 5. 初始化参数默认值
        for ui in [self.detector_ui]:
            ui["kv"].setValue(75)
            ui["ma"].setValue(2)
            ui["sid"].setValue(610)
            ui["sdd"].setValue(670)
            self._update_frametime_range(ui) # 初始化范围限制
        
        # 6. 绑定采集
        self.acq_ui["start_btn"].clicked.connect(self.start_acq_pipeline)


    def start_acq_pipeline(self):
        # 检查电机连接
        if self.motor_driver is None:
            write_log(self.log_box, "[Error] 电机未连接，无法执行！")
            return

        # init
        if self.detector is None or self.detector.det is None or self.detector.offline:
            write_log(self.log_box, "[Error] 未连接正位[COR]探测器，无法采集！")
            return
            
        if os.path.exists(self.save_path):
            write_log(self.log_box, "[Error] 文件路径已存在！")
            return
        
        data_mode = "spectral" if self.detector_ui["radio_spectral"].isChecked() else "binned"
        acq_mode = "fixed" if self.detector_ui["radio_fixed"].isChecked() else "sync"
        cor_win_range = []
        if data_mode == "spectral":
            cor_win_range = (self.detector_ui["spectral"][0].value(), self.detector_ui["spectral"][1].value())
        else:
            for min_spin, max_spin in self.detector_ui["binned_spinboxes"]:
                cor_win_range.append( (min_spin.value(), max_spin.value()) )

        # 2s 是加减速
        try:
            move_time = (self.arm_ui["end_pos"].value()- self.arm_ui["start_pos"].value())/self.arm_ui["speed"].value() + 2
        except:
            move_time = 0.5
            print(f"Exception in cal move_time, set move_time: {move_time}!")

        
        ### 曝光时间 == 采集时间 == 运动时间
        acq_params = {
            "data_mode" : data_mode,
            "win_range" : cor_win_range,
            "time" : self.detector_ui["fixed_time"].value() if acq_mode == "fixed" else move_time,
            "interval" : self.detector_ui["frame_time"].value(),
            "filepath" : self.save_path,
        }

         # 3. 创建同步信号 (红绿灯)
        trigger_event = threading.Event()

        # =========================================================
        # 4. 定义 采集 线程任务 (等待者)
        # =========================================================
        def run_acq_task():
            write_log(self.log_box, "[Info] 采集线程就绪，等待电机启动信号...")
            
            # 阻塞在这里，直到电机线程调用 set()
            is_set = trigger_event.wait(timeout=10) # 设置个超时防止死等
            
            if not is_set:
                write_log(self.log_box, "[Error] 等待电机信号超时，采集取消")
                return

            write_log(self.log_box, "[Info] 信号已收到，开始采集...")
            try:
                # 传入提前获取好的参数
                self.detector.start_acquire(**acq_params)
                write_log(self.log_box, "[Success] 正位(COR) 采集完成")
            except Exception as e:
                write_log(self.log_box, f"[Error-COR] {e}")

        # =========================================================
        # 5. 定义 电机 线程任务 (触发者)
        # =========================================================
        def run_motor_task():
            write_log(self.log_box, "[Info] 电机开始运动流程...")
            try:
                start_pos = self.arm_ui['start_pos'].value()
                end_pos = self.arm_ui['end_pos'].value()
                speed = self.arm_ui['speed'].value()
                time = move_time
                
                # 【关键修改】将 self.motor_driver 传入函数
                control_motor(self.motor_driver, start_pos, end_pos, speed, time=time, start_event=trigger_event)
                
                write_log(self.log_box, "[Info] 电机流程结束")
            except Exception as e:
                write_log(self.log_box, f"[Error-Motor] {e}")
                # 如果发生严重通信错误，可能需要置空 driver 迫使下次重连
                # self.motor_driver = None 

        # =========================================================
        # 6. 启动双线程
        # =========================================================
        # 先启动采集线程让它去 wait
        t_acq = threading.Thread(target=run_acq_task, daemon=True)
        t_acq.start()
        
        # 再启动电机线程
        t_motor = threading.Thread(target=run_motor_task, daemon=True)
        t_motor.start()

        