"""
@author: 54Coconi
@date: 2025-01-10
@version: 1.0.0
@path: ui/widgets/KeyboardRecord.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    键盘录制器模块

        - 使用 PyQt5 实现键盘录制器界面显示
        - 使用 keyboard 库实现键盘监听
        - 本键盘录制器支持按键组合，支持按键按下到释放之间的持续时间
"""


import time
from collections import OrderedDict

import keyboard
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QTreeWidgetItem, QTreeWidget, QMessageBox

from core.register import registry

_DEBUG = True


LABEL_WIDTH = 280
LABEL_HEIGHT = 250
# 标签样式
LABEL_STYLE = """
QLabel { 
    border-width: 3px;
    border-style: solid;
    border-color: rgb(36,216,255);
    border-radius: 8px;
    background-color: rgba(50,50,50, 150);
    padding-left: 2px;
    padding-top: 2px;
    font-size: 18px;
    font-family: 'Microsoft YaHei';
    color : rgba(255,255,134,255);
}
"""


def parse_operation_history(operation_history):
    """处理操作历史，对于组合键在第一个释放的按键前显示持续时间"""
    processed_operations = []
    i = 0
    skip_duration = 0  # 需要跳过持续时间的次数

    while i < len(operation_history):
        operation = operation_history[i]

        # 如果是按下操作，直接添加
        if '按下' in operation:
            processed_operations.append(operation)
            i += 1
            continue

        # 如果是持续时间
        if '持续' in operation:
            if skip_duration - 1 > 0:
                skip_duration -= 1
                i += 1
                continue

            next_duration_index = i + 2  # 跳过下一个释放操作，检查后面的持续时间

            # 如果后面还有持续时间，说明是组合键的一部分
            if next_duration_index < len(operation_history) and '持续' in operation_history[next_duration_index]:

                # 找到最后一个持续时间
                last_duration = None
                temp_index = i
                while temp_index < len(operation_history) and '持续' in operation_history[temp_index]:
                    last_duration = operation_history[temp_index]
                    temp_index += 2
                    skip_duration += 1

                # 使用最后找到的持续时间
                if i == next_duration_index - 2:
                    processed_operations.append(last_duration)
            else:
                # 单键操作，直接添加当前持续时间
                processed_operations.append(operation)

            i += 1
            continue

        # 如果是释放操作，直接添加
        if '释放' in operation:
            processed_operations.append(operation)
            i += 1
            continue

        i += 1

    return processed_operations


