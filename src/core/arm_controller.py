# # core/acq_controller.py
# import numpy as np
# import matplotlib.pyplot as plt
# import threading
# import traceback
# from src.core.arm.slz_wrapper import SLZWorkerThread

# class ArmController:
#     """
#     控制采集流程（Controller 层）
#     与 GUI 解耦，通过回调向界面输出状态信息。
#     """

#     def __init__(self):
#         """
#         det_ctrl: ConnectTab.controller 实例
#         """
#         self.slz = None
#         self.offline = True

    
#     def connect(self, callback=None):
#         """连接设备 (异步执行)"""
#         def run():
#             try:
#                 self.det = SLZWorkerThread()
#                 self.offline = False
#                 # if callback:
#                 #     callback(True, status_label, f"成功连接到 {ip} 并初始化配置。")
#             except Exception as e:
#                 self.slz = None
#                 self.offline = True
#                 # if callback:
#                 #     callback(False, status_label, f"连接失败：{e}")
#         threading.Thread(target=run, daemon=True).start()

    
#     def 

    
