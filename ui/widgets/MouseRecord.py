"""
@author: 54Coconi
@date: 2024-11-26
@version: 1.0.0
@path: ui/widgets/MouseRecord.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    鼠标录制器模块

        - 使用 PyQt5 实现录制器界面显示
        - 使用 pynput 库实现鼠标监听
        - 本模块支持的鼠标动作有：鼠标移动、左键单击、左键双击、右键单击、中间单击、左键拖动、滚轮竖直滚动
"""

import time
from collections import OrderedDict

import keyboard
import pyautogui
from PyQt5.QtGui import QIcon

from pynput import mouse
from screeninfo import get_monitors

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QTreeWidget, QTreeWidgetItem, QMessageBox, \
    QSystemTrayIcon

from core.register import registry

from utils.QSSLoader import QSSLoader

import resources_rc

_DEBUG = True

# 初始配置变量
LABEL_WIDTH = 210
LABEL_HEIGHT = 200
LABEL_STYLE = """
QLabel { 
    border-width: 3px;
    border-style: solid;
    border-color: rgb(255,18,237);
    border-radius: 5px;
    background-color: rgba(80,80,80, 120);
    padding-left: 2px;
    padding-top: 2px;
    font-size: 16px;
    font-family: 'Microsoft YaHei';
    color : rgba(255,255,134,255);
}
"""


def set_label_size(width, height):
    """ 设置标签大小 """
    global LABEL_WIDTH, LABEL_HEIGHT
    LABEL_WIDTH = width
    LABEL_HEIGHT = height


# 获取屏幕分辨率
def get_screen_resolution() -> tuple[int, int]:
    """
    获取屏幕分辨率
    :return: 屏幕宽度, 屏幕高度
    """
    monitor = get_monitors()[0]
    return monitor.width, monitor.height


# 规范坐标值的装饰器
def normalize_coordinates_decorator(func):
    """
    规范坐标值的装饰器
    :param func: 传入的函数
    :return: 规范化后的函数
    """

    def wrapper(*args, **kwargs):
        """
        鼠标事件的回调函数的第2和第3个参数是x和y坐标
        :param args:
        :param kwargs:
        :return:
        """
        screen_width, screen_height = get_screen_resolution()
        # 假设鼠标事件的回调函数的第2和第3个参数是x和y坐标
        x, y = args[1], args[2]
        # 使 0 <= x <= screen_width - 1
        x = max(0, min(x, screen_width - 1))
        # 使 0 <= y <= screen_height - 1
        y = max(0, min(y, screen_height - 1))
        # 使用规范化后的坐标调用原函数
        return func(args[0], int(x), int(y), *args[3:], **kwargs)

    return wrapper