class KeyboardRecorder(QMainWindow):
    """键盘录制器主窗口"""
    close_signal = pyqtSignal()  # 关闭信号

    def __init__(self, cmd_treeWidget: QTreeWidget, parent=None):
        super().__init__(parent)
        self.cmd_treeWidget = cmd_treeWidget
        self.cmd_registry = registry  # 指令注册表
        self.setWindowTitle("键盘录制器")
        self.setWindowIcon(QIcon(":/icons/keys-record"))
        # 设置窗口无边框、窗口置顶，窗体背景透明
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.move(0, 0)  # 设置主窗口为屏幕左上角
        self.resize(LABEL_WIDTH, LABEL_HEIGHT)  # 设置主窗口大小

        # 初始化显示标签
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignLeft)
        self.label.setStyleSheet(LABEL_STYLE)
        self.label.setText("Tab+Esc 停止键盘录制\n\n")

        self.label.move(0, 0)  # 设置标签位置为主窗口的左上角
        self.label.resize(LABEL_WIDTH, LABEL_HEIGHT)  # 设置标签大小

        # 初始化键盘监听线程
        self.keyboard_thread = KeyboardListenerThread(self.label)
        self.keyboard_thread.create_cmd_signal.connect(self.add_operation)
        self.keyboard_thread.stop_signal.connect(self.stop_recording)

        # 启动线程
        self.keyboard_thread.start()

    def add_operation(self, operation):
        """添加操作到操作历史并更新标签内容"""
        # 清空标签内容，显示当前操作
        self.label.setText(operation)

    def stop_recording(self, operation_history: list):
        """停止录制并退出程序"""
        self.keyboard_thread.stop()
        self.creat_tree_item(operation_history)
        self.close()

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.close_signal.emit()
        super().closeEvent(event)

    def creat_tree_item(self, operation_history: list):
        """创建树形控件"""
        # 判断当前指令编辑器内容是否为空
        if self.cmd_treeWidget.topLevelItemCount() > 0:
            msg_box = QMessageBox(self.cmd_treeWidget)

            button_cover = msg_box.addButton("覆盖", QMessageBox.YesRole)
            button_addition = msg_box.addButton("追加", QMessageBox.NoRole)
            button_cancel = msg_box.addButton("取消", QMessageBox.RejectRole)

            msg_box.setWindowTitle("提示")
            msg_box.setText("当前指令编辑器不为空，是否覆盖或追加?\n"
                            "【覆盖】：覆盖当前指令编辑器内容\n"
                            "【追加】：追加到当前指令编辑器内容后面")
            msg_box.setDefaultButton(button_cover)  # 设置默认按钮
            msg_box.exec_()

            if msg_box.clickedButton() == button_cover:
                self.cmd_treeWidget.clear()
            elif msg_box.clickedButton() == button_cancel:
                return
            else:
                pass

        for i, operation in enumerate(operation_history, start=1):
            key = operation.split(': ')[1].split(' (时间')[0]  # 获取按键
            duration = operation.split(': ')[1].split(' 秒')[0]  # 获取持续时间

            if key.lower() == 'tab' and \
                    (i < len(operation_history) and
                     operation_history[i].split(': ')[1].split(' (时间')[0].lower() == 'esc') or \
                    i == len(operation_history):
                continue
            elif key.lower() == 'esc' and \
                    i == len(operation_history) and \
                    operation_history[i - 2].split(': ')[1].split(' (时间')[0].lower() == 'tab':
                continue
            if '按下' in operation:
                item_name = f"键盘按下-{str(key)}"
                # 构建节点数据
                item_data = {
                    "type": "keyboard",
                    "action": "keyPress",
                    "icon": ":/icons/key-press",
                    "params": {
                        "name": item_name,
                        "key": str(key),
                        "retries": 0,
                        "is_active": True,
                        "use_pynput": False,
                        "status": 0
                    }
                }
                # 使用 OrderedDict 创建有序字典
                item_data = OrderedDict(item_data)
                item = QTreeWidgetItem([item_name])  # 创建节点
                item.setData(0, Qt.UserRole, item_data)  # 设置数据
                item.setIcon(0, QIcon(":/icons/key-press"))  # 设置图标
                item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
                self.cmd_registry.register_command(item)  # 注册指令
                self.cmd_treeWidget.addTopLevelItem(item)
            elif '释放' in operation:
                item_name = f"键盘释放-{str(key)}"
                # 构建节点数据
                item_data = {
                    "type": "keyboard",
                    "action": "keyRelease",
                    "icon": ":/icons/key-release",
                    "params": {
                        "name": item_name,
                        "key": str(key),
                        "retries": 0,
                        "is_active": True,
                        "use_pynput": False,
                        "status": 0
                    }
                }
                # 使用 OrderedDict 创建有序字典
                item_data = OrderedDict(item_data)
                item = QTreeWidgetItem([item_name])  # 创建节点
                item.setData(0, Qt.UserRole, item_data)  # 设置数据
                item.setIcon(0, QIcon(":/icons/key-release"))  # 设置图标
                item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
                self.cmd_registry.register_command(item)  # 注册指令
                self.cmd_treeWidget.addTopLevelItem(item)
            elif '持续' in operation:
                # 构建节点数据
                item_data = {
                    "type": "flow",
                    "action": "delay",
                    "icon": ":/icons/delay",
                    "params": {
                        "name": "等待 " + duration + " 秒",
                        "delay_time": float(duration),
                        "is_active": True,
                        "status": 0
                    }
                }
                # 使用 OrderedDict 创建有序字典
                item_data = OrderedDict(item_data)
                item = QTreeWidgetItem(["等待 " + duration + " 秒"])  # 创建节点
                item.setData(0, Qt.UserRole, item_data)  # 设置数据
                item.setIcon(0, QIcon(":/icons/delay"))  # 设置图标
                item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
                self.cmd_registry.register_command(item)  # 注册指令
                self.cmd_treeWidget.addTopLevelItem(item)
            else:
                pass


