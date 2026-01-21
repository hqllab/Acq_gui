'''
Author: LiuSheng
Date: 2026-01-12 16:41:02
LastEditTime: 2026-01-21 12:01:06
Description: 
'''

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout


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
        log_box = log_ui["log_box"]
        
        # -----------------------------
        # 2. Tabs
        # -----------------------------
        tabs_ui = create_tabs(log_box)
        tabs = tabs_ui["tabs"]

        # -----------------------------
        # 3. Central layout
        # -----------------------------
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        layout.addWidget(tabs, stretch=3)
        layout.addWidget(log_group, stretch=2)  # ✅ 加的是 GroupBox
        self.setCentralWidget(central)

