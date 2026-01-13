from PySide6.QtWidgets import QTabWidget, QTextEdit, QGroupBox, QVBoxLayout
from gui.tabs.connect_tab import ConnectTab
from gui.tabs.acquire_tab import AcquireTab

def create_log_groupbox():
    log_group = QGroupBox("输出日志(Log)")
    log_group.setStyleSheet("""
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

    log_layout = QVBoxLayout(log_group)
    log_layout.setContentsMargins(10, 25, 10, 10)

    log_box = QTextEdit()
    log_box.setReadOnly(True)
    log_layout.addWidget(log_box)  # ✅ 只加一次
    
    return log_group, log_box

def create_tabs(log_box):
    tabs = QTabWidget()

    connect_tab = ConnectTab(log_box=log_box)
    acquire_tab = AcquireTab(
        cor_ctrl=connect_tab.cor_controller,
        sag_ctrl=connect_tab.sag_controller,
        arm_thread=connect_tab.arm_thread,
        log_box=log_box
    )

    tabs.addTab(connect_tab, "连接")
    tabs.addTab(acquire_tab, "采集")
    return tabs, connect_tab, acquire_tab