class MouseListenerThread(QThread):
    """鼠标监听线程"""

    def __init__(self, label: QLabel, parent=None):
        super().__init__(parent)
        self.label = label  # 标签控件
        self.last_click_time = 0  # 记录上次点击的时间
        self.is_dragging = False  # 标记是否正在拖拽
        self.start_pos = (0, 0)  # 初始化拖拽起点
        self.screen_w, self.screen_h = get_screen_resolution()  # 获取屏幕分辨率
        self.is_top_left = True  # 标记标签是否在左上角
        self.listener = None  # 初始化鼠标监听器
        self.running = True  # 标记线程是否运行

    def run(self):
        """ 启动鼠标监听 """
        self.listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.listener.start()
        self.listener.join()  # 阻塞线程

    def stop(self):
        """ 停止鼠标监听 """
        self.running = False
        if self.listener:
            self.listener.stop()

    @normalize_coordinates_decorator
    def on_move(self, x, y):
        """
        鼠标移动事件处理
        :param x: 横坐标
        :param y: 纵坐标
        """
        self.move_label(x, y)
        self.updateLabel('移动', (x, y))

    def on_click(self, x, y, button, pressed):
        """
        鼠标点击事件处理
        :param x: 横坐标
        :param y: 纵坐标
        :param button: 按键（左键/右键）
        :param pressed: 是否按下
        """
        # 记录当前时间
        current_time = time.time()
        # 处理鼠标左键事件
        if button == mouse.Button.left:
            if pressed:
                # 判断是否为双击的时间阈值
                # print('两次操作间隔：', current_time - self.last_click_time)
                if current_time - self.last_click_time < 0.4:
                    # 双击事件逻辑
                    self.updateLabel('左键双击', (x, y))
                    self.start_pos = None  # 重置起始位置
                    self.is_dragging = False  # 重置拖拽状态
                else:
                    # 更新点击时间并记录起始位置，准备拖拽或单击处理
                    self.last_click_time = current_time
                    self.start_pos = (x, y)
                    self.is_dragging = True  # 假设开始拖拽
            else:
                # 鼠标左键释放，判断拖拽或单击
                if self.is_dragging:
                    # 拖拽事件逻辑，通过时间判断是否实际拖拽
                    duration = current_time - self.last_click_time
                    # 判断是否为拖动的时间阈值, 且始末位置不同
                    if duration >= 0.2 and self.start_pos != (x, y):
                        self.updateLabel(
                            '拖动', (x, y), start_pos=self.start_pos, duration=duration)
                    else:
                        # 若非拖拽，且释放时间距上次点击小于 0.2 秒，则为单击
                        self.updateLabel('左键单击', (x, y))
                    self.start_pos = None
                    self.is_dragging = False  # 重置拖拽状态

        # 处理鼠标右键事件
        elif button == mouse.Button.right and not pressed:
            # 右键点击事件逻辑
            self.updateLabel('右键单击', (x, y))

        # 处理鼠标中键事件
        elif button == mouse.Button.middle and not pressed:
            # 中键按下事件逻辑
            self.updateLabel('中键点击', (x, y))

        # 重置时间戳
        self.last_click_time = current_time

    def on_scroll(self, x, y, dx, dy):
        """ 鼠标滚轮事件处理 """
        self.updateLabel('滚轮', (x, y), scroll=(dx, dy))

    def updateLabel(self, action_type, pos, start_pos=None, scroll=None, duration=None):
        """
        更新标签内容
        :param action_type: 操作类型
        :param pos: 当前坐标(x,y)
        :param start_pos: 拖拽开始坐标
        :param scroll: 滚轮数值
        :param duration: 拖动间隔
        """
        color = pyautogui.screenshot().getpixel(pos)
        # 根据不同的操作类型，更新标签的显示信息
        if action_type == '移动':
            text = f"操作类型: 移动\n" \
                   f"当前坐标: {pos}\n" \
                   f"RGB色值: {color}"
        elif action_type == '左键单击':
            text = f"操作类型: 左键单击\n" \
                   f"当前坐标: {pos}\n" \
                   f"RGB色值: {color}"
        elif action_type == '左键双击':
            text = f"操作类型: 左键双击\n" \
                   f"当前坐标: {pos}\n" \
                   f"RGB色值: {color}"
        elif action_type == '右键单击':
            text = f"操作类型: 右键单击\n" \
                   f"当前坐标: {pos}\n" \
                   f"RGB色值: {color}"
        elif action_type == '拖动':
            text = f"操作类型: 拖动\n" \
                   f"起点坐标: {start_pos}\n" \
                   f"终点坐标: {pos}\n" \
                   f"拖动时长: {'%.2f' % duration} s\n" \
                   f"RGB色值: {color}"
        elif action_type == '滚轮':
            text = f"操作类型: 滚轮\n" \
                   f"当前坐标: {pos}\n" \
                   f"滚动方向: {scroll}\n" \
                   f"RGB色值: {color}"
        elif action_type == '中键点击':
            text = f"操作类型: 中键点击\n" \
                   f"当前坐标: {pos}\n" \
                   f"RGB色值: {color}"
        else:
            text = "类型未知"
        self.label.setText(text)

    def move_label(self, x, y):
        """ 移动标签 """
        # 判断当前鼠标是否在标签的外边界50像素范围内
        if self.is_top_left and \
                (x < self.label.width() + 50 and y < self.label.height() + 50):
            # 移动标签到屏幕右下角
            self.label.move(self.screen_w - self.label.width(), self.screen_h - self.label.height())
            self.is_top_left = False  # 标记标签是否在左上角
        elif not self.is_top_left and \
                (x > self.screen_w - self.label.width() - 50 and y > self.screen_h - self.label.height() - 50):
            # 移动标签到屏幕左上角
            self.label.move(0, 0)
            self.is_top_left = True  # 标记标签是否在左上角


