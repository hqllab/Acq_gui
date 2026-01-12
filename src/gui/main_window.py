from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QTextEdit,
    QWidget, QGroupBox, QVBoxLayout
)

from gui.tabs.connect_tab import ConnectTab
from gui.tabs.acquire_tab import AcquireTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acquire GUI")
        # -----------------------------
        # 2. Tabs
        # -----------------------------
        self.tabs = QTabWidget()

        self.connect_tab = ConnectTab(log_box=self.log_box)
        self.cali_acquire_tab = AcquireTab(
            cor_ctrl=self.connect_tab.cor_controller,
            sag_ctrl=self.connect_tab.sag_controller,
            arm_thread=self.connect_tab.arm_thread,
            log_box=self.log_box
        )

        self.tabs.addTab(self.connect_tab, "连接")
        self.tabs.addTab(self.cali_acquire_tab, "采集")
        
        
        # -----------------------------
        # 1. 日志 GroupBox + TextEdit
        # -----------------------------
        self.log_group = QGroupBox("输出日志(Log)")
        self.log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid gray;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)

        log_layout = QVBoxLayout(self.log_group)
        log_layout.setContentsMargins(10, 25, 10, 10)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)

        log_layout.addWidget(self.log_box)  # ✅ 只加一次

        # -----------------------------
        # 3. Central layout
        # -----------------------------
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        layout.addWidget(self.tabs, stretch=3)
        layout.addWidget(self.log_group, stretch=1)  # ✅ 加的是 GroupBox

        self.setCentralWidget(central)

    def closeEvent(self, event):
        if self.connect_tab:
            self.connect_tab.shutdown()
        event.accept()
