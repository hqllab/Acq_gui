import cmd2
import socket
import struct
import threading
import time
import msgpack
import sys
from cmd2 import with_argparser
import argparse
from typing import Optional, Callable, Dict

# --- 协议常量 ---
FRAME_HEAD = 0x434D5601
SRC_DEV_ID = 0x14  # 19
# SERVER_IP = "192.168.156.165"  # 默认 IP
# SERVER_IP = "192.168.156.53"  # 默认 IP
SERVER_IP = "10.20.22.232"  # 默认 IP
SERVER_PORT = 47868            # 默认 Port
ACK_MASK = 0x8000
MAX_DATA_LEN = 1024            # 最大数据长度限制

# 头部结构: HEAD(<L), SRC(<B), 预留(<B), 预留(<H), 命令ID(<H), 长度(<H)
HEADER_STRUCT_FMT = '<LBBHHH'
HEADER_SIZE = struct.calcsize(HEADER_STRUCT_FMT)

HEARTBEAT_INTERVAL = 1.0       # 心跳发送间隔 (秒)
HEARTBEAT_TIMEOUT = 10.0       # 心跳超时判定 (秒)

# --- 命令和事件 ID ---
class Command:
    # --- 系统命令 (0x00xx) ---
    HEARTBEAT = 0x0001
    GET_STATE = 0x0002
    RESET_ESTOP = 0x0003
    QUERY_ESTOP = 0x0004
    TRIGGER_ESTOP = 0x0005
    QUERY_UPPER_LIMIT = 0x0006
    QUERY_LOWER_LIMIT = 0x0007

    # --- 电机命令 (0x01xx) ---
    FIND_ZERO = 0x0102
    QUERY_MOVE_RANGE = 0x0108
    CONTINUOUS_MOVE = 0x0103
    SET_EXPOSURE_POS = 0x0106
    MOTOR_MOVE = 0x0107
    PASS_THROUGH = 0x0109
    MOTOR_RESET_ERROR = 0x010A

    # --- 发生器/高压命令 (0x02xx) ---
    SET_VOLTAGE = 0x0201
    SET_CURRENT = 0x0202
    ENTER_EXPOSURE_MODE = 0x0205
    EXIT_EXPOSURE_MODE = 0x0206
    ALLOW_EXPOSURE = 0x0208
    SET_FOCUS = 0x0209
    SET_MAX_EXPOSURE_TIME = 0x020A

    # --- IO 命令 (0x03xx) ---
    SET_OUTPUT_IO = 0x0301
    QUERY_OUTPUT_IO = 0x0302
    QUERY_INPUT_IO = 0x0303
    EXEC_SHUTDOWN = 0x0304
    REQ_SHUTDOWN = 0x0305
    EXEC_POWERON = 0x0306
    QUERY_POWER_STATE = 0x0307
    QUERY_BOARD_IO = 0x0308


class Event:
    # --- 系统事件 (0x00xx) ---
    HEARTBEAT = 0x0001
    ESTOP_STATUS_CHANGED = 0x0010
    HEARTBEAT_TIMEOUT = 0x0011
    ACTIVE_DISCONNECT = 0x0012
    UPPER_LIMIT_CHANGED = 0x0013
    LOWER_LIMIT_CHANGED = 0x0014

    # --- 电源事件 (0x03xx) ---
    POWER_STATE_CHANGED = 0x0310
    SHUTDOWN_REQUEST = 0x0312

    # --- 电机事件 (0x01xx) ---
    FIND_ZERO_COMPLETE = 0x0110
    MOTOR_REACHED_POS = 0x0111
    MOTOR_STATE_CHANGED = 0x0112
    MOVE_TIMEOUT = 0x0113
    MOTOR_ERROR = 0x0114
    MOVE_INTERRUPTED = 0x0115

    # --- 发生器/高压事件 (0x02xx) ---
    GENERATOR_ERROR = 0x0210
    STATE_TRANSITION = 0x0211
    HANDSWITCH_STATUS = 0x0212
    EXPOSURE_PARAMS = 0x0213


# --- 状态映射 ---
MOTOR_STATE_MAP = {
    0: "未连接",
    1: "初始化",
    2: "停止",
    3: "错误",
    4: "移动中",
}

GENERATOR_STATE_MAP = {
    0: "未连接",
    1: "初始化",
    2: "错误状态",
    3: "待机",
    4: "曝光模式——进入中",
    5: "曝光模式——准备未完成",
    6: "曝光模式——准备完成",
    7: "曝光模式——放线中",
    8: "曝光模式——退出中",
}

POWER_STATE_MAP = {
    0: "关机",
    1: "开机",
    2: "正在开机",
    3: "正在关机",
}

INTERRUPT_OP_MAP = {
    0: "持续移动",
    1: "定点移动",
    2: "曝光移动",
}

COMMAND_STATUS_MAP = {
    0x0000: "成功",
    0x0001: "执行失败（通用失败）",
    0x0002: "帧格式错误",
    0x0003: "输入超限（参数错误）",
    0x0004: "执行超时",
    0x0005: "FLASH写入失败",
    0x0006: "设备ID不允许执行该操作",
    0x0007: "设备不在线",
    0x0008: "模块不在线/未连接",
    0x0009: "命令不存在",
}