class KeyboardListenerThread(QThread):
    """键盘监听线程"""
    create_cmd_signal = pyqtSignal(dict)  # 发送创建信号,参数为字典
    stop_signal = pyqtSignal()  # 发送停止信号

    # 中文到英文的映射字典
    translation_dict = {
        '操作类型': 'action',
        '起点坐标': 'start_pos',   # 鼠标拖动起始位置 start_pos
        '当前坐标': 'target_pos',  # 鼠标目标位置 target_pos
        '终点坐标': 'target_pos',  # 鼠标拖动目标位置 target_pos
        '拖动时长': 'duration',
        '滚动方向': 'scroll',
        'RGB色值': 'RGB_color',
    }

    def __init__(self, label: QLabel, parent=None):
        super().__init__(parent)
        self.label = label  # 标签控件
        self.last_enter_time = 0  # 记录上次按下 enter 的时间
        self.cmd_list = []  # 存储指令列表

    def run(self):
        """ 键盘监听线程的主循环 """
        # 按下回车键，打印 label 的内容
        keyboard.add_hotkey('enter', self.print_label_text)

        # TODO: 这里不能采用以下这种方式监听Esc键，因为不会阻塞线程导致弹窗一闪而过
        # keyboard.add_hotkey('esc', self.stop_signal.emit)

        # 采用阻塞方式等待用户按下Esc键
        # suppress=True 参数表示在检测到Esc键按下时，不会触发实际的键盘事件，避免了Esc键的默认行为
        keyboard.wait("esc", suppress=True)
        self.stop_signal.emit()

    def stop(self):
        """ 停止键盘监听线程 """
        keyboard.unhook_all_hotkeys()  # 移除所有的热键
        self.quit()

    # 打印 label 的内容到控制台
    def print_label_text(self):
        """
        打印 label 的内容
        """
        current_time = time.time()
        # 检查两次 Enter 键按下的时间间隔是否大于0.5秒
        if current_time - self.last_enter_time > 0.5:
            self.last_enter_time = current_time
            # 打印 label 的内容
            label_text = self.label.text()
            if label_text:
                action = label_text.split('\n')
                action = self.create_cmd(action)
                self.cmd_list.append(action)
                self.create_cmd_signal.emit(action)
                print('\n------------------------')
                print(f"[1 次操作]：{action}")
                print('------------------------\n')
                print("[所有操作]：")
                for i in self.cmd_list:
                    print(i)
        else:
            print(f"时间间隔太短：{current_time - self.last_enter_time}s")

    def create_cmd(self, action: list) -> dict:
        """ 创建指令 """
        cmd_params = {}
        for item in action:
            key, value = item.split(': ')
            key = self.translation_dict.get(key, key)  # 如果没有找到匹配的键，则保持原样
            cmd_params[key] = value

        import ast
        if start_pos := cmd_params.get('start_pos'):
            # 将字符串转换为元组
            cmd_params['start_pos'] = ast.literal_eval(start_pos)

        if target_pos := cmd_params.get('target_pos'):
            # 将字符串转换为元组
            cmd_params['target_pos'] = ast.literal_eval(target_pos)

        if RGB_color := cmd_params.get('RGB_color'):
            # 将字符串转换为元组
            cmd_params['RGB_color'] = ast.literal_eval(RGB_color)

        if scroll := cmd_params.get('scroll'):
            # 将字符串转换为元组
            cmd_params['scroll'] = ast.literal_eval(scroll)

        return self.solve_cmd(cmd_params)

    @staticmethod
    def solve_cmd(cmd_params: dict) -> dict:
        """ 解析操作类型 """
        action_type = cmd_params.get('action', '未知类型')
        target_pos = cmd_params.get('target_pos', None)
        RGB_color = cmd_params.get('RGB_color', None)
        if action_type == "移动":
            return {
                "action": "moveTo",
                "target_pos": target_pos,
                "RGB_color": RGB_color
            }
        elif action_type == "左键单击":
            return {
                "action": "click",
                "button": "left",
                "clicks": 1,
                "target_pos": target_pos,
                "RGB_color": RGB_color
            }
        elif action_type == "左键双击":
            return {
                "action": "click",
                "button": "left",
                "clicks": 2,
                "target_pos": target_pos,
                "RGB_color": RGB_color
            }
        elif action_type == "右键单击":
            return {
                "action": "click",
                "button": "right",
                "clicks": 1,
                "target_pos": target_pos,
                "RGB_color": RGB_color
            }
        elif action_type == "中键点击":
            return {
                "action": "click",
                "button": "middle",
                "clicks": 1,
                "target_pos": target_pos,
                "RGB_color": RGB_color
            }
        elif action_type == "拖动":
            return {
                "action": "dragTo",
                "start_pos": cmd_params.get('start_pos'),
                "target_pos": target_pos,
                "duration": float(cmd_params.get('duration').split(' s')[0]),
                "RGB_color": RGB_color
            }
        elif action_type == "滚轮":
            return {
                "action": "scrollV",
                "scroll": cmd_params.get('scroll'),
                "target_pos": target_pos,
                "RGB_color": RGB_color
            }
        else:
            return {
                "action": "未知操作",
                "target_pos": target_pos,
                "RGB_color": RGB_color
            }


