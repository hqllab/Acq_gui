import time
import struct
import logging
import numpy as np
from queue import Queue, Empty


class DecodeError(Exception):
    pass


class Det():
    def __init__(self, ip: str):
        self._ip = ip

    def _stAddr(self):
        return (self._ip, 7493)

    def getInstance(self, model: str) -> 'Det':
        modelRef = self.getModelRef()
        param = modelRef.get(model)
        if param is None:
            self.detParam = {}
        else:
            self.detParam = param
        return self

    def addQueue(self, q: tuple[Queue, Queue]):
        (self._qr, self._qt) = q
        return self

    def DetectRegSet(self, addr: int, data: int):
        stId = 1
        stData = struct.pack("<HHL", 1, addr, data)  # write
        self._qt.put((self._ip, stId, stData))
        self._qr.queue.clear()
        try:
            id = 0
            while id != stId:
                (ip, id, data) = self._qr.get(timeout=2)
            logging.debug(f"设备({self._ip})写入地址{addr}成功")
        except Empty as e:
            logging.warning(f"设备({self._ip})写地址{addr}超时: {e}")

    def DetectRegRead(self, addr: int) -> int:
        stId = 1
        stData = struct.pack("<HH", 0, addr)  # read
        self._qt.put((self._ip, stId, stData))
        self._qr.queue.clear()
        try:
            id = 0
            while id != stId:
                (ip, id, data) = self._qr.get(timeout=2)
                (flag, rAddr, data) = struct.unpack("<HHL", data)
            logging.debug(f"设备({self._ip})读取地址{addr}成功")
        except Empty as e:
            logging.warning(f"设备({self._ip})读取地址{addr}超时: {e}")
        return data

    def setWinNum(self, num: int) -> 'Det':
        winNum = self.detParam["winNum"]
        if winNum < num:
            model = self.detParam["model"]
            logging.error(f"探测器{model}最大只支持{winNum}能窗")
            return
        if num <= 0:
            logging.error(f"能窗数量设置错误, 必须大于等于一")
            return
        self.DetectRegSet(0x0020, num - 1)
        logging.info(f"设置能窗数量为{num}")
        return self

    def setWinRange(self, win: int, low: int, high: int) -> 'Det':
        winNum = self.detParam["winNum"]
        maxThr = self.detParam["maxThr"]
        if winNum <= win:
            model = self.detParam["model"]
            logging.error(f"探测器{model}最大只支持{winNum}能窗(能窗号从0开始)")
            return
        if win < 0:
            logging.error(f"能窗号设置错误, 必须大于零")
            return
        if not (0 <= low <= maxThr and 0 <= high <= maxThr):
            logging.error(f"能窗范围必须大于等于0且小于等于{maxThr}")
            return
        if low > high:
            logging.error(f"能窗上限必须大于等于能窗下限")
            return
        self.DetectRegSet(0x0021 + win, high << 16 | low)
        logging.info(f"设置能窗{win}为[{low}, {high}]")
        return self
    
    def statusPower(self) -> dict[str, float]:
        voltage = self.DetectRegRead(0x97) * 1.25 / 1000
        currnet = self.DetectRegRead(0x98) * 1.0 / 1000
        power = self.DetectRegRead(0x99) * 25 / 1000
        return {"voltage": voltage, "currnet": currnet, "power": power}
    
    def setPowerSwitch(self, power: dict) -> 'Det':
        """
        power = {"vcc12": 1, "laser1": 0, "laser0": 0, "vdd25": 1, "opa": 1, "vbias": 1}
        """
        cr = ((power["vcc12"] != 0) << 6) | ((power["laser1"] != 0) << 5) | ((power["laser0"] != 0) << 4)
        cr |= ((power["vdd25"] != 0) << 3) | ((power["opa"] != 0) << 1) | ((power["vbias"] != 0) << 0)
        self.DetectRegSet(0x60, cr)
        return self
    
    def statusPowerSwitch(self) -> dict[str, str|bool]:
        """
        status = {"vcc12": 1, "laser1": 0, "laser0": 0, "vdd25": "11111111", "opa": "1111111111111111", "vbias": "00000000"}
        """
        localPower = self.DetectRegRead(0x61)
        ioBoardPower = self.DetectRegRead(0x62)
        status = {}
        status["vcc12"] = (ioBoardPower & (1 << 6)) != 0
        status["laser1"] = (ioBoardPower & (1 << 5)) != 0
        status["laser0"] = (ioBoardPower & (1 << 4)) != 0
        status["vdd25"] = format((localPower >> 24) & 255, '08b')
        status["opa"] = format((localPower >> 8) & 65535, '016b')
        status["vbias"] = format((localPower >> 0) & 255, '08b')
        return status
    
    def setPositionConfig(self, encoderCfg: list[dict]) -> 'Det':
        """
        encoderCfg = [
            {"pos": 0, "en": 0, "polarity": 0, "clearPos": 1, "zeroShift": 0},
            {"pos": 1, "en": 1, "polarity": 1, "clearPos": 1, "zeroShift": 0},
        ]
        """
        def real2pos(position):
            return struct.unpack('I', struct.pack('i', position))[0]
        for cfg in encoderCfg:
            pos = cfg.get("pos")
            if pos is None:
                logging.error(f"配置中没有设置对应的pos编号")
                continue
            if not (0 <= pos < 2):
                logging.error(f"pos编号必须在[0,2)之间")
                continue
            self.DetectRegSet(0x43 + pos * 8, real2pos(cfg["zeroShift"]))
            cr = ((cfg["en"] != 0) << 2) | ((cfg["clearPos"] != 0) << 1) | (cfg["polarity"] != 0)
            self.DetectRegSet(0x41 + pos * 8, cr)
        return self
    
    def statusPosition(self, lsb: float = None) -> dict[str, int|float|bool]:
        """
        status = {"pos0": 3333, "pos1": 22222, "pos0A": 0, "pos0B": 1, "pos1A": 1, "pos1B": 0}
        """
        def pos2real(position):
            pos = struct.unpack('i', struct.pack('I', position))[0]
            if lsb is None:
                return pos
            else:
                return pos * lsb
        status = {}
        for i in range(2):
            sig = self.DetectRegRead(0x40 + i * 8)
            status[f"pos{i}A"] = (sig & 1) != 0
            status[f"pos{i}B"] = (sig & 2) != 0
            status[f"pos{i}"] = pos2real(self.DetectRegRead(0x42 + i * 8))
        return status

    def statusTemperature(self) -> dict[str, float|int]:
        def temp2real(tempRaw):
            return struct.unpack('h', struct.pack('H', tempRaw))[0] / 128
        status = {}
        boardNum = self.DetectRegRead(0x80)
        status["boardNum"] = boardNum
        ioBoardTemper = self.DetectRegRead(0x91)
        status["temperIO_0"] = temp2real(ioBoardTemper & 0xFFFF)
        status["temperIO_1"] = temp2real(ioBoardTemper >> 16)
        for i in range(boardNum):
            for j in range(2):
                temper = self.DetectRegRead(0x81 + i * 2 + j)
                status[f"temper{i}_{j * 2}"] = temp2real(temper & 0xFFFF)
                status[f"temper{i}_{j * 2 + 1}"] = temp2real(temper >> 16)
        return status

    def statusFanSpeed(self) -> dict[str, int]:
        def raw2speed(raw):
            return struct.unpack('h', struct.pack('H', raw))[0]
        status = {}
        fanNum = self.DetectRegRead(0x92)
        status["fanNum"] = fanNum
        for i in range(0, fanNum, 2):
            value = self.DetectRegRead(0x93 + i // 2)
            status[f"fanSpeed{i}"] = raw2speed(value & 0xFFFF)
            if i + 1 < fanNum:
                status[f"fanSpeed{i+1}"] = raw2speed(value >> 16)
        return status

    def histAcq(self, num: int, intr: int = 10000):
        if num > 65535:
            raise NotImplementedError("暂时没实现超过65535采样次数")
            # 做个循环合并起来就好
        if intr > 65535:
            raise NotImplementedError("暂时没实现超过6.5535sec的采样时间")
            # 做个循环合并起来就好
        delay = (intr + 10000) / 10000 * 2

        self.DetectRegSet(0x0012, 0x03)  # set mode auto
        self.DetectRegSet(0x0013, 0x01)  # set detect hist mode
        self.DetectRegSet(0x0014, intr)  # set auto acq time (100 us)
        self.DetectRegSet(0x0015, num)  # set auto acq count

        winRange = self.DetectRegRead(0x0021 + 0)
        winHigh = winRange >> 16
        winLow = winRange & 0xFFFF
        head = self.DetectRegRead(0x0018)
        infoEn = (head & (1 << 8)) != 0
        pos0En = (head & (1 << 29)) != 0
        pos1En = (head & (1 << 30)) != 0
        dt = self.histDataType((winLow, winHigh))
        headType = dt(withInfo=infoEn, withPos0=pos0En, withPos1=pos1En)
        dataType = dt()
        heads = np.zeros((num, self.detParam["pixNum"]), dtype=headType)
        datas = np.zeros((num, self.detParam["pixNum"]), dtype=dataType)

        logging.info(f"能谱模式采样开始, t:{time.time()}")
        self.DetectRegSet(0x0011, 1)  # start acq
        for i in range(num):
            for j in range(self.detParam["pixNum"]):
                (_, id, data) = self._qr.get(timeout=delay)
                assert (id == 2)
                if j == 0:
                    heads[i, j] = np.frombuffer(data, dtype=headType, count=1)
                else:
                    datas[i, j] = np.frombuffer(data, dtype=dataType, count=1)
        logging.info(f"能谱模式采样结束, t:{time.time()}")

        tgtFields = set(headType.names)
        srcFields = set(dataType.names)
        for field in (srcFields & tgtFields):
            heads[:, 1:][field] = datas[:, 1:][field]
        for field in tgtFields - srcFields:
            heads[:, 1:][field] = np.tile(heads[:, 0][field][:, np.newaxis], (1, self.detParam["pixNum"] - 1))

        return heads

    def thrAcq(self, num: int, intr: int = 10000):
        if num > 65535:
            raise NotImplementedError("暂时没实现超过65535采样次数")
            # 做个循环合并起来就好
        if intr > 65535:
            raise NotImplementedError("暂时没实现超过6.5535sec的采样时间")
            # 做个循环合并起来就好
        delay = (intr + 10000) / 10000 * 2

        self.DetectRegSet(0x0012, 0x03)  # set mode auto
        self.DetectRegSet(0x0013, 0x00)  # detect thr mode
        self.DetectRegSet(0x0014, intr)  # set auto acq time (100 us)
        self.DetectRegSet(0x0015, num)  # set auto acq count

        winNum = self.DetectRegRead(0x0020) + 1
        head = self.DetectRegRead(0x0018)
        infoEn = (head & (1 << 8)) != 0
        pos0En = (head & (1 << 29)) != 0
        pos1En = (head & (1 << 30)) != 0
        slice = self.detParam["pixNum"] // self.detParam["packagePix"]
        dt = self.winDataType(winNum, self.detParam["packagePix"])
        headType = dt(withInfo=infoEn, withPos0=pos0En, withPos1=pos1En)
        dataType = dt()
        heads = np.zeros((num, slice), dtype=headType)
        datas = np.zeros((num, slice), dtype=dataType)

        logging.info(f"阈值模式采样开始, t:{time.time()}")
        self.DetectRegSet(0x0011, 1)  # start acq
        for i in range(num):
            for j in range(slice):
                (_, id, data) = self._qr.get(timeout=delay)
                assert (id == 2)
                if j == 0:
                    heads[i, j] = np.frombuffer(data, dtype=headType, count=1)
                else:
                    datas[i, j] = np.frombuffer(data, dtype=dataType, count=1)
        logging.info(f"阈值模式采样结束, t:{time.time()}")

        tgtFields = set(headType.names)
        srcFields = set(dataType.names)
        for field in (srcFields & tgtFields):
            heads[:, 1:][field] = datas[:, 1:][field]
        for field in tgtFields - srcFields:
            heads[:, 1:][field] = np.tile(heads[:, 0][field][:, np.newaxis], (1, slice - 1))

        return heads

    @classmethod
    def getModelRef(cls) -> dict:
        modelRef = {}
        modelRef["D80"] = {
            "model": "D80",
            "winNum": 4,
            "pixNum": 80,
            "maxThr": 511,
            "packagePix": 20,
        }
        return modelRef

    @staticmethod
    def winDataType(winNum: int, pixNum: int) -> np.dtype:
        def winDataTypeRaw(withInfo: bool = False, withPos0: bool = False, withPos1: bool = False, withTs: bool = False) -> np.dtype:
            winDtype = [
                ('flag', '<u4'),
                ('frame', '<u4'),
                ('idx', '<u2'),
                ('dLen', '<u2'),
                ('data', '<u2', (pixNum, winNum)),
            ]
            if withInfo:
                winDtype.insert(1, ('info', '<u4'))
            if withPos1:
                winDtype.insert(1, ('pos1t', '<i4'))
                winDtype.insert(1, ('pos1h', '<i4'))
            if withPos0:
                winDtype.insert(1, ('pos0t', '<i4'))
                winDtype.insert(1, ('pos0h', '<i4'))
            if withTs:
                winDtype.insert(1, ('ts2', '<u4'))
                winDtype.insert(1, ('ts1', '<u4'))
            return np.dtype(winDtype)
        return winDataTypeRaw

    @staticmethod
    def histDataType(winWidth: tuple):
        def histDataTypeRaw(withInfo: bool = False, withPos0: bool = False, withPos1: bool = False, withTs: bool = False) -> np.dtype:
            (l, h) = winWidth
            hist_dtype = [
                ('flag', '<u4'),
                ('frame', '<u4'),
                ('idx', '<u2'),
                ('dLen', '<u2'),
                ('data', '<u2', (h-l+1,)),
            ]
            if withInfo:
                hist_dtype.insert(1, ('info', '<u4'))
            if withPos1:
                hist_dtype.insert(1, ('pos1t', '<i4'))
                hist_dtype.insert(1, ('pos1h', '<i4'))
            if withPos0:
                hist_dtype.insert(1, ('pos0t', '<i4'))
                hist_dtype.insert(1, ('pos0h', '<i4'))
            if withTs:
                hist_dtype.insert(1, ('ts2', '<u4'))
                hist_dtype.insert(1, ('ts1', '<u4'))
            return np.dtype(hist_dtype)
        return histDataTypeRaw
