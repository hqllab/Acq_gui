# %%
from Det import Det, DetData
import numpy as np
import matplotlib.pyplot as plt
from rich.table import Table
from rich import print
from hdf5storage import loadmat
import time
from AcqFunc import *

# %%
srv = DetData("10.20.22.230")
dets = srv.findDet()
det = list(dets.items())[0][1]
# det = Det("10.20.22.240")
# det.addQueue(srv.addDet("10.20.22.240"))
srv.listen()

# %% 状态信息
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

# %% 电源及参数设置
det.setPositionConfig([
    {"pos": 0, "en": 1, "polarity": 1, "clearPos": 1, "zeroShift": 0},
    {"pos": 1, "en": 0, "polarity": 0, "clearPos": 1, "zeroShift": 0}])
det.setPowerSwitch({
    "laser1": 0, "laser0": 0, "opa": 1, "vbias": 1, "vcc12": 1, "vdd25": 1})
det.detParam["packagePix"] = 64
det.detParam["pixNum"] = 256 * 1
det.detParam["winNum"] = 4
det.detParam["maxThr"] = 511
det.DetectRegSet(0x0018, 0x600003FF)
det.setWinNum(4)

# %%
for i in range(1):
    # tube = f""
    tube = f"_40kV_7.5mA"
    # tube = f"AM241_30min_{i}"
    filter = f"_1650_1950"
    # filter = f"_900_1200"
    speed = f"_666mmps"
    name = f"Acq1106/test17{speed}{filter}{tube}"

    subname = f"{name}"
    det.setWinRange(0, 0, 119)
    # time.sleep(3)
    # print("detector run")
    # time.sleep(3.5)
    data = histAcqNoMove(det, cnt=None, time=8, interval = int(2 * 10))
    saveHist(data, subname, None)
    print(subname)
    showHist(
        data,
        pos_en=False,
        pos_step=0.0375,
        cal_sel=(350, 400),
        rate=680/500,
        log_en=False,
        caxis=(0, 0)
    )
    plt.figure()
    plt.plot(data["data"].sum(axis=0).T)
    plt.show()
    plt.figure()
    plt.plot(data["data"].sum(axis=0).sum(axis=1).T)
    plt.show()


# %%
data_save = loadmat(
    r"D:\vxhd\Acq1106\test17_666mmps_1650_1950_40kV_7.5mA.mat"
)
data = {
    "data": np.transpose(data_save["d"]["data"], (2, 1, 0)),
    "pos0h": data_save["d"]["pos"][:, None]
}
data["data"] = data["data"][:, 254:255, :]
plt.figure()
plt.plot(data["data"].sum(axis=0).T)
plt.show()
plt.figure()
plt.plot(data["data"].sum(axis=0).sum(axis=1).T)
plt.show()
showHist(
    data,
    pos_en=True,
    pos_step=0.0375,
    cal_sel=(350, 400),
    rate=680/500,
    log_en=False,
    caxis=(0, 0),
    save_png=""
)

# %%
