import keyboard
from PyQt5.QtCore import QThread, pyqtSignal


class StopRunningThread(QThread):
    """ 停止指令运行线程 """
    stopSignal = pyqtSignal()

    def run(self):
        # 监听全局的 "Q + Esc" 组合键
        keyboard.add_hotkey('q+esc', self.on_combination_pressed)
        # 进入线程的主循环
        self.exec_()

    def on_combination_pressed(self):
        """Q + Esc 组合键被按下 """
        # 发出停止信号
        self.stopSignal.emit()
        print("Q + Esc 组合键被按下")


# 全局唯一的 StopRunningThread 对象
stop_running_thread = StopRunningThread()
