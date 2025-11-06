# core/acq_controller.py
import numpy as np
import matplotlib.pyplot as plt
import threading
from core.AcqFunc.AcqFunc import histAcqNoMove, saveHist, showHist
import traceback


# def show_res(
#     data,
#     pos_en = True,
#     pos_step = 0.0375, # mm
#     cal_sel: tuple | None = (0, 0), # mm/frame
#     rate: float = 1.18,
#     log_en: bool = True,
#     caxis: tuple | None = (0, 0),
#     save_png: str = ""
# ):
#     histData = np.transpose(data["data"], (2, 1, 0))

#     # 扫描位置
#     if pos_en:
#         pos = data["pos0h"][:, 0].astype(np.float64) * pos_step
#     else:
#         pos = np.arange(histData.shape[2]) * pos_step

#     # 校正
#     if cal_sel is not None and (cal_sel[0] != 0 or cal_sel[1] != 0):
#         pos_sel = np.where((cal_sel[0] <= pos) & (pos < cal_sel[1]))[0]
#         cal_den = histData[:, :, pos_sel].sum(axis=2)
#         cal_num = cal_den.mean(axis=1)[:, None]
#         cal_num = np.where(cal_num == 0, 1, cal_num)
#         cal_den = np.where(cal_den == 0, cal_num, cal_den)
#         cal = (cal_num / cal_den)[:, :, None]
#         img = (histData.astype(np.float64) * cal).sum(axis=0).T
#     else:
#         img = histData.sum(axis=0).astype(np.float64).T

#     (x, y, img) = _show(img, pos, rate, log_en)

#     # 绘图
#     if pos_en:
#         plt.figure()
#         plt.plot(pos)
#         plt.show()

#     fig = plt.figure(dpi=300)
#     mesh = plt.pcolormesh(x, y, img, shading='auto')
#     mesh.set_cmap('gray')
#     mesh.set_antialiased(False)
#     mesh.set_edgecolor('none')
#     plt.gca().set_aspect('equal')
#     plt.xlabel('Width (mm)')
#     plt.ylabel('Position (mm)')
#     plt.colorbar(mesh, label='Counts')
#     if cal_sel is not None and (caxis[0] != 0 or caxis[1] != 0):
#         plt.clim(caxis[0], caxis[1])
#     plt.show()
#     if save_png != "":
#         fig.savefig(f'{save_png}.png', dpi=3000, bbox_inches='tight')
    


class AcquisitionController:
    """
    控制采集流程（Controller 层）
    与 GUI 解耦，通过回调向界面输出状态信息。
    """

    def __init__(self, det_ctrl):
        """
        det_ctrl: ConnectTab.controller 实例
        """
        self.det_ctrl = det_ctrl
        self.last_data = None

    # ----------------------------------------------------------------------
    def acquire(
        self, file_path, voltage, current, filter_range,
        speed, duration, interval, win_params, callback=None
    ):
        """
        启动采集流程（异步）

        参数：
            file_path: 保存路径（.mat）
            voltage/current: 管电压 / 电流
            filter_range: (f1, f2)
            speed: 移动速度 mm/s
            duration: 采集时长 s
            interval: 采样间隔 ×10ms
            win_params: (win_id, low, high)
            callback: 回调函数(level, message)
        """

        def run():
            try:
                if self.det_ctrl is None or self.det_ctrl.offline:
                    raise RuntimeError("未连接探测器（离线模式）")

                det = self.det_ctrl.det.det  # 注意两层 det：controller.det -> interface.det
                win_id, win_low, win_high = win_params

                # 设置窗口范围
                det.setWinRange(win_id, win_low, win_high)

                # 日志反馈
                if callback:
                    callback("[RUNNING]", f"开始采集: WinRange({win_id}, {win_low}, {win_high})")

                # 执行采集
                data = histAcqNoMove(det, cnt=None, time=duration, interval=int(interval))
                self.last_data = data

                # 保存结果
                saveHist(data, file_path, None)

                # 日志反馈
                if callback:
                    callback("[INFO]", f"数据已保存到: {file_path}")
                    callback("[DONE]", "采集完成！")

            except Exception as e:
                tb = traceback.format_exc()
                if callback:
                    callback("[ERROR]", f"采集失败: {e}\n{tb}")

        # 异步执行，防止阻塞 GUI
        threading.Thread(target=run, daemon=True).start()
