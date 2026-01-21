import socket
import struct
import time

class MotorDriver:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(0.1) # 设置非阻塞接收的超时时间
        self.buffer = bytearray() # 内部维护接收缓冲区
    
    def connect(self, ip, port, status_label, callback=None):   
        try:
            self.ip = ip
            self.port = port
            self.sock.connect((self.ip, self.port))
            
            if callable:
                callback(True, status_label, f"成功连接到 {ip} 并初始化配置。")

        except Exception as e:
            if callback:
                callback(False, status_label, f"连接失败：{e}")

    def close(self):
        self.sock.close()

    def _ctr_format(self, cmd_id, data):
        """
        对应 ctr_format.m
        协议结构: Head(4) + ID(4) + Flag(2) + Len(2) + Data(N*4)
        """
        head = b'\xAA\xAA\xAA\xAA'
        
        # ID: MATLAB中是 uint32(id) 转 uint8，实际上占4字节
        # '<I' 代表 Little Endian 无符号 int
        ctr_id_bytes = struct.pack('<I', cmd_id) 
        
        # Flag: MATLAB typecast(0x0000, 'uint8') -> 2字节 0
        flag_bytes = b'\x00\x00'
        
        # Data 处理
        if data is None:
            data = []
        if not isinstance(data, list) and not isinstance(data, tuple):
            data = [data]
            
        data_bytes = bytearray()
        for val in data:
            # 对应 any(data < 0) 的判断，统一使用 signed int32 ('<i')
            # 这样既能表示负数，也能表示正数（在范围内）
            data_bytes.extend(struct.pack('<i', int(val)))
            
        # Len: 数据长度 (字节数)
        d_len = len(data_bytes)
        d_len_bytes = struct.pack('<H', d_len) # uint16
        
        # 拼接
        out = head + ctr_id_bytes + flag_bytes + d_len_bytes + data_bytes
        return out

    def _ctr_deformat(self):
        """
        对应 ctr_deformat.m
        从 self.buffer 中解析完整的数据包
        """
        packets = []
        head = b'\xAA\xAA\xAA\xAA'
        
        while True:
            # 1. 检查缓冲区长度是否足够包含最小头部 (12字节)
            if len(self.buffer) < 12:
                break
            
            # 2. 寻找头部
            head_idx = self.buffer.find(head)
            if head_idx == -1:
                # 没有找到头部，保留最后3个字节（防止头部被切断），其余丢弃
                self.buffer = self.buffer[-3:]
                break
            
            if head_idx > 0:
                # 丢弃头部之前的垃圾数据
                self.buffer = self.buffer[head_idx:]
                # 重新检查长度
                if len(self.buffer) < 12:
                    break
            
            # 3. 解析长度 (Offset 10, 2 bytes, uint16)
            # buffer[10:12]
            d_len = struct.unpack('<H', self.buffer[10:12])[0]
            
            # 4. 检查是否接收完整
            total_len = 12 + d_len
            if len(self.buffer) < total_len:
                break # 数据还不够，等待下次读取
            
            # 5. 提取数据
            # ID (Offset 4, 4 bytes, uint32) - MATLAB代码其实只用了前2字节作为ID，后2字节断言为0
            # 这里我们按 uint32 解析，和发送保持一致
            ctr_id = struct.unpack('<I', self.buffer[4:8])[0]
            
            # Flag (Offset 8, 2 bytes, uint16)
            flag = struct.unpack('<H', self.buffer[8:10])[0]
            
            # Payload
            payload = self.buffer[12 : 12 + d_len]
            
            packets.append({
                'id': ctr_id,
                'flag': flag,
                'data': payload
            })
            
            # 6. 移除已处理的数据
            self.buffer = self.buffer[total_len:]
            
        return packets

    def doctr(self, cmd_id, data=None, with_succ=True):
        """
        对应 doctr.m
        发送指令并等待 ACK
        """
        packet = self._ctr_format(cmd_id, data)
        self.sock.sendall(packet)
        
        timeout_counter = 500 # 对应 timeout = 500
        
        while timeout_counter > 0:
            time.sleep(0.001) # 1ms
            timeout_counter -= 1
            
            # 尝试读取数据
            try:
                recv_data = self.sock.recv(4096)
                if recv_data:
                    self.buffer.extend(recv_data)
            except socket.timeout:
                pass # 没读到数据继续循环
            except BlockingIOError:
                pass
            
            # 尝试解析
            parsed_packets = self._ctr_deformat()
            
            for pkt in parsed_packets:
                print(f"Recv ID: 0x{pkt['id']:04X}, Flag: 0x{pkt['flag']:04X}") # 对应 disp_ctrid
                
                # 匹配 ID (注意 MATLAB 里判断的是 id == x(1)，这里 pkt['id'] 已经是整数)
                if pkt['id'] == cmd_id:
                    # 检查 Error bit (Flag 的第2位, bitand(temp(2), 2))
                    if (pkt['flag'] & 2) != 0:
                        raise RuntimeError("General Error Ack received")
                    
                    # 检查业务逻辑错误
                    # MATLAB: if typecast(uint8(temp(3:6)), 'uint32') ~= 0
                    if with_succ and len(pkt['data']) >= 4:
                        err_code = struct.unpack('<I', pkt['data'][0:4])[0]
                        if err_code != 0:
                            user_input = input(f"Error code {err_code} detected. ACK 是否正确? (y/n): ")
                            if user_input.lower() == 'n':
                                raise RuntimeError("Error Ack confirmed by user")
                    
                    return pkt['data'] # 返回 payload 字节数据
                
                else:
                    # 如果收到了其他 ID 的包，MATLAB 是存入 outs 并 continue
                    # 这里简化处理：打印日志，忽略非目标包，继续等待目标包
                    print(f"Ignored packet with ID 0x{pkt['id']:04X} (Expected 0x{cmd_id:04X})")

        raise TimeoutError("Error: Timeout waiting for ACK")

