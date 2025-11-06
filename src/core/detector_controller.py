'''
Author: LiuSheng
Date: 2025-11-06 16:12:14
LastEditTime: 2025-11-06 16:12:17
Description: 
'''
# core/detector_controller.py
from core.det_interface import DetInterface
import threading


class DetectorController:
    """控制层：管理探测器连接、状态、参数设置"""

    def __init__(self):
        self.det = None
        self.offline = True

    # ---------------------------------------------------------
    def connect(self, ip: str, callback=None):
        """连接设备 (异步执行)"""
        def run():
            try:
                self.det = DetInterface(ip)
                self.offline = False
                if callback:
                    callback(True, f"成功连接到 {ip}")
            except Exception as e:
                self.det = None
                self.offline = True
                if callback:
                    callback(False, f"连接失败：{e}")
        threading.Thread(target=run, daemon=True).start()

    # ---------------------------------------------------------
    def get_status(self, callback=None):
        """读取设备状态 (异步)"""
        if self.offline or not self.det:
            if callback:
                callback(False, "离线模式无法获取状态。")
            return

        def run():
            try:
                status = self.det.get_status()
                if callback:
                    callback(True, status)
            except Exception as e:
                callback(False, f"状态获取失败: {e}")
        threading.Thread(target=run, daemon=True).start()

    # ---------------------------------------------------------
    def apply_config(self, pos_cfgs, power_dict, det_params, callback=None):
        """应用参数配置 (异步)"""
        if self.offline or not self.det:
            if callback:
                callback(False, "离线模式无法应用参数。")
            return

        def run():
            try:
                self.det.set_position_config(pos_cfgs)
                self.det.set_power_switch(power_dict)
                self.det.update_detector_params(det_params)
                if callback:
                    callback(True, "所有参数已成功应用。")
            except Exception as e:
                if callback:
                    callback(False, f"参数应用失败: {e}")
        threading.Thread(target=run, daemon=True).start()
