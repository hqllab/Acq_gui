from DetCfg.DetCfg import *
import numpy as np


class DetCfgFactory(DetCfg):
    """
    相比基础功能增加了出厂刷写仅厂家可控的配置的功能以及相应基础页
    """

    def __init__(self, mac):
        super().__init__(mac)
        self._field.update({"boardNum": 1})

    def __setitem__(self, key, value):
        if key == "engCal":
            if type(value) != np.ndarray:
                raise TypeError()
            value = value.astype('<u4')[:self._field["boardNum"], :, :]
            if (self[key] != value).any():  # use boardNum reduce
                self._field[key][:self._field["boardNum"], :, :] = value
                self._editPage.add(self._fieldPage[key])
        else:
            return super().__setitem__(key, value)

    def __getitem__(self, key):
        if key == "engCal":
            return self._field[key][:self._field["boardNum"], :, :]
        else:
            return super().__getitem__(key)

    def field(self):
        d = super().field()
        d.update({"engCal": self["engCal"]})
        return d

    def decodePage(self, page: bytes, pageNum: int) -> 'DetCfg':
        if len(page) != 256:
            raise DecodeError("page数据长度不正确")
        boardNum = (pageNum - 2048) // 512
        pageNumReal = (pageNum - 2048) % 512 + 2048
        if pageNum == 0:
            super().decodePage(page, pageNum)
        elif pageNumReal == 2048:
            field = {
                "modelF": struct.unpack_from("<8s", page, 0x0000)[0].hex(),
                "snF":    struct.unpack_from("<16s", page, 0x0008)[0].hex(),
                "swVerF": struct.unpack_from("<4s", page, 0x0018)[0].hex(),
                "fwVerF": struct.unpack_from("<4s", page, 0x0020)[0].hex(),
                "hwVerF": struct.unpack_from("<2s", page, 0x0024)[0].hex(),
            }
            self._field.update(field)
            self._fieldPage.update({key: pageNum for key in field})
            self._editPage.discard(pageNum)
        elif pageNumReal == 2049:
            field = {
                f"qtcVolt{boardNum}": struct.unpack_from("<H", page, 0x0008)[0],
                f"refVolt{boardNum}": struct.unpack_from("<H", page, 0x000A)[0],
            }
            self._field.update(field)
            self._fieldPage.update({key: pageNum for key in field})
            self._editPage.discard(pageNum)
        elif 2052 <= pageNumReal <= 2055:
            idx = pageNumReal - 2052
            fieldName = f"engCal"
            fieldData = self._field.get(fieldName, np.zeros((8, 4, 64), '<u4'))
            t = np.frombuffer(page, dtype='<u4')
            fieldData[boardNum, idx, :] = np.frombuffer(page, dtype='<u4')
            self._field[fieldName] = fieldData
            self._fieldPage.update({fieldName: 2052})
            self._editPage.discard(pageNum)
        else:
            pass
        return self

    def encodePage(self, pageNum: int) -> bytes:
        page = bytearray(256)
        boardNum = (pageNum - 2048) // 512
        pageNumReal = (pageNum - 2048) % 512 + 2048
        if pageNum == 0:
            return super().encodePage(pageNum)
        elif pageNumReal == 2048:
            struct.pack_into("<8s", page, 0x00, bytes.fromhex(self["modelF"]))
            struct.pack_into("<16s", page, 0x08, bytes.fromhex(self["snF"]))
            struct.pack_into("<4s", page, 0x18, bytes.fromhex(self["swVerF"]))
            struct.pack_into("<4s", page, 0x20, bytes.fromhex(self["fwVerF"]))
            struct.pack_into("<2s", page, 0x24, bytes.fromhex(self["hwVerF"]))
        elif pageNumReal == 2049:
            struct.pack_into("<H", page, 0x08, self[f"qtcVolt{boardNum}"])
            struct.pack_into("<H", page, 0x0A, self[f"refVolt{boardNum}"])
        elif 2052 <= pageNumReal <= 2055:
            idx = pageNumReal - 2052
            page[:] = self["engCal"][boardNum, idx, :].tobytes()
        else:
            pass
        return bytes(page)

    def readAllPage(self, s: socket.socket) -> 'DetCfg':
        self.readPage(s, 0)
        self.readFactoryPage(s, 2048)
        for b in range(self["boardNum"]):
            shift = b * 512
            self.readFactoryPage(s, shift + 2049)
            for i in range(2052, 2056):
                self.readFactoryPage(s, shift + i)

    def flushEditPage(self, s):
        for pageNum in self._editPage:
            if pageNum >= 2048:
                if pageNum == 2049:
                    for b in range(self["boardNum"]):
                        shift = b * 512
                        self.writeFactoryPage(s, shift + 2049)
                elif pageNum == 2052:
                    for b in range(self["boardNum"]):
                        shift = b * 512
                        for i in range(2052, 2056):
                            i += shift
                            self.writeFactoryPage(s, i)
                else:
                    self.writeFactoryPage(s, pageNum)
            else:
                self.writePage(s, pageNum)

    def readFactoryPage(self, s, pageNum):
        # todo auth read
        self.readPage(s, pageNum)

    def writeFactoryPage(self, s, pageNum):
        # todo auth write
        self.writePage(s, pageNum)

    @staticmethod
    def getInstance(det: 'DetCfgFactory'):
        modelMap = {
            cls.getModelName(): cls for cls in DetCfgFactory.__subclasses__()}
        modelMap[""] = None
        subCls = modelMap.get(det["model"])
        if subCls is None:
            return det
        else:
            return subCls(det)

    @staticmethod
    def broadcastFind(s: socket.socket) -> list['DetCfgFactory']:
        l = DetCfg.broadcastFind(s)
        return [DetCfgFactory(df) for df in l]


class vXD80Factory(DetCfgFactory):
    modelName = "D80"


class vXD68Factory(DetCfgFactory):
    modelName = "D68"


class vXHD140Factory(DetCfgFactory):
    modelName = "HD140"


class vXHD280Factory(DetCfgFactory):
    modelName = "HD280"

    def __init__(self, mac):
        super().__init__(mac)
        self._field.update({"boardNum": 2})


class vXHD420Factory(DetCfgFactory):
    modelName = "HD420"

    def __init__(self, mac):
        super().__init__(mac)
        self._field.update({"boardNum": 3})


class vXHD560Factory(DetCfgFactory):
    modelName = "HD560"

    def __init__(self, mac):
        super().__init__(mac)
        self._field.update({"boardNum": 4})
