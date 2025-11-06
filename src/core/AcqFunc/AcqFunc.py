import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用 agg 后端，避免启动 GUI

import matplotlib.pyplot as plt
from hdf5storage import loadmat, savemat
import subprocess
import time
import logging
import os

def _move(speed, pos):
    speed = int(speed)
    pos = int(pos)
    pause = int(pos / speed) + 2
    subrum = f"""run_speed = {speed}; end_pos = {pos}; pause_time = {pause}; run('D:/DEXA/AcqCode/Untitled.m'); exit;"""
    cmd = f"""matlab -nosplash -nodesktop -nojvm -r "{subrum}"\n"""
    subprocess.run(cmd)
    time.sleep(3.5)
    return pause

def histAcq(det, speed, pos, interval = 5 * 10):
    movetime = _move(speed, pos)
    acq_time = 1 + movetime
    acq_cnt = int(acq_time * 1000 * 10 / interval)
    data = det.histAcq(acq_cnt, interval) # cnt & 0.1ms
    sdataIdx = data["idx"].argsort()
    for i in range(data.shape[0]):
        data[i, :] = data[i, sdataIdx[i]]
    # delay back
    time.sleep(pos / 10000 + 1)
    return data

def histAcqNoMove(det, cnt=None, time=None, interval = 5 * 10):
    if cnt is None:
        acq_cnt = int(time * 1000 * 10 / interval)
    elif time is None:
        acq_cnt = cnt
    else:
        raise ValueError("请传入时间或次数")
    data = det.histAcq(acq_cnt, interval)
    sdataIdx = data["idx"].argsort()
    for i in range(data.shape[0]):
        data[i, :] = data[i, sdataIdx[i]]
    return data

def move(speed, pos):
    pause = _move(speed, pos)
    acq_time = 1 + pause
    time.sleep(acq_time)
    # delay back
    time.sleep(pos / 10000 + 1)

def _pixCalibration(tdata, calFile: str):
    cal = loadmat(calFile)['fpu32']
    cal_bit = 8
    cal_bit_max = 2 ** cal_bit
    cal_k = np.bitwise_and(cal >> 16, 255).astype(np.int64) + 256
    cal_b = np.bitwise_and(cal, 65535).astype(np.int16).astype(np.int64)

    tdata = np.pad(tdata, ((0, 1), (0, 0), (0, 0)))
    padIdx = tdata.shape[0] - 1

    cal_shape0 = np.ceil(((tdata.shape[0] * cal_bit_max - cal_b) / cal_k).max()) + 1
    cal_x = np.arange(0, cal_shape0, dtype=np.int64)
    raw_x_step = (cal_k * cal_x + cal_b).T
    raw_x_int = raw_x_step >> cal_bit
    raw_x_fr = np.bitwise_and(raw_x_step, cal_bit_max - 1)
    raw_x_intnext = raw_x_int[1:, :]
    raw_x_frnext = raw_x_fr[1:, :, None]
    raw_x_int = raw_x_int[:-1, :]
    raw_x_fr = raw_x_fr[:-1, :, None]

    col = np.arange(tdata.shape[1])[None, :]
    first_idx = np.where((raw_x_int > padIdx) | (raw_x_int < 0), padIdx, raw_x_int)
    first_cnt = tdata[first_idx, col, :]  * (cal_bit_max - raw_x_fr)
    last_idx = np.where((raw_x_intnext > padIdx) | (raw_x_intnext < 0), padIdx, raw_x_intnext)
    last_cnt = tdata[last_idx, col, :] * raw_x_frnext
    mid_idx = np.where(raw_x_intnext - raw_x_int <= 1, padIdx, raw_x_int + 1)
    mid_idx = np.where((mid_idx > padIdx) | (mid_idx < 0), padIdx, mid_idx)
    mid_cnt = tdata[mid_idx, col, :] * cal_bit_max
    total_cal_cnt = (first_cnt + mid_cnt + last_cnt)

    cal_cnt = np.round(total_cal_cnt / cal_bit_max)
    return cal_cnt

def _save(name, data):
    real_name = f"{name}.mat"
    if os.path.exists(real_name):
        y = input("文件存在是否覆盖")
        if y == 'y' or y == 'Y':
            os.remove(real_name)
        else:
            logging.warning("跳过保存")
            return
    savemat(real_name, data, oned_as="column")

