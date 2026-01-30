'''
Author: LiuSheng
Date: 2026-01-15 10:59:57
LastEditTime: 2026-01-21 12:03:00
Description: 
'''
from PySide6.QtWidgets import QTabWidget, QTextEdit, QGroupBox, QVBoxLayout
from acq.gui.tabs.connect_tab import ConnectTab
from acq.gui.tabs.acquire_tab import AcquireTab
from acq.gui.tabs.exam_acquire_tab import ExamAcquireTab

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
    log_layout.setContentsMargins(10, 20, 10, 10)

    log_box = QTextEdit()
    log_box.setReadOnly(True)
    log_layout.addWidget(log_box)  # ✅ 只加一次
    
    return {
        "log_group": log_group,
        "log_box": log_box
    }

def create_tabs(log_box):
    tabs = QTabWidget()

    connect_tab = ConnectTab(log_box=log_box)
    exam_acq_tab = ExamAcquireTab(
        connect_tab_instance = connect_tab,
        log_box=log_box
    )

    tabs.addTab(connect_tab, "连接")
    # tabs.addTab(acquire_tab, "骨成像平台")
    # tabs.addTab(exam_acq_tab, "实验平台")
    return {
        "tabs": tabs,
        "connect_tab": connect_tab,
        # "acquire_tab": acquire_tab,
        # "exam_acq_tab": exam_acq_tab
    }

