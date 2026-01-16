'''
Author: LiuSheng
Date: 2026-01-12 16:41:02
LastEditTime: 2026-01-16 13:53:56
Description: 
'''

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout


from .main_window_helper import create_log_groupbox, create_tabs


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acquire GUI")
        
        # -----------------------------
        # 1. 日志 GroupBox + TextEdit
        # -----------------------------
        log_ui = create_log_groupbox()
        log_group = log_ui["log_group"]
        self.log_box = log_ui["log_box"]
        
        # -----------------------------
        # 2. Tabs
        # -----------------------------
        tabs_ui = create_tabs(self.log_box)
        tabs = tabs_ui["tabs"]
        self.connect_tab = tabs_ui["connect_tab"]
        # self.acquire_tab = tabs_ui["acquire_tab"]
        self.acquire_tab2 = tabs_ui["acquire_tab2"]

        # -----------------------------
        # 3. Central layout
        # -----------------------------
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.addWidget(tabs, stretch=3)
        layout.addWidget(log_group, stretch=1)  # ✅ 加的是 GroupBox

        self.setCentralWidget(central)

    # def closeEvent(self, event):
    #     if self.connect_tab:
    #         self.connect_tab.shutdown()
    #     event.accept()
