'''
Author: LiuSheng
Date: 2025-11-06 14:35:28
LastEditTime: 2026-01-09 17:56:36
Description: 主窗口类，包含连接、采集、绘图三个tab页
'''

# gui/main_window.py
from PySide6.QtWidgets import QMainWindow, QTabWidget
from gui.tabs.connect_tab import ConnectTab
from gui.tabs.cali_acquire_tab import CaliAcquireTab
from gui.tabs.recon_acquire_tab import ReconAcquireTab

from gui.tabs.analysis_tab import AnalysisTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acquire GUI")

        self.tabs = QTabWidget()
        self.connect_tab = ConnectTab()
        # self.cali_acquire_tab = CaliAcquireTab(det_ctrl=self.connect_tab.controller)
        # self.recon_acquire_tab = ReconAcquireTab(det_ctrl=self.connect_tab.controller)
        # self.analysis_tab = AnalysisTab()  

        self.tabs.addTab(self.connect_tab, "连接")
        # self.tabs.addTab(self.cali_acquire_tab, "能谱采集")
        # self.tabs.addTab(self.recon_acquire_tab, "重建采集")
        # self.tabs.addTab(self.analysis_tab, "绘图")

        self.setCentralWidget(self.tabs)