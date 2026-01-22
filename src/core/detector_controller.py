'''
Author: LiuSheng
Date: 2025-11-06 16:12:14
LastEditTime: 2026-01-21 15:42:10
Description: 
'''

from core.det_interface import DetInterface
from core.AcqFunc.AcqFunc import histAcqNoMove, thrAcqNoMove
from core.AcqFunc.AcqFunc import saveHist, saveThr
import threading



default_config = {
    "position_configs": [
        {"pos": 0, "en": 0, "polarity": 0, "clearPos": 1, "zeroShift": 0},
        {"pos": 1, "en": 0, "polarity": 0, "clearPos": 1, "zeroShift": 0}
    ],
    "power_switches": {
        "laser1": 0,
        "laser0": 0,
        "opa": 1,
        "vbias": 1,
        "vcc12": 1,
        "vdd25": 1
    },
    "detector_params": {
        "reg_addr_0x0018": 0x600003FF
    },
    "detector_win_num": 4
}


class DetectorController:
    """控制层：管理探测器连接、状态、参数设置"""

    def __init__(self):
        self.det = None
        self.offline = True

    # ---------------------------------------------------------
    def connect(self, ip: str, port: int, status_label, callback=None):
        """连接设备 (异步执行)"""
        def run():
            try:
                self.det = DetInterface(ip, port)
                self.init_config()
                self.offline = False
                if callback:
                    callback(True, status_label, f"成功连接到 {ip} 并初始化配置。")
            except Exception as e:
                self.det = None
                self.offline = True
                if callback:
                    callback(False, status_label, f"连接失败：{e}")
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
                info = self.det.get_status()
                if callback:
                    callback(True, info)
            except Exception as e:
                callback(False, f"状态获取失败: {e}")
        threading.Thread(target=run, daemon=True).start()

    # ---------------------------------------------------------
    def init_config(self):
        """应用参数配置 (异步)"""
        if self.offline or not self.det:
            return
        try:
            self.det.set_position_config(default_config["position_configs"])
            self.det.set_power_switch(default_config["power_switches"])
            self.det.update_detector_params(default_config["detector_params"])
            
            self.det.DetectRegSet(0x0018, 0x600003FF)
        except Exception as e:
            print(f"初始化配置失败: {e}")
    
    def laser_control(self, callback=None):
        """控制激光器开关"""
        if self.offline or not self.det:
            callback(False, "离线模式无法控制激光器。")
            return
        try:
            default_config["power_switches"]["laser1"] = 1 - default_config["power_switches"]["laser1"]
            default_config["power_switches"]["laser0"] = 1 - default_config["power_switches"]["laser0"]
            self.det.set_power_switch(default_config["power_switches"])
            if callback:
                callback(True, "激光器开关已切换。")
        except Exception as e:
            if callback:
                callback(False, f"激光器控制失败: {e}")
    
    def start_acquire(self, data_mode, win_range, acq_time, interval, filepath, callback=None):
        """启动数据采集"""
        if self.offline or not self.det:
            callback(False, "离线模式无法启动采集。")
            return
        try:
            if data_mode == "spectral":
                self.det.det.setWinRange(0, win_range[0], win_range[1])
                interval = int(interval * 10)
                data = histAcqNoMove(self.det.det, cnt=None, time=acq_time, interval = interval)
                saveHist(data, filepath, None)

            elif data_mode == "binned":
                for i,win in enumerate(win_range):
                    self.det.det.setWinRange(i, win[0], win[1])
                interval = int(interval * 10)
                data = thrAcqNoMove(self.det.det, cnt=None, time=acq_time, interval = interval)
                saveThr(data, filepath)
                
            
            if callback:
                callback(True, "数据采集已启动。")
        except Exception as e:
            if callback:
                callback(False, f"采集启动失败: {e}")
            
            raise(e)
