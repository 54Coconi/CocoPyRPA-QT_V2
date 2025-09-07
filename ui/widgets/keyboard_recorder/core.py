"""
@author: 54Coconi
@date: 2025-07-28
@version: 1.0.0

键盘录制器核心模块
    - 键盘监听器
    - 控制器
"""

import time

import keyboard
from PyQt5.QtCore import QThread, pyqtSignal, QObject

from .ui import RecorderWidget

_DEBUG = True


class KeyboardListener(QThread):
    """
    键盘监听器
    """
    # 信号：更新操作文本显示（用于UI） / 录制完成后发出结构化历史数据
    operation_update = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, _exit_key="tab+esc", parent=None):
        super().__init__(parent)
        self._exit_key = _exit_key
        self.key_pressed = {}         # {key_name: press_time}
        self.current_operation = []   # 当前操作文本列表
        self.operation_history = []   # 最终结构化输出
        self.running = True

    def run(self):
        """启动键盘监听线程"""
        keyboard.hook(self._process_event)
        # suppress=True 可以禁用键盘事件，使其只对程序起作用，不对系统起作用
        keyboard.wait(self._exit_key, suppress=True)
        self.finished.emit(self.operation_history)

    def stop(self):
        """停止键盘监听线程"""
        keyboard.unhook_all()
        self.running = False

    def _process_event(self, event):
        """处理键盘事件"""
        if not self.running:
            return

        current_time = time.time()
        key = event.name
        event_type = event.event_type

        if event_type == 'down':
            if key not in self.key_pressed:
                self.key_pressed[key] = current_time
                time_str = time.strftime("%H:%M:%S", time.localtime(current_time))
                text = f"按下 ↓: {key} (时间: {time_str})"
                self.current_operation.append(text)

                self.operation_history.append({
                    "type": "keyboard",
                    "action": "keyPress",
                    "key": key,
                    "time": current_time,
                    "duration": None
                })

                self.operation_update.emit("\n".join(self.current_operation))

        elif event_type == 'up':
            if key in self.key_pressed:
                press_time = self.key_pressed.pop(key)
                duration = current_time - press_time
                time_str = time.strftime("%H:%M:%S", time.localtime(current_time))

                text1 = f"持续 ⏱: {duration:.2f} 秒"
                text2 = f"释放 ↑: {key} (时间: {time_str})"
                self.current_operation.extend([text1, text2])

                self.operation_history.append({
                    "type": "flow",
                    "action": "delay",
                    "delay_time": duration
                })
                self.operation_history.append({
                    "type": "keyboard",
                    "action": "keyRelease",
                    "key": key,
                    "time": current_time,
                    "duration": duration
                })

                self.operation_update.emit("\n".join(self.current_operation))

                if not self.key_pressed:
                    self.current_operation.clear()


class Controller(QObject):
    """
    控制器，负责创建 RecorderWidget 和 KeyboardListener 对象，并连接信号

    Attributes:
        closed: 关闭信号

    Args:
        cmd_treeWidget: 命令树控件
        _exit_key: 停止录制的组合键
    """
    closed = pyqtSignal()

    def __init__(self, recorder_widget_class=RecorderWidget, cmd_treeWidget=None, _exit_key="tab+esc"):
        """初始化控制器，创建 UI 和监听器，并连接信号槽"""
        super().__init__()
        self.cmd_treeWidget = cmd_treeWidget
        self._exit_key = _exit_key

        self.widget = recorder_widget_class(stop_tip_text=f"{_exit_key.title()}: 退出", parent=cmd_treeWidget)
        self.listener = KeyboardListener(_exit_key=_exit_key)
        # 存储录制历史
        self._history = []

        # 连接信号
        self.widget.closed.connect(self.close_window)
        self.listener.operation_update.connect(self.widget.set_operation)
        self.listener.finished.connect(self._on_finished)

    def start_recording(self):
        """启动录制器（显示窗口并开始监听）"""
        self.widget.show()
        self.listener.start()

    def stop_recording(self):
        """手动停止录制（不常用，建议使用组合键）"""
        self.listener.stop()
        self.widget.close()

    def get_parsed_history(self):
        """返回过滤后的结构化的按键操作历史"""
        from .operation_parser import parse_operation_history
        return parse_operation_history(self._history)

    def close_window(self):
        """关闭窗口"""
        self._build_tree_items()
        self.closed.emit()

    def _on_finished(self, history: list):
        """录制完成：关闭界面、打印结构化数据"""
        self._history = history
        self.widget.close()

        if _DEBUG:
            # 打印结构化按键操作历史（人类可读格式）
            print("录制的结构化数据如下：")
            print("=" * 60)
            for item in self._history:
                print(item)

            print("\n解析后的结构化数据如下：")
            print("=" * 60)
            from .operation_parser import parse_operation_history
            parse_operation = parse_operation_history(self._history)
            for item in parse_operation:
                print(item)

            # print("\n操作记录如下：")
            # print("=" * 60)
            # for item in operation_history_to_text(parse_operation):
            #     print(item)

    def _build_tree_items(self):
        """将操作历史转换为树节点"""
        if not self.cmd_treeWidget:
            return
            
        from PyQt5.QtWidgets import QMessageBox
        
        # 若 cmd_tree 不为空则提示覆盖/追加
        if self.cmd_treeWidget.topLevelItemCount() > 0:
            msg = QMessageBox(self.cmd_treeWidget)
            btn_cover = msg.addButton("覆盖", QMessageBox.YesRole)
            btn_add = msg.addButton("追加", QMessageBox.NoRole)
            btn_cancel = msg.addButton("取消", QMessageBox.RejectRole)
            msg.setWindowTitle("提示")
            msg.setText("当前指令编辑器不为空，是否覆盖或追加?\n【覆盖】：覆盖当前指令\n【追加】：追加到末尾")
            msg.setDefaultButton(btn_cover)
            msg.exec_()
            if msg.clickedButton() == btn_cover:
                self.cmd_treeWidget.clear()
            elif msg.clickedButton() == btn_cancel:
                return
        # 解析并创建
        for op in self.get_parsed_history():
            self._create_tree_item(op)

    def _create_tree_item(self, record: dict):
        """调用 API 创建树节点"""
        from .tree_build_api import create_tree_item
        create_tree_item(self.cmd_treeWidget, record)
