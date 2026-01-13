import queue
import time
import sys
from PySide6.QtCore import QThread, Signal

# 引入你原来的类
from core.arm.SLZCMD import SLZCtrCmd

class SLZWorkerThread(QThread):
    """
    一个专门运行 SLZCMD 的后台线程。
    它维护一个指令队列，GUI 只需要往队列里扔字符串，它就会执行。
    """
    
    # 定义信号：用于把文本发回给 GUI
    sig_log = Signal(str)

    def __init__(self):
        super().__init__()
        # 线程安全的指令队列
        self.cmd_queue = queue.Queue()
        self.slz_app = None
        self._is_running = True

    @property
    def isRunning(self):
        return self._is_running

    def send_command(self, cmd_str):
        """GUI 调用的方法：发送指令"""
        self.cmd_queue.put(cmd_str)
        print(1111)

    def run(self):
        """线程的主入口"""
        
        # 1. 定义一个中间类，用来拦截输出
        # 这是一个内部类，专门用来“偷听” SLZCtrCmd 的说话
        # 我们在这里把 poutput 等方法“劫持”到我们的信号上
        thread_instance = self

        class InterceptedSLZ(SLZCtrCmd):
            def __init__(self):
                # 调用原版初始化
                # 注意：这里会触发 connect，产生的日志会被下面的方法拦截
                super().__init__()

            # --- 劫持标准输出 ---
            def poutput(self, msg: str = '', *, end: str = '\n') -> None:
                thread_instance.sig_log.emit(str(msg))

            def pfeedback(self, msg: str = '', *, end: str = '\n') -> None:
                thread_instance.sig_log.emit(f"[反馈] {msg}")

            def perror(self, msg: str = '', *, end: str = '\n') -> None:
                thread_instance.sig_log.emit(f"[错误] {msg}")

            def async_alert(self, msg: str = '', *, end: str = '\n') -> None:
                thread_instance.sig_log.emit(f"[异步] {msg}")
            
            # --- 屏蔽掉可能导致阻塞的方法 ---
            def do_continuous_move(self, args):
                self.perror("GUI 模式下暂不支持 continuous_move (避免阻塞线程)。")

        # 2. 实例化 (此时日志会立即通过信号发出)
        try:
            self.slz_app = InterceptedSLZ()
        except Exception as e:
            self.sig_log.emit(f"[系统错误] 初始化失败: {e}")
            return

        self.sig_log.emit("[系统] 机械臂控制线程已就绪，等待指令...")

        # 3. 循环等待指令 (消费者循环)
        while self._is_running:
            try:
                # 从队列获取指令，超时时间 0.1秒，避免死等导致无法退出线程
                cmd_str = self.cmd_queue.get(timeout=0.1)
                
                if cmd_str == "__EXIT__":
                    break
                
                # 执行指令 (使用 cmd2 的 onecmd 方法)
                self.sig_log.emit(f">>> 发送指令: {cmd_str}")
                self.slz_app.onecmd(cmd_str)
                
            except queue.Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                self.sig_log.emit(f"[执行异常] {e}")

        # 线程结束前的清理
        if self.slz_app:
            self.slz_app.client.disconnect()
        self.sig_log.emit("[系统] 线程已停止。")

    def stop(self):
        """停止线程"""
        self._is_running = False
        self.cmd_queue.put("__EXIT__") # 唤醒队列
        self.quit()
        self.wait()
        
    
if __name__ == "__main__":
    # 测试代码：直接运行这个文件会启动线程并发送一些测试指令
    pass
