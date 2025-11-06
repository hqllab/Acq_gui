# core/acq_controller.py
import threading
from core.AcqFunc.AcqFunc import histAcqNoMove, saveHist, showHist
import traceback


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
