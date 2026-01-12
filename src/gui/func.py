'''
Author: LiuSheng
Date: 2026-01-12 12:09:49
LastEditTime: 2026-01-12 18:19:40
Description: 
'''
from PySide6.QtWidgets import QTextEdit
from datetime import datetime

def write_log(log_box: QTextEdit, message):
    """带时间戳的日志输出，并自动滚动到底部"""
    # 获取当前时间，格式为：时:分:秒.毫秒
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3] 
    
    # 拼接最终文本
    full_msg = f"[{timestamp}] {message}"
    
    # 追加文本
    log_box.append(full_msg)
    
    # 自动滚动到底部 (之前提到的功能)
    scrollbar = log_box.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())


# def gen_script_file(filename: str, cor_pos: int, sag_pos: int, voltage: float, current: float):
#     """生成机械臂控制脚本文件"""
#     pass
    # with open