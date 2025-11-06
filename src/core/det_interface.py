# core/det_interface.py
from core.Det import DetData

class DetInterface:
    """封装 DetData 的硬件操作接口"""

    def __init__(self, ip: str):
        """连接指定 IP 的探测器"""
        srv = DetData(ip)
        dets = srv.findDet()
        if not dets:
            raise ConnectionError(f"未在 {ip} 找到探测器")
        self.det = list(dets.values())[0]
        srv.listen()

    # -------------------- 状态信息 --------------------
    def get_status(self):
        """组合温度、电源、风扇状态"""
        # d = {}
        # d.update(self.det.statusTemperature())
        # d.update(self.det.statusPower())
        # d.update(self.det.statusFanSpeed())
        
        return {
            "温度": self.det.statusTemperature(),
            "位置": self.det.statusPosition(0.0375),
            "电源": self.det.statusPower(),
            "开关": self.det.statusPowerSwitch(),
            "风扇": self.det.statusFanSpeed(),
        }

    # -------------------- 参数设置 --------------------
    def set_position_config(self, pos_cfgs):
        """设置位置参数"""
        self.det.setPositionConfig(pos_cfgs)

    def set_power_switch(self, power_dict):
        """设置电源开关状态"""
        self.det.setPowerSwitch(power_dict)

    def update_detector_params(self, params):
        """更新探测参数"""
        for k, v in params.items():
            self.det.detParam[k] = v