class MouseRecorder(QMainWindow):
    """鼠标录制器主窗口"""
    close_signal = pyqtSignal()

    def __init__(self, cmd_treeWidget: QTreeWidget,
                 system_tray: QSystemTrayIcon,
                 parent=None):
        super().__init__(parent)
        self.cmd_treeWidget = cmd_treeWidget  # 指令编辑器
        self.system_tray = system_tray  # 系统托盘
        self.register = registry  # 指令注册管理器

        self.label_w = LABEL_WIDTH
        self.label_h = LABEL_HEIGHT
        self.screen_w = 0
        self.screen_h = 0

        self.setWindowTitle("鼠标录制器")
        self.setWindowIcon(QIcon(":/icons/mouse-record"))
        # 设置窗口无边框、窗口置顶，窗体背景透明
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 获取屏幕分辨率（长和宽）
        self.screen_w, self.screen_h = pyautogui.size()
        # 设置主窗口位置,位于屏幕左上角.大小为屏幕的宽度和高度
        self.setGeometry(0, 0, self.screen_w, self.screen_h)
        self.operation_list = []  # 存储操作记录

        # 初始化显示标签 UI
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignLeft)  # 设置标签内容居左对齐
        self.label.resize(LABEL_WIDTH, LABEL_HEIGHT)  # 设置标签大小
        self.label.setStyleSheet(LABEL_STYLE)  # 设置标签样式
        self.label.setText("按Enter记录操作\n按Esc退出录制")

        # 初始化鼠标和键盘监听线程
        self.mouse_thread = MouseListenerThread(self.label)
        self.keyboard_thread = KeyboardListenerThread(self.label)

        # 绑定信号
        self.keyboard_thread.create_cmd_signal.connect(self.add_command)
        self.keyboard_thread.stop_signal.connect(self.stop_recording)

        # 启动线程
        self.mouse_thread.start()
        self.keyboard_thread.start()

    def stop_recording(self):
        """停止录制并退出程序"""
        self.mouse_thread.stop()
        self.keyboard_thread.stop()

        if _DEBUG:
            # 打印操作记录
            for _, record in enumerate(self.operation_list, 1):
                print(f"指令[{_}]: {record}")

        # 解析操作记录并生成树控件节点
        self.parse_and_add_commands()

        self.close()

    def add_command(self, cmd_data: dict):
        """ 添加单个指令 """
        self.operation_list.append(cmd_data)
        self.label.setText("已记录一次操作\n操作类型：" + cmd_data.get('action'))
        self.system_tray.showMessage("鼠标录制器",
                                     f"已记录一次操作\n操作类型：{cmd_data.get('action')}",
                                     QSystemTrayIcon.Information,
                                     2000)

    def parse_and_add_commands(self):
        """解析操作记录并生成树控件节点"""
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
        for i, record in enumerate(self.operation_list, 1):
            self.create_tree_item(record)

    def create_tree_item(self, record):
        """创建树控件节点"""

        action = record.get('action')
        target_pos = record.get('target_pos')
        # 处理鼠标移动操作
        if action == "moveTo":
            item_name = "鼠标定点移动" + f"{str(target_pos)}"
            item_data = {
                "type": "mouse",
                "action": "moveTo",
                "icon": ":/icons/mouse-move",
                "params": {
                    "name": item_name,
                    "target_pos": target_pos,
                    "duration": 1.0,
                    "retries": 0,
                    "is_active": True,
                    "use_pynput": True,
                    "status": 0
                }
            }
            # 使用 OrderedDict 创建有序字典
            item_data = OrderedDict(item_data)
            item = QTreeWidgetItem([item_name])  # 创建节点
            item.setData(0, Qt.UserRole, item_data)  # 设置数据
            item.setIcon(0, QIcon(":/icons/mouse-move"))  # 设置图标
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
            self.register.register_command(item)  # 注册指令
            self.cmd_treeWidget.addTopLevelItem(item)
        # 处理鼠标点击操作
        elif action == "click" and record.get('button') == 'left':
            item_name = "鼠标左键点击" + f"{str(target_pos)}"
            item_data = {
                "type": "mouse",
                "action": "click",
                "icon": ":/icons/mouse-click-left",
                "params": {
                    "name": item_name,
                    "target_pos": target_pos,
                    "clicks": record.get('clicks'),
                    "interval": 0.2,
                    "duration": 1.0,
                    "retries": 0,
                    "button": "left",
                    "is_active": True,
                    "use_pynput": True,
                    "status": 0
                }
            }
            # 使用 OrderedDict 创建有序字典
            item_data = OrderedDict(item_data)
            item = QTreeWidgetItem([item_name])  # 创建节点
            item.setData(0, Qt.UserRole, item_data)  # 设置数据
            item.setIcon(0, QIcon(":/icons/mouse-click-left"))  # 设置图标
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
            self.register.register_command(item)  # 注册指令
            self.cmd_treeWidget.addTopLevelItem(item)
        elif action == "click" and record.get('button') == 'right':
            item_name = "鼠标右键点击" + f"{str(target_pos)}"
            item_data = {
                "type": "mouse",
                "action": "click",
                "icon": ":/icons/mouse-click-right",
                "params": {
                    "name": item_name,
                    "target_pos": target_pos,
                    "clicks": record.get('clicks'),
                    "interval": 0.2,
                    "duration": 1.0,
                    "retries": 0,
                    "button": "right",
                    "is_active": True,
                    "use_pynput": True,
                    "status": 0
                }
            }
            # 使用 OrderedDict 创建有序字典
            item_data = OrderedDict(item_data)
            item = QTreeWidgetItem([item_name])  # 创建节点
            item.setData(0, Qt.UserRole, item_data)  # 设置数据
            item.setIcon(0, QIcon(":/icons/mouse-click-right"))  # 设置图标
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
            self.register.register_command(item)  # 注册指令
            self.cmd_treeWidget.addTopLevelItem(item)
        elif action == "click" and record.get('button') == 'middle':
            item_name = "鼠标中键点击" + f"{str(target_pos)}"
            item_data = {
                "type": "mouse",
                "action": "click",
                "icon": ":/icons/mouse-click-middle",
                "params": {
                    "name": item_name,
                    "target_pos": target_pos,
                    "clicks": record.get('clicks'),
                    "interval": 0.2,
                    "duration": 1.0,
                    "retries": 0,
                    "button": "middle",
                    "is_active": True,
                    "use_pynput": True,
                    "status": 0
                }
            }
            # 使用 OrderedDict 创建有序字典
            item_data = OrderedDict(item_data)
            item = QTreeWidgetItem([item_name])  # 创建节点
            item.setData(0, Qt.UserRole, item_data)  # 设置数据
            item.setIcon(0, QIcon(":/icons/mouse-click-middle"))  # 设置图标
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
            self.register.register_command(item)  # 注册指令
            self.cmd_treeWidget.addTopLevelItem(item)
        # 处理鼠标滚轮操作，'scroll' 是一个元组(0,1)或(0,-1)，第一个元素是横向滚动，第二个元素是纵向滚动,正负表示方向
        elif action == "scrollV":
            # 创建 <鼠标定点移动> 指令
            target_pos = record.get('target_pos')
            item1_name = "鼠标定点移动" + f"{str(target_pos)}"
            item1_data = {
                "type": "mouse",
                "action": "moveTo",
                "icon": ":/icons/mouse-move",
                "params": {
                    "name": item1_name,
                    "target_pos": target_pos,
                    "duration": 1.0,
                    "retries": 0,
                    "is_active": True,
                    "use_pynput": True,
                    "status": 0
                }
            }
            # 使用 OrderedDict 创建有序字典
            item1_data = OrderedDict(item1_data)
            item1 = QTreeWidgetItem([item1_name])  # 创建节点
            item1.setData(0, Qt.UserRole, item1_data)  # 设置数据
            item1.setIcon(0, QIcon(":/icons/mouse-move"))  # 设置图标
            item1.setFlags(item1.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
            self.register.register_command(item1)  # 注册指令
            self.cmd_treeWidget.addTopLevelItem(item1)

            # 创建 <鼠标竖直滚动> 指令
            scroll_units = record.get('scroll')[1] * 100  # 滚动单位数默认为100
            item2_name = "鼠标竖直滚动" + f"({scroll_units})"
            item2_data = {
                "type": "mouse",
                "action": "scrollV",
                "icon": ":/icons/wheel-v",
                "params": {
                    "name": item2_name,
                    "scroll_units": scroll_units,
                    "retries": 0,
                    "is_active": True,
                    "use_pynput": True,
                    "status": 0
                }
            }
            # 使 OrderedDict 创建有序字典
            item2_data = OrderedDict(item2_data)
            item2 = QTreeWidgetItem([item2_name])  # 创建节点
            item2.setData(0, Qt.UserRole, item2_data)  # 设置数据
            item2.setIcon(0, QIcon(":/icons/wheel-v"))  # 设置图标
            item2.setFlags(item2.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
            self.register.register_command(item2)  # 注册指令
            self.cmd_treeWidget.addTopLevelItem(item2)
        # 处理鼠标拖动操作(鼠标从起点拖动到终点，所以鼠标应该先定点移动到起点，再拖动到终点)
        elif action == "dragTo":
            # 创建 <鼠标定点移动> 指令
            start_pos = record.get('start_pos')
            item1_name = "鼠标定点移动" + f"{str(start_pos)}"
            item1_data = {
                "type": "mouse",
                "action": "moveTo",
                "icon": ":/icons/mouse-move",
                "params": {
                    "name": item1_name,
                    "target_pos": start_pos,
                    "duration": 1.0,
                    "retries": 0,
                    "is_active": True,
                    "use_pynput": True,
                    "status": 0
                }
            }
            # 使用 OrderedDict 创建有序字典
            item1_data = OrderedDict(item1_data)
            item1 = QTreeWidgetItem([item1_name])  # 创建节点
            item1.setData(0, Qt.UserRole, item1_data)  # 设置数据
            item1.setIcon(0, QIcon(":/icons/mouse-move"))  # 设置图标
            item1.setFlags(item1.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
            self.register.register_command(item1)  # 注册指令
            self.cmd_treeWidget.addTopLevelItem(item1)

            # 创建 <鼠标定点拖动> 指令
            item2_name = "鼠标定点拖动" + f"{str(target_pos)}"
            item2_data = {
                "type": "mouse",
                "action": "dragTo",
                "icon": ":/icons/mouse-drag",
                "params": {
                    "name": item2_name,
                    "target_pos": target_pos,
                    "duration": record.get('duration'),
                    "retries": 0,
                    "button": "left",
                    "is_active": True,
                    "use_pynput": True,
                    "status": 0
                }
            }
            # 使用 OrderedDict 创建有序字典
            item2_data = OrderedDict(item2_data)
            item2 = QTreeWidgetItem([item2_name])  # 创建节点
            item2.setData(0, Qt.UserRole, item2_data)  # 设置数据
            item2.setIcon(0, QIcon(":/icons/mouse-drag"))  # 设置图标
            item2.setFlags(item2.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
            self.register.register_command(item2)  # 注册指令
            self.cmd_treeWidget.addTopLevelItem(item2)

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.close_signal.emit()
        super().closeEvent(event)
