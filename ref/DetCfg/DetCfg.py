import socket
import struct
import logging
from typing import Union


class DecodeError(Exception):
    pass


class ActionError(Exception):
    pass


class DetCfg():
    def __init__(self, mac):
        if type(mac) == bytes:
            self._field = {}
            self._editPage = set()
            self._fieldPage = {}
            self._field["mac"] = mac
        else:
            self.__init__(mac["mac"])
            self._editPage.update(mac._editPage)
            self._field.update(mac._field)
            self._fieldPage.update(mac._fieldPage)

    def __getitem__(self, key):
        return self._field[key]

    def __setitem__(self, key, value):
        if key == "mac":
            return
        if type(self._field[key]) != type(value):
            raise TypeError()
        if self._field[key] != value:
            self._field[key] = value
            self._editPage.add(self._fieldPage[key])

    def field(self) -> dict:
        field = dict(self._field)
        field["mac"] = self["mac"].hex()
        return field

    def name(self) -> str:
        return self["mac"].hex()

    # 子类要扩充其他页
    def decodePage(self, page: bytes, pageNum: int) -> 'DetCfg':
        if len(page) != 256:
            raise DecodeError("page数据长度不正确")
        if pageNum == 0:
            field = {
                "model":      struct.unpack_from("<8s", page, 0x0000)[0],
                "sn":         struct.unpack_from("<16s", page, 0x0008)[0],
                "swVer":      struct.unpack_from("<4s", page, 0x0018)[0],
                "fwVer":      struct.unpack_from("<4s", page, 0x0020)[0],
                "hwVer":      struct.unpack_from("<2s", page, 0x0024)[0],
                "detIp":      struct.unpack_from("<4s", page, 0x0040)[0],
                "gateway":    struct.unpack_from("<4s", page, 0x0044)[0],
                "serverIp":   struct.unpack_from("<4s", page, 0x0048)[0],
                "detMask":    struct.unpack_from("<B", page, 0x004C + 0)[0],
                "hbInterval": struct.unpack_from("<B", page, 0x004C + 1)[0],
                "serverPort": struct.unpack_from("<H", page, 0x004C + 2)[0],
            }
            # model & sn
            field["sn"] = field["sn"].strip(b'\xff').decode('ascii').rstrip('\x00')
            field["model"] = field["model"].strip(b'\xff').decode('ascii').rstrip('\x00')

            def ver2str(num, seg=3):
                if seg == 3:
                    return f"{num[2]}.{num[1]}.{num[0]}"
                else:
                    return f"{num[1]}.{num[0]}"
            field["swVer"] = ver2str(field["swVer"])
            field["fwVer"] = ver2str(field["fwVer"])
            field["hwVer"] = ver2str(field["hwVer"], 2)
            # ip->str转换函数inet_ntoa基于大端转换
            field["detIp"] = socket.inet_ntoa(field["detIp"][::-1])
            field["gateway"] = socket.inet_ntoa(field["gateway"][::-1])
            field["serverIp"] = socket.inet_ntoa(field["serverIp"][::-1])
            self._field.update(field)
            self._fieldPage.update({key: pageNum for key in field})
            self._editPage.discard(pageNum)
        else:
            pass
        return self

    # 子类要扩充其他页
    def encodePage(self, pageNum: int) -> bytes:
        page = bytearray(256)
        if pageNum == 0:
            detIp = socket.inet_aton(self["detIp"])[::-1]
            gateway = socket.inet_aton(self["gateway"])[::-1]
            serverIp = socket.inet_aton(self["serverIp"])[::-1]
            struct.pack_into("<4s", page, 0x0040, detIp)
            struct.pack_into("<4s", page, 0x0044, gateway)
            struct.pack_into("<4s", page, 0x0048, serverIp)
            struct.pack_into("<B",  page, 0x004C, self["detMask"])
            struct.pack_into("<B",  page, 0x004D, self["hbInterval"])
            struct.pack_into("<H",  page, 0x004E, self["serverPort"])
        else:
            pass
        return bytes(page)

    def readPage(self, s: socket.socket, pageNum: int) -> 'DetCfg':
        logging.debug(f"设备({self.name()})开始读取页{pageNum}")
        s.settimeout(0.5)
        stId = 1
        stAddr = ("255.255.255.255", 7492)
        stData = struct.pack("<HH", 0, pageNum)
        stPkg = DetCfg.headEncode(stId, stData, self["mac"])
        s.sendto(stPkg, stAddr)
        try:
            while True:
                (recv, (addr, port)) = s.recvfrom(1500)
                if port != 7492:
                    continue
                head = struct.unpack("<6s", recv[:6])[0]
                if head != b'VPDTCH':
                    continue
                (mac, id, subData) = DetCfg.headDecode(recv)
                if mac != self["mac"] or id != stId:
                    continue
                (flag, recvPageNum) = struct.unpack("<HH", subData[:4])
                if pageNum != recvPageNum:
                    continue
                if flag != 0:
                    raise ActionError(f"读取错误, flag={flag}")
                self.decodePage(subData[4:], pageNum)
                logging.debug(f"设备({self.name()})读取页{pageNum}结束")
                break
        except socket.timeout as e:
            logging.warning(f"设备({self.name()})读取页超时: {e}")
        return self

    def writePage(self, s: socket.socket, pageNum: int) -> 'DetCfg':
        logging.debug(f"设备({self.name()})开始写入页{pageNum}")
        s.settimeout(0.5)

        def check(data: bytes):
            (flag, recvPageNum) = struct.unpack("<HH", data)
            if pageNum != recvPageNum:
                return False
            if flag != 0:
                raise ActionError(f"写入错误, flag={flag}")
            return True
        stId = 2
        stData = struct.pack("<HH", 0, pageNum) + self.encodePage(pageNum)
        try:
            self.sendData(s, stId, stData, check)
        except socket.timeout as e:
            logging.warning(f"设备({self.name()})写入页响应超时: {e}")
        logging.debug(f"设备({self.name()})写入页{pageNum}结束")

        return self

    def _defaultCheck(data: bytes):
        return True

    def sendData(self, s: socket.socket, stId: int, stData: bytes, check=_defaultCheck) -> bytes:
        stAddr = ("255.255.255.255", 7492)
        stPkg = DetCfg.headEncode(stId, stData, self["mac"])
        s.sendto(stPkg, stAddr)
        while True:
            (recv, (addr, port)) = s.recvfrom(1500)
            if port != 7492:
                continue
            head = struct.unpack("<6s", recv[:6])[0]
            if head != b'VPDTCH':
                continue
            (mac, id, subData) = DetCfg.headDecode(recv)
            if mac != self["mac"] or id != stId:
                continue
            if not check(subData):
                continue
            return subData

    def flushEditPage(self, s: socket.socket) -> 'DetCfg':
        for pageNum in self._editPage:
            self.writePage(s, pageNum)

    # 子类要实现读取已有的全部页
    def readAllPage(self, s: socket.socket) -> 'DetCfg':
        self.readPage(s, 0)

    @classmethod
    def getModelName(cls):
        return cls.modelName if hasattr(cls, 'modelName') else ""

    @staticmethod
    def getInstance(det: 'DetCfg'):
        modelMap = {cls.getModelName(): cls for cls in DetCfg.__subclasses__()}
        modelMap[""] = None
        subCls = modelMap.get(det["model"])
        if subCls is None:
            return det
        else:
            return subCls(det)

    @staticmethod
    def pkgHeader(mac: bytes = b"\xFF\xFF\xFF\xFF\xFF\xFF") -> bytes:
        return b"\x56\x50\x44\x54\x43\x48" + mac

    @staticmethod
    def headEncode(type: int, data: bytes, mac: bytes = b"\xFF\xFF\xFF\xFF\xFF\xFF") -> bytes:
        if len(mac) != 6:
            raise RuntimeError("mac长度必须为6")
        return DetCfg.pkgHeader(mac) + struct.pack("<I", type) + data

    @staticmethod
    def headDecode(buf: bytes) -> tuple[bytes, int, bytes]:
        if len(buf) < 20:
            raise DecodeError("数据长度过短")
        (head, mac, id) = struct.unpack("<6s6sI", buf[:16])
        if head != b'VPDTCH':
            raise DecodeError("数据头部错误")
        return (mac, id, buf[16:])

    @staticmethod
    def broadcastFind(s: socket.socket) -> list['DetCfg']:
        logging.info("开始查找内网设备")
        s.settimeout(1)
        stAddr = ("255.255.255.255", 7492)
        stPkg = DetCfg.headEncode(1, struct.pack("<HH", 0, 0))
        s.sendto(stPkg, stAddr)

        dataBuf = []
        try:
            while True:
                (recv, (addr, port)) = s.recvfrom(1500)
                if port == 7492:
                    dataBuf.append((recv, addr))
        except socket.timeout as e:
            pass

        objBuf = []
        for (data, addr) in dataBuf:
            try:
                (mac, id, subData) = DetCfg.headDecode(data)
                if id == 1:
                    (pageNum, flag, page) = struct.unpack("<HH256s", subData)
                    if pageNum == 0 and flag == 0:
                        det = DetCfg(mac).decodePage(page, 0)
                        logging.info(f"找到设备:{det.name()}")
                        logging.debug(det._field)
                        objBuf.append(det)
                    else:
                        logging.warning(
                            f"收到错误数据包, page={pageNum}, flag={flag}")
                else:
                    logging.warning(f"收到错误数据包, type={id}")
            except DecodeError as e:
                logging.warning(f"解析失败': {(addr, data)} : {e}")
            except struct.error as e:
                logging.warning(f"拆包失败: {(addr, data)} : {e}")

        logging.info(f"结束查找内网设备, 共找到设备{len(objBuf)}个")
        return objBuf


class vXD80(DetCfg):
    modelName = "D80"
