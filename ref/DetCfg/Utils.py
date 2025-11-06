import logging
from DetCfg.DetCfg import DetCfg
import json
import os
import numpy as np
from hdf5storage import savemat, loadmat


def saveAsMat(data: np.ndarray, dataName: str, file: str):
    logging.info(f"将数据{dataName}保存到{file}中")
    savemat(file, {dataName: data})


def loadAsMat(dataName: str, file: str) -> np.ndarray:
    logging.info(f"从{file}中加载数据{dataName}")
    d = loadmat(file)
    return d[dataName]


def saveJson(det: DetCfg, path="./", fileName=None):
    """
    engCal: engCal->del; engCalRd->name_eng_cal.mat; engCalWr->""
    """
    if fileName is None:
        fileName = f"{det.name()}"
    fullPath = os.path.join(path, fileName)
    try:
        field = det.field()
        if 'engCal' in field.keys():
            engCalName = f"{fullPath}_engcal.mat"
            saveAsMat(field['engCal'], 'eng_cal', engCalName)
            del field['engCal']
            field['engCalRd'] = engCalName
            field['engCalWr'] = ""
        with open(f"{fullPath}.json", 'w') as jsonFile:
            json.dump(field, jsonFile, indent=4)
        logging.info(f"设备({det.name()})的配置文件保存为{fullPath}.json")
    except Exception as e:
        logging.error(f"设备({det.name()})的配置文件保存失败: {e}")


def loadJson(det: DetCfg, path="./", fileName=None):
    """
    engCalRd: engCalRd->del
    engCalWr: engCalWr->del, engCal->load(engCalWr)
    """
    if fileName is None:
        fileName = f"{det.name()}.json"
    fullPath = os.path.join(path, fileName)
    try:
        logging.info(f"设备({det.name()})从{fullPath}配置文件中加载变量")
        with open(fullPath, 'r') as jsonFile:
            f = json.load(jsonFile).items()
            for k, v in f:
                if k == 'engCalWr':
                    if v != "":
                        det['engCal'] = loadAsMat('eng_cal', v)
                elif k == 'engCalRd':
                    pass
                else:
                    det[k] = v
    except Exception as e:
        logging.error(f"设备({det.name()})加载配置文件失败: {e}")