class KeyboardListenerThread(QThread):
    """键盘监听线程"""
    create_cmd_signal = pyqtSignal(str)  # 发送创建信号
    stop_signal = pyqtSignal(list)  # 发送停止信号, 传递操作历史

    def __init__(self, label: QLabel, parent=None):
        super().__init__(parent)
        self.label = label  # 标签控件
        self.key_pressed = {}  # 记录按下的键（键为按键字符，值为按下时间）
        self.running = True  # 标记线程是否运行

        self.current_operation = []  # 记录当前操作
        self.operation_history = []  # 存储所有操作历史

    def run(self):
        """ 键盘监听线程的主循环 """
        keyboard.hook(self._process_event)
        keyboard.wait('Tab+Esc', suppress=True)
        print("已按下 Tab+Esc 停止键盘录制")
        self.stop_signal.emit(parse_operation_history(self.operation_history))

    def stop(self):
        """ 停止键盘监听线程 """
        keyboard.unhook_all()
        self.running = False

        if _DEBUG:
            print("原来的指令列表:")
            for operation in self.operation_history:
                print(operation)
                print("-" * 20)

            print("=" * 100)

            print("解析后的指令列表:")
            new_operation_history = parse_operation_history(self.operation_history)
            for operation in new_operation_history:
                print(operation)
                print("-" * 20)

    def _process_event(self, event):
        """ 处理键盘事件 """
        if not self.running:
            return

        current_time = time.time()
        key = event.name
        event_type = event.event_type

        if event_type == 'down':
            if key not in self.key_pressed:
                self.key_pressed[key] = current_time
                self._add_key_down(key, current_time)
        elif event_type == 'up':
            if key in self.key_pressed:  # 判断该键是否已经按下
                press_time = self.key_pressed[key]
                duration = current_time - press_time  # 计算按下并释放的间隔
                self._add_key_up(key, current_time, duration)
                del self.key_pressed[key]
                # 如果所有按键都已释放，记录完整操作
                if not self.key_pressed:
                    self._complete_operation()

    def _add_key_down(self, key, timestamp):
        """ 添加按键按下事件 """
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
        operation = f"按下 ↓: {key} (时间: {time_str})"
        self.current_operation.append(operation)  # 添加到当前操作
        self.operation_history.append(operation)
        # 清空标签内容，显示当前操作
        self.create_cmd_signal.emit("\n".join(self.current_operation))

    def _add_key_up(self, key, timestamp, duration):
        """ 添加按键释放事件 """
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
        release_operation = f"释放 ↑: {key} (时间: {time_str})"
        duration_operation = f"持续 ⏱: {duration:.2f} 秒"
        # 添加到当前操作
        self.current_operation.append(duration_operation)
        self.current_operation.append(release_operation)

        # 添加到操作历史
        self.operation_history.append(duration_operation)
        self.operation_history.append(release_operation)

        # 更新标签内容
        self.create_cmd_signal.emit("\n".join(self.current_operation))

    def _complete_operation(self):
        """ 完成一次完整操作 """
        # 将当前操作记录到标签中
        operation_text = "\n".join(self.current_operation)  # 显示当前操作
        self.create_cmd_signal.emit(operation_text)

        # 清空当前操作记录
        self.current_operation.clear()