# 来自规格说明书的有效 mA 值 (R'20 系列)
MA_VALUES = [
    10, 11, 12.5, 14, 16, 18, 20, 22, 25, 28, 32, 36, 40, 45, 50,
    56, 63, 71, 80, 90, 100, 110, 125, 140, 160, 180, 200, 220,
    250, 280, 320, 360, 400, 450, 500, 560, 630, 710, 800, 900, 1000
]

MS_R20_VALUES = [
    1, 1.1, 1.2, 1.4, 1.6, 1.8, 2, 2.2, 2.5, 2.8, 3.2, 3.6, 4, 4.5, 5,
    5.6, 6.3, 7.1, 8, 9, 10, 11, 12.5, 14, 16, 18, 20, 22, 25, 28,
    32, 36, 40, 45, 50, 56, 63, 71, 80, 90, 100, 110, 125, 140,
    160, 180, 200, 220, 250, 280, 320, 360, 400, 450, 500, 560,
    630, 710, 800, 900, 1000, 1100, 1250, 1400, 1600, 1800, 2000,
    2200, 2500, 2800, 3200, 3600, 4000, 4500, 5000, 5600, 6300,
    7100, 8000, 9000, 10000, 11000, 12500, 14000
]


class SLZClient:
    """处理底层 Socket 通信、多线程以及协议的封装与解析。"""

    def __init__(self, ip: str, port: int,
                 on_message_callback: Callable[[int, bytes], None],
                 on_disconnect_callback: Callable[[str], None],
                 on_connect_callback: Callable[[str], None],
                 on_timeout_callback: Optional[Callable[[str], None]] = None):
        self.server_ip = ip
        self.server_port = port
        self.on_message = on_message_callback
        self.on_disconnect = on_disconnect_callback
        self.on_connect = on_connect_callback
        self.on_timeout = on_timeout_callback

        self.sock: Optional[socket.socket] = None
        self.send_lock = threading.Lock()
        self.shutdown_flag = threading.Event()

        self.listener_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None

        self.last_heartbeat_time = 0.0
        self.timeout_warned = False

    def connect(self) -> bool:
        """建立与服务器的连接并启动后台线程。"""
        if self.sock:
            return True  # 已连接

        self.shutdown_flag.clear()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(None)  # 阻塞模式 (默认)
            self.sock.connect((self.server_ip, self.server_port))

            self.last_heartbeat_time = time.time()  # 重置心跳时间

            self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)

            self.listener_thread.start()
            self.heartbeat_thread.start()

            if self.on_connect:
                self.on_connect(f"成功连接到 {self.server_ip}:{self.server_port}")
            return True
        except socket.error as e:
            if self.on_disconnect:
                self.on_disconnect(f"连接失败: {e}")
            self._cleanup_socket()
            return False

    def disconnect(self):
        """手动断开连接。"""
        self.shutdown_flag.set()
        self._cleanup_socket()
        if self.on_disconnect:
            self.on_disconnect("用户主动断开连接。")

    def send_command(self, cmd_id: int, data: bytes = b'') -> bool:
        """安全地封装并发送命令。"""
        if not self.sock:
            if self.on_disconnect:
                self.on_disconnect("未连接。无法发送命令。")
            return False

        try:
            packet = self._pack_command(cmd_id, data)
            with self.send_lock:
                if self.sock:
                    self.sock.sendall(packet)
            return True
        except socket.error as e:
            if self.on_disconnect:
                self.on_disconnect(f"发送命令失败: {e}")
            self._handle_connection_lost()
            return False

    def _cleanup_socket(self):
        """关闭 Socket 并重置状态。"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def _handle_connection_lost(self, reason: str = "连接已断开。"):
        """线程检测到连接断开时的内部处理函数。"""
        if not self.shutdown_flag.is_set():
            self.shutdown_flag.set()
            self._cleanup_socket()
            if self.on_disconnect:
                self.on_disconnect(reason)

    def _pack_command(self, cmd_id: int, data: bytes = b'') -> bytes:
        """将命令封装为指定的二进制格式（小端序）。"""
        data_len = len(data)
        header = struct.pack(HEADER_STRUCT_FMT, FRAME_HEAD, SRC_DEV_ID, 0, 0, cmd_id, data_len)
        return header + data

    def _listen_loop(self):
        """用于接收消息的后台线程循环。"""
        while not self.shutdown_flag.is_set():
            try:
                if self.sock is None:
                    break

                header_bytes = self.sock.recv(HEADER_SIZE)
                if not header_bytes:
                    self._handle_connection_lost()
                    break

                if len(header_bytes) < HEADER_SIZE:
                    continue

                head, _, _, _, cmd_id, data_len = struct.unpack(HEADER_STRUCT_FMT, header_bytes)

                if head != FRAME_HEAD:
                    continue

                # 检查数据长度限制
                if data_len > MAX_DATA_LEN:
                    self._handle_connection_lost(f"数据长度 {data_len} 超过限制 {MAX_DATA_LEN}。")
                    break

                data = b''
                if data_len > 0:
                    if self.sock is None:
                        break
                    received = 0
                    chunks = []
                    while received < data_len:
                        chunk = self.sock.recv(data_len - received)
                        if not chunk:
                            break
                        chunks.append(chunk)
                        received += len(chunk)

                    if received < data_len:
                         self._handle_connection_lost()
                         break
                    data = b''.join(chunks)

                # 更新心跳时间
                if cmd_id == Event.HEARTBEAT:
                    self.last_heartbeat_time = time.time()
                    self.timeout_warned = False

                if self.on_message:
                    try:
                        self.on_message(cmd_id, data)
                    except Exception as e:
                        print(f"处理消息 0x{cmd_id:04x} 时出错: {e}", file=sys.stderr)

            except socket.error:
                self._handle_connection_lost()
                break
            except Exception as e:
                self._handle_connection_lost(f"监听器出错: {e}")
                break

    def _heartbeat_loop(self):
        """发送心跳和检查超时的后台线程循环。"""
        # 启动时重置心跳时间以避免立即超时
        self.last_heartbeat_time = time.time()
        self.timeout_warned = False

        next_heartbeat_send = time.time()

        while not self.shutdown_flag.is_set():
            now = time.time()

            # 检查服务器超时
            if now - self.last_heartbeat_time > HEARTBEAT_TIMEOUT:
                if not self.timeout_warned:
                    if self.on_timeout:
                        self.on_timeout(f"警告：{HEARTBEAT_TIMEOUT}秒内未收到心跳。")
                    self.timeout_warned = True

            # 发送心跳
            if now >= next_heartbeat_send:
                if not self.send_command(Command.HEARTBEAT):
                    # 如果发送失败，可能已断开连接，由 handle_connection_lost 处理
                    break
                next_heartbeat_send = now + HEARTBEAT_INTERVAL

            # 稍微休眠以避免忙等待
            time.sleep(0.01)


class SLZCtrCmd(cmd2.Cmd):
    """一个通过 TCP 控制远程设备的 cmd2 应用程序。"""

    def __init__(self):
        super().__init__()
        self.prompt = "(已断开连接)> "

        # 初始化客户端
        self.client = SLZClient(
            SERVER_IP,
            SERVER_PORT,
            self._process_packet_callback,
            self._on_disconnect_callback,
            self._on_connect_callback,
            self._on_timeout_callback
        )

        # 将命令/事件 ID 映射到其处理方法
        self.handlers = {
            # 现有处理程序
            Command.GET_STATE: self._handle_state_response,
            Command.MOTOR_MOVE | ACK_MASK: self._handle_ack,
            Command.HEARTBEAT | ACK_MASK: self._handle_pass,
            Command.SET_EXPOSURE_POS | ACK_MASK: self._handle_ack,
            Event.HEARTBEAT: self._handle_pass,
            Event.MOTOR_REACHED_POS: self._handle_motor_reached,
            Event.MOTOR_STATE_CHANGED: self._handle_motor_state_changed,

            # 新命令确认 (ACK)
            Command.SET_VOLTAGE | ACK_MASK: self._handle_ack,
            Command.SET_CURRENT | ACK_MASK: self._handle_ack,
            Command.ENTER_EXPOSURE_MODE | ACK_MASK: self._handle_ack,
            Command.EXIT_EXPOSURE_MODE | ACK_MASK: self._handle_ack,
            Command.ALLOW_EXPOSURE | ACK_MASK: self._handle_ack,
            Command.SET_MAX_EXPOSURE_TIME | ACK_MASK: self._handle_ack,
            Command.SET_FOCUS | ACK_MASK: self._handle_ack,

            # 持续移动和找零处理程序
            Command.FIND_ZERO | ACK_MASK: self._handle_find_zero_ack,
            Command.CONTINUOUS_MOVE | ACK_MASK: self._handle_continuous_move_ack,
            Command.QUERY_MOVE_RANGE | ACK_MASK: self._handle_move_range_response,
            Command.PASS_THROUGH | ACK_MASK: self._handle_pass_through_response,
            Command.MOTOR_RESET_ERROR | ACK_MASK: self._handle_ack,

            # 新事件处理程序
            Event.STATE_TRANSITION: self._handle_state_transition,
            Event.HANDSWITCH_STATUS: self._handle_handswitch_status,
            Event.GENERATOR_ERROR: self._handle_generator_error,
            Event.MOVE_TIMEOUT: self._handle_move_timeout,
            Event.FIND_ZERO_COMPLETE: self._handle_find_zero_complete,
            Event.MOTOR_ERROR: self._handle_motor_error,
            Event.EXPOSURE_PARAMS: self._handle_exposure_params,

            # 急停和限位处理程序
            Command.RESET_ESTOP | ACK_MASK: self._handle_ack,
            Command.TRIGGER_ESTOP | ACK_MASK: self._handle_ack,
            Command.QUERY_ESTOP | ACK_MASK: self._handle_u32_response,
            Command.QUERY_UPPER_LIMIT | ACK_MASK: self._handle_u32_response,
            Command.QUERY_LOWER_LIMIT | ACK_MASK: self._handle_u32_response,
            Event.ESTOP_STATUS_CHANGED: self._handle_u32_event,
            Event.UPPER_LIMIT_CHANGED: self._handle_u32_event,
            Event.LOWER_LIMIT_CHANGED: self._handle_u32_event,

            # IO 处理程序
            Command.SET_OUTPUT_IO | ACK_MASK: self._handle_ack,
            Command.QUERY_OUTPUT_IO | ACK_MASK: self._handle_u64_response,
            Command.QUERY_INPUT_IO | ACK_MASK: self._handle_u64_response,

            # 电源管理处理程序
            Command.EXEC_SHUTDOWN | ACK_MASK: self._handle_ack,
            Command.REQ_SHUTDOWN | ACK_MASK: self._handle_ack,
            Command.EXEC_POWERON | ACK_MASK: self._handle_ack,
            Command.QUERY_POWER_STATE | ACK_MASK: self._handle_power_state_response,
            Command.QUERY_BOARD_IO | ACK_MASK: self._handle_board_io_response,
            Event.POWER_STATE_CHANGED: self._handle_power_state_changed,
            Event.SHUTDOWN_REQUEST: self._handle_shutdown_request,
            Event.HEARTBEAT_TIMEOUT: self._handle_heartbeat_timeout_event,
            Event.ACTIVE_DISCONNECT: self._handle_active_disconnect_event,
            Event.MOVE_INTERRUPTED: self._handle_move_interrupted,
        }

        # 启动时自动连接
        self.pfeedback(f"正在连接到 {SERVER_IP}:{SERVER_PORT}...")
        self.client.connect()

        # 用于跟踪当前是否正在执行命令的状态标志
        self.executing = False

    def precmd(self, statement):
        """在解析命令之前执行的钩子。"""
        self.executing = True
        return super().precmd(statement)

    def postcmd(self, stop, statement):
        """在命令分发完成后执行的钩子。"""
        # 稍微延迟以在仍处于“执行中”状态时捕获即时响应
        time.sleep(0.2)
        self.executing = False
        return super().postcmd(stop, statement)

    # --- 来自客户端的回调 ---

    def _display_msg(self, msg: str):
        """用于从任何线程安全显示消息的辅助函数。"""
        if threading.current_thread() is threading.main_thread():
            self.pfeedback(msg)
        elif getattr(self, 'executing', False):
            # 如果正在执行命令，直接打印而不重新绘制提示符
            print(msg, flush=True)
        else:
            # 如果处于空闲状态，使用 async_alert 重新绘制提示符
            self.async_alert(msg)

    def _on_timeout_callback(self, msg: str):
        self._display_msg(f"超时: {msg}")

    def _on_connect_callback(self, msg: str):
        self.prompt = f"({self.client.server_ip})> "
        self._display_msg(msg)

    def _on_disconnect_callback(self, msg: str):
        self.prompt = "(已断开连接)> "
        self._display_msg(f"连接断开: {msg}")

    def _process_packet_callback(self, cmd_id: int, data: bytes):
        """接收到完整数据包时调用。"""
        handler = self.handlers.get(cmd_id)
        result = ""
        if handler:
            result = handler(cmd_id, data)
        else:
            result = f">> 收到未知命令/事件 0x{cmd_id:04x}，数据: {data.hex() if data else '无'}"

        if result:
            self._display_msg(result)

    # --- 数据包处理程序 ---

    def _try_unpack(self, data: bytes, fmt: str) -> Optional[tuple]:
        required_size = struct.calcsize(fmt)
        if len(data) < required_size:
            return None
        return struct.unpack(fmt, data[:required_size])

    def _handle_pass(self, cmd_id, data) -> str:
        return ""

    def _handle_ack(self, cmd_id, data) -> str:
        original_cmd_id = cmd_id & ~ACK_MASK
        cmd_name = "未知"
        for name, val in vars(Command).items():
            if val == original_cmd_id:
                cmd_name = name
                break

        unpacked = self._try_unpack(data, '<H')
        if unpacked:
            ack_code = unpacked[0]
            desc = COMMAND_STATUS_MAP.get(ack_code, "未知状态")
            return f">> {cmd_name} (0x{original_cmd_id:04x}) 的确认: 0x{ack_code:04x} ({desc})"
        return f">> {cmd_name} (0x{original_cmd_id:04x}) 的确认数据格式错误。"

    def _handle_pass_through_response(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<HHI')
        if unpacked:
            status, align, val = unpacked
            status_str = COMMAND_STATUS_MAP.get(status, "未知状态")
            return f">> 透传响应: 状态=0x{status:04x} ({status_str}), 对齐=0x{align:04x}, 数据=0x{val:08x}"
        return f">> !! 透传响应数据长度无效。收到 {len(data)}，预期 >= 8。"

    def _handle_state_response(self, cmd_id, data) -> str:
        try:
            state_data = msgpack.unpackb(data, raw=False)
            output = "\n>> 状态响应:\n"
            for key, value in state_data.items():
                output += f"   - {key}: {value}\n"
            return output.strip()
        except Exception as e:
            return f">> !! 状态信息的 msgpack 解码失败: {e}"

    def _handle_motor_reached(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<i')
        if unpacked:
            pos = unpacked[0]
            return f">> 事件: 电机到达位置。当前位置: {pos * 0.1:.1f} mm"
        return ">> !! 电机位置事件的数据长度无效。"

    def _handle_motor_state_changed(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<BB')
        if unpacked:
            old_state_id, new_state_id = unpacked
            old_state = MOTOR_STATE_MAP.get(old_state_id, f"未知 ({old_state_id})")
            new_state = MOTOR_STATE_MAP.get(new_state_id, f"未知 ({new_state_id})")
            return f">> 事件: 电机状态变更。从 '{old_state}' 变为 '{new_state}'。"
        return ">> !! 电机状态变更事件的数据长度无效。"

    def _handle_state_transition(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<BBB')
        if unpacked:
            gen_id, old_state_id, new_state_id = unpacked
            gen_name = 'A' if gen_id == 0 else 'B'
            old_state = GENERATOR_STATE_MAP.get(old_state_id, f"未知 ({old_state_id})")
            new_state = GENERATOR_STATE_MAP.get(new_state_id, f"未知 ({new_state_id})")
            return f">> 事件: 发生器 {gen_name} 状态变更。从 '{old_state}' 变为 '{new_state}'。"
        return f">> !! 状态切换事件的数据长度无效。"

    def _handle_handswitch_status(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<B')
        if unpacked:
            status_byte = unpacked[0]
            prep_status = "按下" if (status_byte & 0x01) else "松开"
            exposure_status = "按下" if (status_byte & 0x02) else "松开"
            return f">> 事件: 手闸状态。准备: {prep_status}, 曝光: {exposure_status}。"
        return f">> !! 手闸状态事件的数据长度无效。"

    def _handle_generator_error(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<BBH')
        if unpacked:
            gen_id, _, error_code = unpacked
            gen_name = 'A' if gen_id == 0 else 'B'
            return f">> 事件: 发生器 {gen_name} 错误。代码: 0x{error_code:04x}"
        return f">> !! 发生器错误事件的数据长度无效。"

    def _handle_find_zero_ack(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<H')
        if unpacked:
            code = unpacked[0]
            status_str = COMMAND_STATUS_MAP.get(code, "未知状态")
            return f">> 找零响应: 0x{code:04x} ({status_str})"
        return f">> !! 找零 ACK 的数据长度无效。"

    def _handle_continuous_move_ack(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<H')
        if unpacked:
            code = unpacked[0]
            if code == 0:
                return ""  # 抑制成功输出以避免淹没控制台
            status_str = COMMAND_STATUS_MAP.get(code, "未知状态")
            return f">> 持续移动错误: 0x{code:04x} ({status_str})"
        return f">> !! 持续移动 ACK 的数据长度无效。"

    def _handle_move_timeout(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<i')
        if unpacked:
            pos = unpacked[0]
            return f">> 事件: 移动超时 (0x0113)。当前位置: {pos * 0.1:.1f} mm"
        return f">> !! 移动超时事件的数据长度无效。"

    def _handle_find_zero_complete(self, cmd_id, data) -> str:
        return ">> 事件: 找零完成。正在移至 0 位。请设置探测器原点！"

    def _handle_motor_error(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<H')
        if unpacked:
            error_code = unpacked[0]
            return f">> 事件: 电机驱动错误。代码: 0x{error_code:04x}"
        return ">> !! 电机错误事件的数据长度无效。"

    def _handle_exposure_params(self, cmd_id, data) -> str:
        # u8 gen_id, u8 align, u16 kv, u16 ma (0.1 step)
        unpacked = self._try_unpack(data, '<BBHH')
        if unpacked:
            gen_id, _, kv, ma_raw = unpacked
            gen_name = 'A' if gen_id == 0 else 'B'
            ma = ma_raw * 0.1
            return f">> 事件: 曝光参数 (发生器 {gen_name})。电压: {kv} kV, 电流: {ma:.1f} mA"
        return ">> !! 曝光参数事件的数据长度无效。"

    def _handle_u32_response(self, cmd_id, data) -> str:
        original_cmd_id = cmd_id & ~ACK_MASK
        unpacked = self._try_unpack(data, '<I')
        if unpacked:
            val = unpacked[0]
            cmd_name = "未知"
            for name, value in vars(Command).items():
                if value == original_cmd_id:
                    cmd_name = name
                    break
            return f">> {cmd_name} (0x{original_cmd_id:04x}) 的响应: 0x{val:08x}"
        return f">> !! u32 响应的数据长度无效。"

    def _handle_u32_event(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<I')
        if unpacked:
            val = unpacked[0]
            evt_name = "未知"
            for name, value in vars(Event).items():
                if value == cmd_id:
                    evt_name = name
                    break
            return f">> 事件: {evt_name} (0x{cmd_id:04x})。状态: 0x{val:08x}"
        return f">> !! u32 事件的数据长度无效。"

    def _handle_u64_response(self, cmd_id, data) -> str:
        original_cmd_id = cmd_id & ~ACK_MASK
        unpacked = self._try_unpack(data, '<Q')
        if unpacked:
            val = unpacked[0]
            cmd_name = "未知"
            for name, value in vars(Command).items():
                if value == original_cmd_id:
                    cmd_name = name
                    break
            return f">> {cmd_name} (0x{original_cmd_id:04x}) 的响应: 0x{val:016x}"
        return f">> !! u64 响应的数据长度无效。"

    def _handle_power_state_response(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<H')
        if unpacked:
            state = unpacked[0]
            state_str = POWER_STATE_MAP.get(state, "未知")
            return f">> 电源状态: 0x{state:04x} ({state_str})"
        return ">> !! 电源状态响应的数据长度无效。"

    def _handle_board_io_response(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<QQ')
        if unpacked:
            input_io, output_io = unpacked
            return f">> 板卡 IO 状态:\n   输入:  0x{input_io:016x}\n   输出: 0x{output_io:016x}"
        return ">> !! 板卡 IO 响应的数据长度无效。"

    def _handle_power_state_changed(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<HH')
        if unpacked:
            old_state, new_state = unpacked
            old_str = POWER_STATE_MAP.get(old_state, "未知")
            new_str = POWER_STATE_MAP.get(new_state, "未知")
            return f">> 事件: 电源状态变更。0x{old_state:04x} ({old_str}) -> 0x{new_state:04x} ({new_str})"
        return ">> !! 电源状态变更事件的数据长度无效。"

    def _handle_shutdown_request(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<H')
        if unpacked:
            device_id = unpacked[0]
            return f">> 事件: 设备 ID 0x{device_id:04x} 请求关机"
        return ">> !! 关机请求事件的数据长度无效。"

    def _handle_heartbeat_timeout_event(self, cmd_id, data) -> str:
        return f">> 事件: 心跳超时 (0x{cmd_id:04x})。"

    def _handle_active_disconnect_event(self, cmd_id, data) -> str:
        return f">> 事件: 主动断开连接 (0x{cmd_id:04x})。远程设备正在关闭连接。"

    def _handle_move_interrupted(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<BB')
        if unpacked:
            dev_id, op_type = unpacked
            op_str = INTERRUPT_OP_MAP.get(op_type, f"未知 ({op_type})")
            return f">> 事件: 移动中断。设备 ID: 0x{dev_id:02x}, 操作类型: {op_str}"
        return f">> !! 移动中断事件的数据长度无效。"

    def _handle_move_range_response(self, cmd_id, data) -> str:
        unpacked = self._try_unpack(data, '<iii')
        if unpacked:
            min_pos, max_pos, max_speed = unpacked
            return (f">> 行程范围响应:\n"
                    f"   最小位置: {min_pos * 0.1:.1f} mm\n"
                    f"   最大位置: {max_pos * 0.1:.1f} mm\n"
                    f"   最大速度: {max_speed * 0.1:.1f} mm/s")
        return ">> !! 行程范围响应数据长度错误。"

    # --- 连接管理命令 ---

    def do_reconnect(self, _):
        """断开并重新连接到服务器。"""
        self.pfeedback("正在重新连接...")
        self.client.disconnect()
        # 给一点时间清理
        time.sleep(0.5)
        if self.client.connect():
            self.pfeedback("已启动重连尝试。")
        else:
            self.perror("重连立即失败。")

    def do_disconnect(self, _):
        """从服务器断开连接。"""
        self.pfeedback("正在断开连接...")
        self.client.disconnect()

    # --- 现有命令 ---
    def do_state(self, _):
        """请求远程设备的当前状态。"""
        self.pfeedback("正在请求状态...")
        self.client.send_command(Command.GET_STATE)

    move_parser = cmd2.Cmd2ArgumentParser(description="控制电机移动。")
    move_parser.add_argument('position', type=int, help='目标位置 (单位: 0.1mm)')
    move_parser.add_argument('speed', type=int, help='移动速度 (单位: 0.1mm/s)')
    @with_argparser(move_parser)
    def do_move(self, args):
        if args.speed < 0:
            self.perror("速度必须是非负整数。")
            return
        self.pfeedback(f"正在发送移动命令: 位置={args.position}, 速度={args.speed}")
        data = struct.pack('<ii', args.position, args.speed)
        self.client.send_command(Command.MOTOR_MOVE, data)

    set_exposure_pos_parser = cmd2.Cmd2ArgumentParser(description="设置曝光期间的移动参数。")
    set_exposure_pos_parser.add_argument('position', type=int, help='目标位置 (单位: 0.1mm)')
    set_exposure_pos_parser.add_argument('speed', type=int, help='移动速度 (单位: 0.1mm/s)')
    @with_argparser(set_exposure_pos_parser)
    def do_set_exposure_pos(self, args):
        """设置曝光状态下的移动参数。"""
        if args.speed < 0:
            self.perror("速度必须是非负整数。")
            return
        self.pfeedback(f"正在设置曝光移动参数: 位置={args.position}, 速度={args.speed}")
        data = struct.pack('<ii', args.position, args.speed)
        self.client.send_command(Command.SET_EXPOSURE_POS, data)

    def do_find_zero(self, _):
        """
        执行找零 (0x0102)。
        注意：双向找零，耗时 2-3 分钟。异步执行。
        """
        self.pfeedback("正在发送找零命令 (0x0102)...")
        self.pfeedback("此过程需要 2-3 分钟。请等待异步完成事件。")
        self.client.send_command(Command.FIND_ZERO)

    def do_reset_motor_error(self, _):
        """
        重置电机驱动错误 (0x010A)。
        """
        self.pfeedback("正在发送电机重置错误命令 (0x010A)...")
        # 数据: 0x6D727374 (小端序)
        data = struct.pack('<I', 0x6D727374)
        self.client.send_command(Command.MOTOR_RESET_ERROR, data)

    continuous_move_parser = cmd2.Cmd2ArgumentParser(description="持续移动，直到按下 Enter 键。")
    continuous_move_parser.add_argument('position', type=int, help='目标位置 (单位: 0.1mm)')
    continuous_move_parser.add_argument('speed', type=int, help='速度 (单位: 0.1mm/s)，必须为正数')
    @with_argparser(continuous_move_parser)
    def do_continuous_move(self, args):
        """每 50ms 持续发送移动命令，直到按下 Enter 键。"""
        if args.speed < 0:
            self.perror("速度必须为正数。")
            return

        self.pfeedback(f"正在开始持续移动到 {args.position}，速度 {args.speed}...")
        self.pfeedback("按下 <Enter> 停止。")

        stop_event = threading.Event()

        def sender_task():
            payload = struct.pack('<ii', args.position, args.speed)
            while not stop_event.is_set():
                self.client.send_command(Command.CONTINUOUS_MOVE, payload)
                time.sleep(0.05)  # 50ms 间隔

        t = threading.Thread(target=sender_task, daemon=True)
        t.start()

        # 阻塞主线程等待用户输入
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass  # 优雅地处理 Ctrl+C 或 EOF

        # 停止信号
        stop_event.set()
        t.join()

        # 发送刹车命令 (速度为 0)
        brake_payload = struct.pack('<ii', args.position, 0)
        self.client.send_command(Command.CONTINUOUS_MOVE, brake_payload)
        self.pfeedback("持续移动已停止。")

    # --- 新命令 ---
    set_voltage_parser = cmd2.Cmd2ArgumentParser(description="设置管电压。")
    set_voltage_parser.add_argument('generator_id', type=int, choices=[0, 1], help='发生器 ID (0 代表 A, 1 代表 B)')
    set_voltage_parser.add_argument('voltage', type=int, help='管电压 kV (范围: 40-150)')
    @with_argparser(set_voltage_parser)
    def do_set_voltage(self, args):
        """设置管电压。"""
        if not 40 <= args.voltage <= 150:
            self.perror("电压必须在 40 到 150 kV 之间。")
            return
        self.pfeedback(f"正在将发生器 {args.generator_id} 的电压设置为 {args.voltage} kV...")
        data = struct.pack('<BBH', args.generator_id, 0, args.voltage)
        self.client.send_command(Command.SET_VOLTAGE, data)

    set_current_parser = cmd2.Cmd2ArgumentParser(description="设置管电流。")
    set_current_parser.add_argument('generator_id', type=int, choices=[0, 1], help='发生器 ID (0 代表 A, 1 代表 B)')
    set_current_parser.add_argument('current', type=float, choices=MA_VALUES, help=f"管电流 mA。允许的值: {MA_VALUES}")
    @with_argparser(set_current_parser)
    def do_set_current(self, args):
        """从允许的值列表中设置管电流。"""
        self.pfeedback(f"正在将发生器 {args.generator_id} 的电流设置为 {args.current} mA...")
        current = int(args.current * 10)
        data = struct.pack('<BBH', args.generator_id, 0, int(args.current * 10))
        self.client.send_command(Command.SET_CURRENT, data)

    allow_exposure_parser = cmd2.Cmd2ArgumentParser(description="允许球管曝光。")
    allow_exposure_parser.add_argument('id_mask', type=int, help='曝光允许掩码：bit0 代表 A, bit1 代表 B (例如：1 代表 A, 2 代表 B, 3 代表两者)')
    @with_argparser(allow_exposure_parser)
    def do_allow_exposure(self, args):
        """使用位掩码允许球管曝光。"""
        if not 0 <= args.id_mask <= 3:
            self.perror("ID 掩码必须在 0 到 3 之间。")
            return
        self.pfeedback(f"正在设置曝光允许掩码为 {args.id_mask}...")
        data = struct.pack('<B', args.id_mask)
        self.client.send_command(Command.ALLOW_EXPOSURE, data)

    set_max_time_parser = cmd2.Cmd2ArgumentParser(description="设置最大曝光时间。")
    set_max_time_parser.add_argument('generator_id', type=int, choices=[0, 1], help='发生器 ID (0 代表 A, 1 代表 B)')
    set_max_time_parser.add_argument('time', type=float, nargs='?', default=9000.0, help='最大曝光时间 ms (R\'20 系列, 最大 9000ms, 默认 9000)')
    @with_argparser(set_max_time_parser)
    def do_set_max_exposure_time(self, args):
        """设置发生器的最大曝光时间。"""
        if args.time not in MS_R20_VALUES:
            self.perror(f"无效的时间值。允许的值 (ms): {MS_R20_VALUES}")
            return

        max_time_val = int(args.time * 10)  # 5s = 5000ms = 50000 * 0.1ms
        self.pfeedback(f"正在将 G{args.generator_id} 的最大曝光时间设置为 {args.time} ms...")
        data = struct.pack('<B3xI', args.generator_id, max_time_val)
        self.client.send_command(Command.SET_MAX_EXPOSURE_TIME, data)

    def do_enter_exposure_mode(self, _):
        """进入曝光模式。"""
        self.pfeedback("正在进入曝光模式...")
        data = struct.pack('<I', 0x4F50454E)
        self.client.send_command(Command.ENTER_EXPOSURE_MODE, data)

    def do_exit_exposure_mode(self, _):
        """退出曝光模式。"""
        self.pfeedback("正在退出曝光模式...")
        self.client.send_command(Command.EXIT_EXPOSURE_MODE)

    def do_query_move_range(self, _):
        """获取当前可用的移动范围和最大速度 (0x0108)。"""
        self.pfeedback("正在获取行程范围...")
        self.client.send_command(Command.QUERY_MOVE_RANGE)

    set_focus_parser = cmd2.Cmd2ArgumentParser(description="修改焦点 (0x0209)。")
    set_focus_parser.add_argument('generator_id', type=int, choices=[0, 1], help='高压发生器ID (0: A, 1: B)')
    set_focus_parser.add_argument('focus', type=int, choices=[0, 1], help='焦点 (0: 小焦点, 1: 大焦点)')
    @with_argparser(set_focus_parser)
    def do_set_focus(self, args):
        """修改焦点 (0x0209)。"""
        self.pfeedback(f"正在修改发生器 {args.generator_id} 的焦点为 {'大焦点' if args.focus else '小焦点'}...")
        data = struct.pack('<BB', args.generator_id, args.focus)
        self.client.send_command(Command.SET_FOCUS, data)

    def do_reset_estop(self, _):
        """解除急停状态。"""
        self.pfeedback("正在解除急停...")
        # 数据: 0x65727374 (小端序)
        data = struct.pack('<I', 0x65727374)
        self.client.send_command(Command.RESET_ESTOP, data)

    def do_trigger_estop(self, _):
        """触发软件急停。"""
        self.pfeedback("正在触发软件急停...")
        self.client.send_command(Command.TRIGGER_ESTOP)

    def do_query_estop(self, _):
        """查询急停状态。"""
        self.pfeedback("正在查询急停状态...")
        self.client.send_command(Command.QUERY_ESTOP)

    def do_query_upper_limit(self, _):
        """查询上限位状态。"""
        self.pfeedback("正在查询上限位状态...")
        self.client.send_command(Command.QUERY_UPPER_LIMIT)

    def do_query_lower_limit(self, _):
        """查询下限位状态。"""
        self.pfeedback("正在查询下限位状态...")
        self.client.send_command(Command.QUERY_LOWER_LIMIT)

    # --- IO 命令 ---
    set_output_io_parser = cmd2.Cmd2ArgumentParser(description="设置输出 IO 配置。")
    set_output_io_parser.add_argument('value', type=str, help='输出 IO 值 (整数或十六进制字符串，如 0x1A)')
    @with_argparser(set_output_io_parser)
    def do_set_output_io(self, args):
        """设置输出 IO 配置。"""
        try:
            val = int(args.value, 0)
        except ValueError:
            self.perror("无效的值格式。请使用整数或十六进制字符串 (例如 0x1234)。")
            return

        self.pfeedback(f"正在将输出 IO 设置为 0x{val:016x}...")
        data = struct.pack('<Q', val)
        self.client.send_command(Command.SET_OUTPUT_IO, data)

    def do_query_output_io(self, _):
        """查询输出 IO 状态。"""
        self.pfeedback("正在查询输出 IO 状态...")
        self.client.send_command(Command.QUERY_OUTPUT_IO)

    def do_query_input_io(self, _):
        """查询输入 IO 状态。"""
        self.pfeedback("正在查询输入 IO 状态...")
        self.client.send_command(Command.QUERY_INPUT_IO)

    # --- 电源管理命令 ---
    def do_exec_shutdown(self, _):
        """执行关机 (0x0304)。"""
        self.pfeedback("正在执行关机...")
        # 数据: 'stdn' (0x7374646E)
        data = struct.pack('<I', 0x7374646E)
        self.client.send_command(Command.EXEC_SHUTDOWN, data)

    def do_req_shutdown(self, _):
        """请求关机 (0x0305)。"""
        self.pfeedback("正在请求关机...")
        self.client.send_command(Command.REQ_SHUTDOWN)

    def do_exec_poweron(self, _):
        """执行开机 (0x0306)。"""
        self.pfeedback("正在执行开机...")
        # 数据: 'open' (0x6F70656E)
        data = struct.pack('<I', 0x6F70656E)
        self.client.send_command(Command.EXEC_POWERON, data)

    def do_query_power_state(self, _):
        """查询电源状态 (0x0307)。"""
        self.pfeedback("正在查询电源状态...")
        self.client.send_command(Command.QUERY_POWER_STATE)

    def do_query_board_io(self, _):
        """查询板卡功能 IO 状态 (0x0308)。"""
        self.pfeedback("正在查询板卡 IO 状态...")
        self.client.send_command(Command.QUERY_BOARD_IO)

    # --- 寄存器访问命令 ---
    rw_reg_parser = cmd2.Cmd2ArgumentParser(description="读/写寄存器 (透传)。")
    rw_reg_parser.add_argument('operation', type=int, choices=[0, 1], help='操作: 0 代表写, 1 代表读')
    rw_reg_parser.add_argument('width', type=int, choices=[2, 4], help='寄存器宽度: 2 或 4 字节')
    rw_reg_parser.add_argument('address', type=str, help='寄存器地址 (例如 0x1000)')
    rw_reg_parser.add_argument('value', type=str, nargs='?', default='0', help='写入的值 (读取时默认为 0)')
    @with_argparser(rw_reg_parser)
    def do_rw_reg(self, args):
        """使用透传命令读或写寄存器。"""
        try:
            addr = int(args.address, 0)
            val = int(args.value, 0)
        except ValueError:
            self.perror("无效的地址或值格式。请使用整数或十六进制字符串 (例如 0x1000)。")
            return

        op_str = "读取" if args.operation == 1 else "写入"
        self.pfeedback(f"正在发送{op_str}寄存器命令: 地址=0x{addr:04x}, 宽度={args.width}, 值=0x{val:08x}...")

        # 封装: Op(u8), Width(u8), Addr(u16), Data(u32)
        data = struct.pack('<BBHI', args.operation, args.width, addr, val)
        self.client.send_command(Command.PASS_THROUGH, data)

    def postloop(self) -> None:
        """命令循环结束后执行的钩子方法。"""
        self.poutput("正在退出程序。正在清理...")
        self.client.disconnect()


if __name__ == '__main__':
    app = SLZCtrCmd()
    sys.exit(app.cmdloop())