def saveHist(data, name, calFile: str | None = ""):
    d = {
        "d": {
            "ypos": data[:, 0]["pos1h"],
            "yposend": data[:, 0]["pos1t"],
            "pos": data[:, 0]["pos0h"],
            "posend": data[:, 0]["pos0t"],
            "data": np.transpose(data["data"], (2, 1, 0))
        }
    }
    plt.figure()
    plt.imshow(d["d"]["data"].sum(axis=0), aspect="auto")
    plt.colorbar()
    plt.show()
    _save(name, d)
    if calFile is not None and calFile != "":
        d["d"]["data"] = _pixCalibration(d["d"]["data"], calFile)
        _save(f"{name}_caldata", d)

def _show(img, pos, rate, log_en):
    # 探测器像素每4个为一组，对应偏移1.6mm
    offset_cycle = 1.6 / rate * np.arange(4, dtype=np.float64)
    offset_arr = np.tile(offset_cycle, img.shape[1] // 4)

    # 查找错位校正后的位置并移除以确保插值后没有错位区域
    start_idx_value = 2 * offset_cycle[-1] - offset_cycle[-2]
    start_idx = np.searchsorted(pos, pos[0] + start_idx_value, side='left')
    end_idx = np.searchsorted(pos, pos[-1] + offset_arr.min(), side='right')
    pos_valid = pos[start_idx:end_idx]
    if pos_valid.shape[0] == 0:
        pos_valid = pos
        logging.error("没有足够的帧用于重建")

    # 根据各列对应偏移修正采样位置，并用插值映射到目标坐标pos
    img_corr = np.empty((pos_valid.shape[0], img.shape[1]), dtype=img.dtype)
    for j in range(img.shape[1]):
        pos_shifted = pos + offset_arr[j]
        img_corr[:, j] = np.interp(pos_valid, pos_shifted, img[:, j], left=np.nan, right=np.nan)

    # 构造水平方向坐标：每个像素0.55mm
    x_edges = np.arange(img_corr.shape[1] + 1) * 0.55

    # 构造垂直方向边界
    dy = np.diff(pos_valid)
    y_edges = np.empty(pos_valid.shape[0] + 1)
    y_edges[1:-1] = (pos_valid[:-1] + pos_valid[1:]) / 2.0
    y_edges[0] = pos_valid[0] - 0.5 * dy[0]
    y_edges[-1] = pos_valid[-1] + 0.5 * dy[-1]

    if log_en:
        img_corr[img_corr < np.e] = np.e
        img_corr = np.log(img_corr)

    return (x_edges, y_edges, img_corr)

def showHist(
    data,
    pos_en = True,
    pos_step = 0.0375, # mm
    cal_sel: tuple | None = (0, 0), # mm/frame
    rate: float = 1.18,
    log_en: bool = True,
    caxis: tuple | None = (0, 0),
    save_png: str = ""
):
    histData = np.transpose(data["data"], (2, 1, 0))

    # 扫描位置
    if pos_en:
        pos = data["pos0h"][:, 0].astype(np.float64) * pos_step
    else:
        pos = np.arange(histData.shape[2]) * pos_step

    # 校正
    if cal_sel is not None and (cal_sel[0] != 0 or cal_sel[1] != 0):
        pos_sel = np.where((cal_sel[0] <= pos) & (pos < cal_sel[1]))[0]
        cal_den = histData[:, :, pos_sel].sum(axis=2)
        cal_num = cal_den.mean(axis=1)[:, None]
        cal_num = np.where(cal_num == 0, 1, cal_num)
        cal_den = np.where(cal_den == 0, cal_num, cal_den)
        cal = (cal_num / cal_den)[:, :, None]
        img = (histData.astype(np.float64) * cal).sum(axis=0).T
    else:
        img = histData.sum(axis=0).astype(np.float64).T

    (x, y, img) = _show(img, pos, rate, log_en)

    # 绘图
    if pos_en:
        plt.figure()
        plt.plot(pos)
        plt.show()

    fig = plt.figure(dpi=300)
    mesh = plt.pcolormesh(x, y, img, shading='auto')
    mesh.set_cmap('gray')
    mesh.set_antialiased(False)
    mesh.set_edgecolor('none')
    plt.gca().set_aspect('equal')
    plt.xlabel('Width (mm)')
    plt.ylabel('Position (mm)')
    plt.colorbar(mesh, label='Counts')
    if cal_sel is not None and (caxis[0] != 0 or caxis[1] != 0):
        plt.clim(caxis[0], caxis[1])
    plt.show()
    if save_png != "":
        fig.savefig(f'{save_png}.png', dpi=3000, bbox_inches='tight')
