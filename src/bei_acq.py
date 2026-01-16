# %%
from core.Det import Det, DetData
import numpy as np
import matplotlib.pyplot as plt
from rich.table import Table
from rich import print
from hdf5storage import loadmat
import time
from core.AcqFunc import *


srv = DetData("10.20.22.230",7494)
dets = srv.findDet()
print(dets)
det = list(dets.items())[0][1]
srv.listen()


def dictPrint(d: dict, title="", k="", v=""):
    t = Table(title=title)
    t.add_column(k)
    t.add_column(v)
    [t.add_row(k, str(v)) for k, v in d.items()]
    print(t)
dictPrint(det.statusTemperature(), "温度")
dictPrint(det.statusPosition(0.0375), "位置")
dictPrint(det.statusPower(), "电源")
dictPrint(det.statusPowerSwitch(), "开关")
dictPrint(det.statusFanSpeed(), "风扇")



det.setPositionConfig([
    {"pos": 0, "en": 1, "polarity": 0, "clearPos": 1, "zeroShift": 0},
    {"pos": 1, "en": 0, "polarity": 0, "clearPos": 1, "zeroShift": 0}])
det.setPowerSwitch({
    "laser1": 0, "laser0": 0, "opa": 1, "vbias": 1, "vcc12": 1, "vdd25": 1})
det.DetectRegSet(0x0018, 0x600003FF)
det.setWinNum(4)


for i in range(100000):
    name = f"D:\\Acq_gui\\bei_acq\\bei_{i}.mat"

    subname = f"{name}"
    det.setWinRange(0, 0, 100)
    # time.sleep(4)
    print("detector run")
    # time.sleep(1)
    data = histAcqNoMove(det, cnt=None, time=5, interval = int(100 * 10))
    saveHist(data, subname, None)
    # print(subname)
    # showHist(
    #     data,
    #     pos_en=True,
    #     pos_step=0.0375,
    #     cal_sel=(400, 450),
    #     rate=1400/20,
    #     log_en=False,
    #     pos_limit=(0, 0),
    #     caxis=(0, 0),
    #     save_png=""
    # )