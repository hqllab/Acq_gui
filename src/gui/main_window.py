# gui/main_window.py
from PySide6.QtWidgets import QMainWindow, QTabWidget
from gui.tabs.connect_tab import ConnectTab
from gui.tabs.acquire_tab import AcquireTab
from gui.tabs.analysis_tab import AnalysisTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acquire GUI")

        self.tabs = QTabWidget()
        self.connect_tab = ConnectTab()
        self.acquire_tab = AcquireTab(det_ctrl=self.connect_tab.controller)
        self.analysis_tab = AnalysisTab()  # ✅ 新增

        self.tabs.addTab(self.connect_tab, "连接")
        self.tabs.addTab(self.acquire_tab, "采集")
        self.tabs.addTab(self.analysis_tab, "绘图")  # ✅ 新增 Tab

        self.setCentralWidget(self.tabs)