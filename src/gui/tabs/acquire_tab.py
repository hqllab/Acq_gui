# gui/tabs/acquire_tab.py

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QTextEdit, QLabel, QRadioButton, QButtonGroup,
    QDoubleSpinBox, QSpinBox, QFrame, QLineEdit, 
    QPushButton, QFileDialog
)
from PySide6.QtCore import Qt, QSettings

from .acquire_tab_helper import create_motion_block, create_channel_panel, create_execution_block
# from .acq_worker import AcquisitionWorker
# from core.slz_controller import SLZWorkerThread
from gui.func import write_log
import time
import threading

class AcquireTab(QWidget):
    """采集参数设置与控制界面"""

    def __init__(self, connect_tab_instance, log_box):
        super().__init__()
        # self.settings = QSettings("ScanGUI", "DetectorApp")
        self.cor_ctrl = connect_tab_instance.cor_detector
        self.sag_ctrl = connect_tab_instance.sag_detector
        self.arm_thread = connect_tab_instance.arm_thread 

        self.log_box = log_box

        self.initUI()
        self.bind_events()
        # 初始化界面数值逻辑
        self.update_file_preview()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # 1. 运动控制
        self.arm_ui = create_motion_block()
        main_layout.addWidget(self.arm_ui["group_box"])

        # 2. 正位与侧位通道
        channels_layout = QHBoxLayout()
        self.cor_ui = create_channel_panel("正位 (COR)")
        self.sag_ui = create_channel_panel("侧位 (SAG)")
        channels_layout.addWidget(self.cor_ui["panel"])
        channels_layout.addWidget(self.sag_ui["panel"])
        main_layout.addLayout(channels_layout)
        
        # 3. 采集执行模块
        self.acq_ui = create_execution_block()
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
            ui_dict["frame_time"].setMinimum(4.0)
            if ui_dict["frame_time"].value() < 4.0:
                ui_dict["frame_time"].setValue(4.0)
        else:
            # 合并能窗: 0.5ms - 100ms
            ui_dict["frame_time"].setMinimum(0.5)

    def update_file_preview(self):
        """实时更新文件路径预览"""
        # save_dir = self.dir_edit.text()
        # prefix = self.prefix_edit.text()
        # speed = self.speed.value()
        save_dir = self.acq_ui["dir_edit"].text()
        prefix = self.acq_ui["prefix_edit"].text()
        speed = int(self.arm_ui["speed"].value())

        def generate_path(ui, suffix):
            # 逻辑：能谱 -> cali, 合并能窗 -> recon
            mode_tag = "cali" if ui["radio_spectral"].isChecked() else "recon"
            filename = (f"{prefix}_{speed}mmps_{ui['kv'].value()}kv_{ui['ma'].value()}ma_"
                        f"{mode_tag}_{int(ui['frame_time'].value())}mspf_sid{int(ui['sid'].value())}_{suffix}.mat")
            return os.path.join(save_dir, filename)

        self.cor_save_path = generate_path(self.cor_ui, "cor")
        self.sag_save_path = generate_path(self.sag_ui, "sag")
        
        self.acq_ui["cor_preview_label"].setText(f"正位路径: {self.cor_save_path}")
        self.acq_ui["sag_preview_label"].setText(f"侧位路径: {self.sag_save_path}")

    def bind_events(self):
        """绑定 UI 事件"""
        # 1. 目录浏览
        self.acq_ui["browse_btn"].clicked.connect(self.select_directory)

        # 2. 采集模式联动 (固定时长输入框开关)
        self.cor_ui["radio_fixed"].toggled.connect(lambda checked: self.cor_ui["fixed_duration"].setEnabled(checked))
        self.sag_ui["radio_fixed"].toggled.connect(lambda checked: self.sag_ui["fixed_duration"].setEnabled(checked))

        # 3. 数据模式联动 (FrameTime 范围限制)
        self.cor_ui["radio_spectral"].toggled.connect(lambda: self._update_frametime_range(self.cor_ui))
        self.sag_ui["radio_spectral"].toggled.connect(lambda: self._update_frametime_range(self.sag_ui))

        # 4. 路径预览联动 (所有相关控件变化时触发预览更新)
        # 基础信息
        self.acq_ui["dir_edit"].textChanged.connect(self.update_file_preview)
        self.acq_ui["prefix_edit"].textChanged.connect(self.update_file_preview)
        self.arm_ui["speed"].textChanged.connect(self.update_file_preview)
        # self.prefix_edit.textChanged.connect(self.update_file_preview)
        # self.speed.valueChanged.connect(self.update_file_preview)
        
        # 通道参数
        for ui in [self.cor_ui, self.sag_ui]:
            ui["kv"].valueChanged.connect(self.update_file_preview)
            ui["ma"].valueChanged.connect(self.update_file_preview)
            ui["frame_time"].valueChanged.connect(self.update_file_preview)
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
        self.acq_ui["init_btn"].clicked.connect(self.init_acq_pipeline)
        self.acq_ui["start_btn"].clicked.connect(self.start_acq_pipeline)
    
    def init_acq_pipeline(self):
        # init
        if self.cor_ctrl is None or self.cor_ctrl.det is None or self.cor_ctrl.offline:
            write_log(self.log_box, "[Error] 未连接正位[COR]探测器，无法采集！")
            return
        
        if self.sag_ctrl is None or self.sag_ctrl.det is None or self.sag_ctrl.offline:
            write_log(self.log_box, "[Error] 未连接侧位[SAG]探测器，无法采集！")
            return
        
        current_arm_thread = self.arm_thread
        if current_arm_thread is None or not current_arm_thread.isRunning():
            write_log(self.log_box, "[Error] 机械臂未连接！")
            return
            
        if os.path.exists(self.cor_save_path) or os.path.exists(self.sag_save_path):
            write_log(self.log_box, "[Error] 文件路径已存在！")
            return
        
        # 第一步, 生成script.txt 文件, 设置 机械臂参数 和 电压电流参数
        cmds = []
        cmds.append(f"exit_exposure_mode")
        cmds.append(f"allow_exposure 3")
        # cmds.append(f"set_max_exposure_time 0 9000")
        # cmds.append(f"set_max_exposure_time 1 9000")
        
        # 球管B -> 正位
        cmds.append(f"set_voltage 0 {self.sag_ui['kv'].value()}")   
        cmds.append(f"set_current 0 {self.sag_ui['ma'].value()}")
        # 球管A -> 侧位
        cmds.append(f"set_voltage 1 {self.cor_ui['kv'].value()}")
        cmds.append(f"set_current 1 {self.cor_ui['ma'].value()}")
        
        # 机械臂位置
        cmds.append(f"move {int(self.arm_ui['start_pos'].value()*10)} {1500}")
        cmds.append(f"set_exposure_pos {int(self.arm_ui['end_pos'].value()*10)} {int(self.arm_ui['speed'].value()*10)}")
        # cmds.append(f"set_exposure_pos {int(self.end_pos.value()*10)} {int(self.speed.value()*10)}")
        cmds.append(f"enter_exposure_mode")
        
        for cmd in cmds:
            self.arm_thread.send_command(cmd)
            time.sleep(0.05)
            
            if "move" in cmd:
                time.sleep(0.4)
        # write_log(self.log_box, f"[Info] 初始化完毕！55555555555555555555555555")
        

    def start_acq_pipeline(self):
        cor_acq_mode = "spectral" if self.cor_ui["radio_spectral"].isChecked() else "binned"
        cor_win_range = []
        if cor_acq_mode == "spectral":
            cor_win_range = (self.cor_ui["spectral"][0].value(), self.cor_ui["spectral"][1].value())
            # cor_win_range = (self.cor_ui["spectral_min"].value(), self.cor_ui["spectral_max"].value())
        else:
            for min_spin, max_spin in self.cor_ui["binned_spinboxes"]:
                cor_win_range.append( (min_spin.value(), max_spin.value()) )
        if os.path.exists(self.cor_save_path):
            write_log(self.log_box, f"[Error]: {self.cor_save_path} 文件已存在！")
            return
        
        sag_acq_mode = "spectral" if self.sag_ui["radio_spectral"].isChecked() else "binned"
        sag_win_range = []
        if sag_acq_mode == "spectral":
            sag_win_range = (self.sag_ui["spectral"][0].value(), self.sag_ui["spectral"][1].value())
        else:
            for min_spin, max_spin in self.sag_ui["binned_spinboxes"]:
                sag_win_range.append( (min_spin.value(), max_spin.value()) )
        if os.path.exists(self.sag_save_path):
            write_log(self.log_box, f"[Error]: {self.sag_save_path} 文件已存在！")
            return


        # =========================================================
        # 2. 定义线程任务函数
        # =========================================================
        def run_cor():
            try:
                cor_params = {
                    "acq_mode" : cor_acq_mode,
                    "win_range" : cor_win_range,
                    "time" : self.cor_ui["fixed_duration"].value(),
                    "interval" : self.cor_ui["time"].value(),
                    "filepath" : self.cor_save_path,
                }
                self.cor_ctrl.start_acquire(**cor_params)
                write_log(self.log_box, "[Success] 正位(COR) 采集完成")
            except Exception as e:
                write_log(self.log_box, f"[Error-COR] {e}")

        def run_sag():
            try:
                sag_params = {
                    "acq_mode": sag_acq_mode,
                    "win_range": sag_win_range,
                    "time" : self.sag_ui["fixed_duration"].value(),
                    "interval" : self.sag_ui["time"].value(),
                    "filepath" : self.sag_save_path,
                }
                self.sag_ctrl.start_acquire(**sag_params)
                write_log(self.log_box, "[Success] 侧位(SAG) 采集完成")
            except Exception as e:
                write_log(self.log_box, f"[Error-SAG] {e}")
            write_log(self.log_box, f"[INFO]: 采集结束！")
        
        write_log(self.log_box, "[Info] 启动双探测器采集线程...")
    
        t1 = threading.Thread(target=run_cor)
        t2 = threading.Thread(target=run_sag)
        
        t1.start()
        t2.start()
        
        