# ==========================================
# 主逻辑 (对应 Untitled.m)
# ==========================================

# core/motor.py
# 这里的 MotorDriver 类定义保持不变，省略不写...

def control_motor(driver, posstart=0, posend=400, speed=100, time=0, start_event=None):
    """
    driver: 已经连接好的 MotorDriver 实例
    posstart: 起点位置
    posend: 终点位置
    speed: 速度
    start_event: 线程同步事件
    """
    # 参数设置
    start_pos = posstart * 100
    end_pos = posend * 100
    run_speed = speed * 100
    
    # 静止采集
    if run_speed == 0 and time != 0:
        print('静止采集模式')
        try:
            print("Tube ON")
            driver.doctr(0x7F01, [1]) 
            time.sleep(2)
            
            # 4. 发出采集信号
            if start_event is not None:
                print(">>> Signal Triggered: Start Acquisition!")
                start_event.set()
                
            # 球管比采集时间多等0.5s
            time.sleep(time+0.5)
            # 6. Tube OFF
            print("Tube OFF")
            driver.doctr(0x7F01, [0])
            time.sleep(2) # 稍微多等一下
        
        except Exception as e:
            print(f"Error in Tube ON/OFF: {e}")
            raise e
        return
    
    use_y = True
    id = 0x0400
    def getId(id):
        if use_y:
            return id + 0x0100 
        return id
    def moveInSpeedMode(drv: MotorDriver, speed: int, pos: int):
        ack_data = drv.doctr(getId(0x0401), [], with_succ=False)
        if len(ack_data) >= 8:
            current_pos = struct.unpack('<i', ack_data[4:8])[0]
        else:
            current_pos = 0
        if current_pos < pos:
            drv.doctr(getId(0x0402), [1, abs(speed), 2, pos], with_succ=True)
        else:
            drv.doctr(getId(0x0402), [1, -abs(speed), 1, pos], with_succ=True)
    
    try:
        print("\n--- Processing X Axis ---")
        
        # 1. 检查状态 (使用传入的 driver)
        ack_data = driver.doctr(getId(0x0401), [], with_succ=False)
        
        if len(ack_data) >= 8:
            current_x = struct.unpack('<i', ack_data[4:8])[0]
        else:
            current_x = 0
            
        print(f"Current X: {current_x}")
        
        # 2. 回原点逻辑
        if abs(current_x - 600) > 200:
            print("Resetting X position...")
            moveInSpeedMode(driver, 10000, 600)
            # driver.doctr(0x0402, [2, 600, 1, 10000], with_succ=True)
            time.sleep(2)

        # # # 3. 移动到出发位置
        # print(f"Moving to {start_pos}...")
        # driver.doctr(0x0402, [1, run_speed, 2, start_pos], with_succ=True)
        # # 等待运动结束
        # time.sleep((start_pos/run_speed)+0.5)
        
        
        # 3. Tube ON
        print("Tube ON")
        driver.doctr(0x7F01, [1]) 
        time.sleep(2)
        
        # 4. 发出采集信号
        if start_event is not None:
            print(">>> Signal Triggered: Start Acquisition!")
            start_event.set()

        # 5. 运动
        print(f"Moving to {end_pos}...")
        moveInSpeedMode(driver, run_speed, end_pos)
        # driver.doctr(0x0402, [1, run_speed, 2, end_pos], with_succ=True)
        moving_time = (end_pos-start_pos)/run_speed + 2
        print(f"moving time: {moving_time}")
        # 等待运动结束
        time.sleep(moving_time)

        # 6. Tube OFF
        print("Tube OFF")
        driver.doctr(0x7F01, [0])
        time.sleep(2) # 稍微多等一下

        # 7. 回退
        print("Moving back...")
        moveInSpeedMode(driver, 4000, 900)
        # driver.doctr(0x0402, [1, -4000, 1, 900], with_succ=True)

    except Exception as e:
        print(f"An error occurred in motor control: {e}")
        # 【注意】这里发生了错误也不要 close，除非是网络断开（BrokenPipe），
        # 否则留给上层决定是否重连。
        raise e 

if __name__ == "__main__":
    control_motor()