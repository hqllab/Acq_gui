from queue import Queue, Empty
from threading import Thread, Lock
import socket
import struct
import logging
import ipaddress
import time
from Det import Det


class DetData():

    def __init__(self, ip, port=7494):
        self._ip = ip
        self._detR: dict[str, Queue] = {}
        self._detT: Queue = Queue()
        self._detRLock = Lock()
        self._device = {}
        self._listenFlag = [False]

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((ip, port))
        # 用于广播包发现
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # 防止能谱模式丢数据
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1536 * 1024 * 1024)
        s.settimeout(2)
        self._s = s

    def listen(self):
        if not self._listenFlag[0]:
            self._listenFlag[0] = True
            self._listenerR = Thread(
                target=self._loopR,
                args=(self._listenFlag,)
            )
            self._listenerT = Thread(
                target=self._loopT,
                args=(self._listenFlag,)
            )
            self._listenerR.start()
            self._listenerT.start()
        return self

    def close(self):
        self._listenFlag[0] = False
        return self

    def _loopR(self, flag: list[bool]):
        while flag[0]:
            try:
                (recv, (ip, port)) = self._s.recvfrom(500)
                if port != 7493 or len(recv) < 8:
                    continue
                ((hd, id), data) = (struct.unpack("<4sL", recv[:8]), recv[8:])
                if hd != b"VPDT":
                    continue
                if not ip in self._detR:
                    # new device
                    continue
                with self._detRLock:
                    match id:
                        case 1:
                            # logging.debug(f"接收到控制包, ip:{ip}")
                            self._detR[ip].put_nowait((ip, id, data))
                        case 2:
                            # logging.debug(f"接收到数据包", {ip})
                            self._detR[ip].put_nowait((ip, id, data))
                        case 3:
                            logging.debug(f"接收到心跳包/校正包, ip:{ip}")
                            # TODO 实现心跳包超时的检测(在线检测)
                        case _:
                            logging.warning("接收到无效数据包")
            except socket.timeout as e:
                pass

    def _loopT(self, flag: list[bool]):
        while flag[0]:
            try:
                (ip, id, data) = self._detT.get(timeout=2)
                ds = b"VPDT" + struct.pack("<L", id) + data
                self._s.sendto(ds, (ip, 7493))
            except Empty:
                pass

    def device(self) -> dict:
        return self._device.copy()

    def findDet(self) -> dict[str, Det]:
        dH = b"VPDT" + struct.pack("<L", 1)
        dD0 = struct.pack("<HH", 0, 0)  # read addr 0
        dD1 = struct.pack("<HH", 0, 1)  # read addr 1

        logging.info("开始查找内网设备")
        self._s.sendto(dH + dD0, ("255.255.255.255", 7493))
        self._s.sendto(dH + dD1, ("255.255.255.255", 7493))
        model = {}
        dataBuf = {}
        timeout_value = time.time() + 10
        try:
            while timeout_value >= time.time():
                (recv, (ip, port)) = self._s.recvfrom(1500)
                if port != 7493 or len(recv) != 16:
                    continue
                (head, id) = struct.unpack("<4sL", recv[:8])
                (ctr, addr, data) = struct.unpack("<HH4s", recv[8:])
                if head != b"VPDT" or id != 1 or ctr != 0 or addr > 2:
                    continue
                if addr == 0:
                    model[ip] = data
                else:
                    m = (model[ip] + data).strip(b'\xff').decode('ascii').rstrip('\x00')
                    if ip not in dataBuf:
                        dataBuf[ip] = Det(ip).getInstance(m)
                        dataBuf[ip].addQueue(self.addDet(ip))
        except socket.timeout as e:
            pass
        logging.info(f"结束查找内网设备, 共找到设备{len(dataBuf)}个")
        self._device.update(dataBuf)
        return dataBuf

    def addDet(self, ip: str) -> tuple[Queue, Queue]:
        ipaddress.ip_address(ip)
        qR = Queue()
        qT = self._detT
        with self._detRLock:
            self._detR[ip] = qR
        return (qR, qT)
