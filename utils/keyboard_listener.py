from PyQt5.QtCore import QObject, pyqtSignal, QThread
from pynput import keyboard
import time


class GlobalKeyListener(QThread):
    """全局键盘监听器"""
    stop_signal = pyqtSignal()  # 发送停止信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listener = None  # 键盘监听器对象
        self.pressed_keys = set()  # 记录当前按下的按键

    def run(self):
        """启动键盘监听"""
        print("[GlobalKeyListener] 键盘监听器启动")
        with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:
            self.listener = listener
            listener.join()  # 阻塞线程，直到监听器停止

    def on_press(self, key):
        """按键事件处理"""
        try:
            self.pressed_keys.add(key)
            # 检测 Ctrl + Esc
            if keyboard.Key.esc in self.pressed_keys and \
                    (keyboard.Key.ctrl_l in self.pressed_keys or keyboard.Key.ctrl_r in self.pressed_keys):
                print("[GlobalKeyListener] 检测到 Ctrl + Esc 组合键")
                self.stop_signal.emit()  # 发送停止信号
        except Exception as e:
            print(f"[GlobalKeyListener] 错误: {e}")

    def on_release(self, key):
        """释放按键事件处理"""
        try:
            self.pressed_keys.discard(key)
        except Exception as e:
            print(f"[GlobalKeyListener] 释放按键时出错: {e}")

    def stop(self):
        """停止监听"""
        print("[GlobalKeyListener] 停止键盘监听器")
        if self.listener:
            self.listener.stop()
        self.quit()


class CommandExecutor(QObject):
    """指令执行器"""
    terminate_signal = pyqtSignal()  # 终止信号

    def __init__(self):
        super().__init__()
        self.running = False

    def execute(self):
        """模拟指令执行"""
        print("[CommandExecutor] 开始执行任务...")
        self.running = True
        while self.running:
            print("[CommandExecutor] 任务进行中...")
            time.sleep(1)  # 模拟任务的运行，避免阻塞

        print("[CommandExecutor] 任务已终止")

    def terminate_execution(self):
        """终止指令执行"""
        print("[CommandExecutor] 收到终止信号，正在停止...")
        self.running = False


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # 创建键盘监听器
    key_listener = GlobalKeyListener()
    key_listener.start()

    # 创建指令执行器
    executor = CommandExecutor()

    # 当检测到 Ctrl+Esc 时发送终止信号
    key_listener.stop_signal.connect(executor.terminate_execution)

    # 模拟执行任务
    executor_thread = QThread()
    executor.moveToThread(executor_thread)
    executor_thread.started.connect(executor.execute)
    executor_thread.start()

    sys.exit(app.exec_())
