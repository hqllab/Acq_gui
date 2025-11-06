from socket import socket
import struct
import logging
import time
import hashlib
from DetCfg import DetCfg
import zlib


class DetUpdate(DetCfg):
    @staticmethod
    def getInstance(det: 'DetCfg'):
        return DetUpdate(det)

    def _id3Send(self, s: socket, stData: bytes, name: str, timeout: float = 0.5) -> int:
        s.settimeout(timeout)
        stId = 3
        logging.debug(f"设备({self.name()})开始下发{name}")

        def check(data: bytes):
            (_, page) = struct.unpack("<HH", stData[:4])
            if len(data) < 4:
                return False
            (_, rvPage) = struct.unpack("<HH", data[:4])
            return page == rvPage
        rvData = self.sendData(s, stId, stData, check)
        # try:
        #     rvData = self.sendData(s, stId, stData, check)
        # except socket.timeout as e:
        #     logging.warning(f"设备({self.name()}){name}响应超时: {e}")
        #     return -1
        (flag, page) = struct.unpack("<HH", rvData)
        if flag == 0:
            logging.info(f"设备({self.name()}){name}成功")
        else:
            logging.warning(f"设备({self.name()}){name}失败，错误{flag}")
        return flag

    def unlock(self, s: socket) -> int:
        stType = 1
        stData = b'ULCK'
        stPack = struct.pack("<HH", 0, stType) + stData
        return self._id3Send(s, stPack, "解锁Flash")

    def hash(self, s: socket, data: bytes) -> int:
        logging.debug(f"设备({self.name()})开始计算Hash")
        stType = 2
        # hashType = 2
        # hash = hashlib.sha1(data).digest()
        hashType = 3
        hash = struct.pack('<I', zlib.crc32(data))
        logging.debug(f"设备({self.name()})文件Hash:{hash.hex()}")
        stPack = struct.pack("<HHII20s", 0, stType, len(data), hashType, hash)
        return self._id3Send(s, stPack, "Hash校验", 60)

    def checkout(self, s: socket) -> int:
        stType = 3
        stData = b'CHECKOUT'
        stPack = struct.pack("<HH", 0, stType) + stData
        return self._id3Send(s, stPack, "切换镜像")

    def _id4Send(self, s: socket, stData: bytes) -> int:
        def check(data: bytes):
            (_, page) = struct.unpack("<HH", stData[:4])
            if len(data) < 4:
                return False
            (_, rvPage) = struct.unpack("<HH", data[:4])
            return page == rvPage
        stId = 4
        rvData = self.sendData(s, stId, stData, check)
        (flag, page) = struct.unpack("<HH", rvData)
        return flag

    def _program(self, s: socket, data: bytes):
        timeSum = 0.0
        timeMax = 0.0
        page = 0
        dataSize = len(data)
        nextProgress = 0
        for offset in range(0, dataSize, 256):
            progress = int(offset / dataSize * 100)
            if progress >= nextProgress:
                logging.info(f"设备({self.name()})已写入: {progress}%")
                nextProgress = progress + 10
            chunk = data[offset:offset+256]
            if len(chunk) < 256:
                chunk += bytes([0xFF] * (256 - len(chunk)))
            stPack = struct.pack("<HH", 0, page) + chunk
            start = time.time()
            if self._id4Send(s, stPack) != 0:
                return False
            stop = time.time()
            timeSum += stop - start
            timeMax = max(timeMax, stop - start)
            page += 1
        logging.debug(f"timeSum:{timeSum:.4f}s")
        logging.debug(f"timeMax:{timeMax:.4f}s")
        return True

    def _earse(self, s: socket, earseLen: int) -> bool:
        timeSum = 0.0
        timeMax = 0.0
        blockSizes = [(1, 64 * 1024), (0, 4 * 1024)]
        remaining = earseLen + blockSizes[-1][-1] - 1
        currentPage = 0
        nextProgress = 0
        for (bitSet, size) in blockSizes:
            while remaining >= size:
                progress = int((1 - remaining / earseLen) * 100)
                if progress >= nextProgress:
                    logging.info(f"设备({self.name()})已擦除: {progress}%")
                    nextProgress = progress + 10
                ctr = 1 << bitSet
                stPack = struct.pack("<HH", ctr, currentPage)
                start = time.time()
                if self._id4Send(s, stPack) != 0:
                    return False
                stop = time.time()
                timeSum += stop - start
                timeMax = max(timeMax, stop - start)
                remaining -= size
                currentPage += size // 256
        logging.debug(f"timeSum:{timeSum:.4f}s")
        logging.debug(f"timeMax:{timeMax:.4f}s")
        return True

    def update(self, s: socket, data: bytes) -> int:
        logging.info(f"设备({self.name()})开始擦除Flash")
        s.settimeout(1.5)
        if not self._earse(s, len(data)):
            logging.warning(f"设备({self.name()})擦除Flash错误")
            return 1
        logging.info(f"设备({self.name()})擦除Flash成功")
        logging.info(f"设备({self.name()})开始写入Flash")
        s.settimeout(0.5)
        if not self._program(s, data):
            logging.warning(f"设备({self.name()})写入Flash错误")
            return 2
        logging.info(f"设备({self.name()})写入Flash成功")
        return 0
