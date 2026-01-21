'''
Author: LiuSheng
Date: 2026-01-12 12:09:49
LastEditTime: 2026-01-21 16:29:11
Description: 
'''
import numpy as np
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
    
def load_mat_from_file(cur_file, step=0.0375):
    """
    step: 表示 相邻帧数据 步长
    """
    import h5py
    with h5py.File(cur_file, 'r') as f:
        pixels_array = f['d']['data'][:]
        pos = f['d']['pos'][:] * step
        ypos = f['d']['ypos'][:] * step
        posend = f['d']['posend'][:] * step
        yposend = f['d']['yposend'][:] * step
        
        pos_array = np.vstack((pos, ypos, posend, yposend)).T
    return pos_array, pixels_array