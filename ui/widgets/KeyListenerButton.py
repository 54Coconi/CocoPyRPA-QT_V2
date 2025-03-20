"""
自定义按键控件
用于检测用户按下的按键，并将按键信息传递给父窗口

Path: ui/widgets/KeyListenerButton.py
"""
import re

from PyQt5.QtWidgets import QPushButton, QInputDialog, QMessageBox
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QKeySequence

_DEBUG = True


class KeyCaptureButton(QPushButton):
    """
    自定义按键捕获按钮

    Attributes:
        key_changed: (pyqtSignal): 按键变化信号
    """
    # 定义按键变化信号，传递按键描述字符串
    key_changed = pyqtSignal(str)

    def __init__(self, parent=None, mode="single"):
        super(KeyCaptureButton, self).__init__(parent)
        self.parent = parent
        self.mode = mode  # 模式选择：'single'（单键）或 'shortcut'（快捷键）
        self.setFocusPolicy(Qt.StrongFocus)
        self._last_key = ""  # 保存最后的按键字符串
        self.display_string = ""  # 用于显示的字符串
        self._listening = False  # 控制监听状态
        self._shortcut_keys = []  # 存储快捷键按键序列

    def focusInEvent(self, event):
        """当按钮获取焦点时开始监听"""
        # print(f"(focusInEvent) 获取焦点 {event}")
        super(KeyCaptureButton, self).focusInEvent(event)
        self.setText("Listening...")
        self._listening = True
        if self.mode == "shortcut":
            self._shortcut_keys.clear()  # 进入快捷键模式时清空已有按键序列

    def keyPressEvent(self, event):
        """捕获键盘按下事件"""
        if self._listening:
            super(KeyCaptureButton, self).keyPressEvent(event)

            if event.key() == Qt.Key_Tab:  # 如果按下的是 Tab 键
                event.accept()  # 阻止 Tab 键的焦点切换
                self._handle_key(Qt.Key_Tab)
                return

            # 优先处理特殊键
            key_string = self._get_special_key_string(event.key())
            print(f"(KeyPressEvent) 映射后的键 = {key_string}") if _DEBUG else None
            if not key_string:  # 如果不是特殊键，则尝试使用文本
                key_string = event.text()
                print(f"(KeyPressEvent) event.text = {key_string}") if _DEBUG else None
                if not key_string or key_string.isspace():  # 空字符或空格字符
                    key_string = None

            if not key_string:  # 最终无法解析时，使用未知键格式
                key_string = QKeySequence(event.key()).toString()
                print(f"(KeyPressEvent) QKeySequence = {key_string}") if _DEBUG else None
            # 处理特殊符号 &,将 & 替换为 &&,以避免 & 被误认为快捷键的分隔符
            self.display_string = key_string.replace("&", "&&") if key_string else ""

            if self.mode == "single":
                # 单键模式：直接更新
                self._last_key = key_string
                self.setText(self.display_string)
            elif self.mode == "shortcut":
                # 快捷键模式：记录按键序列
                if len(self._shortcut_keys) < 4:  # 最多记录 4 个按键
                    self._shortcut_keys.append(key_string)
                # 将快捷键序列连接成字符串显示
                self._last_key = " + ".join(self._shortcut_keys)
                self.display_string = self._last_key.replace("&", "&&")
                self.setText(self.display_string)

    def focusOutEvent(self, event):
        """当按钮失去焦点时停止监听"""
        super(KeyCaptureButton, self).focusOutEvent(event)
        self._listening = False  # 停止监听
        if self.mode == "single":
            self.setText(self.display_string or "按下单个按键")
        else:
            self.setText(self.display_string or "分别按下多个按键")
        self.key_changed.emit(self._last_key)  # 发出信号

    def leaveEvent(self, event):
        """当鼠标移开时，清除按钮焦点"""
        super(KeyCaptureButton, self).leaveEvent(event)
        self.clearFocus()  # 主动清除焦点，停止捕获按键

    def mousePressEvent(self, event):
        """ 捕获右键事件，并弹出输入框 """
        if event.button() == Qt.RightButton:
            # 弹出输入框, 获取用户输入的按键
            text, ok = QInputDialog.getText(self, "输入按键", "请输入按键\n"
                                            "对于多个按键，用‘+’分隔")
            if ok and text:
                text = self._sanitize_input(text)
                if self.mode == "single" and len(text) > 1 and "+" in text:
                    QMessageBox.warning(self, "错误", "单键模式不支持多个按键。")
                    return
                if text:
                    # 如果用户输入的文本有效，则更新按钮显示
                    self.display_string = text
                    self.setText(self.display_string)
                    self._last_key = self.display_string
                    self.key_changed.emit(self._last_key)
                else:
                    # 如果输入不规范, 弹出错误提示
                    QMessageBox.warning(self, "错误", "无效的按键输入。")

    def _handle_key(self, key):
        """处理特殊键"""
        print(f"(_handle_key) key: {key}") if _DEBUG else None
        if key == Qt.Key_Tab:
            self.display_string = "tab"
            self.setText(self.display_string)
            self._last_key = self.display_string

    def _sanitize_input(self, text):
        """过滤不规范的输入"""
        # 只允许字母、数字、空格、加号、减号等符号
        # 可以根据需求添加其他规范
        sanitized_text = re.sub(r'[^a-zA-Z0-9\s+\-]', '', text)
        return sanitized_text.strip()

    @staticmethod
    def _get_special_key_string(key):
        """映射 PyQt 按键到 pyautogui/pynput 通用按键"""
        print(f"(_get_special_key_string) key: {key}") if _DEBUG else None
        key_map = {
            Qt.Key_Escape: "esc",
            Qt.Key_Tab: "tab",
            Qt.Key_Backspace: "backspace",
            Qt.Key_Return: "enter",
            Qt.Key_Enter: "enter",
            Qt.Key_Insert: "insert",
            Qt.Key_Delete: "delete",
            Qt.Key_Pause: "pause",
            Qt.Key_Print: "print_screen",
            Qt.Key_Home: "home",
            Qt.Key_End: "end",
            Qt.Key_Left: "left",
            Qt.Key_Up: "up",
            Qt.Key_Right: "right",
            Qt.Key_Down: "down",
            Qt.Key_PageUp: "page_up",
            Qt.Key_PageDown: "page_down",
            Qt.Key_Space: "space",
            Qt.Key_Shift: "shift",
            Qt.Key_Control: "ctrl",
            Qt.Key_Alt: "alt",
            Qt.Key_Meta: "win",  # Meta 键一般对应 Win 键
            Qt.Key_F1: "f1",
            Qt.Key_F2: "f2",
            Qt.Key_F3: "f3",
            Qt.Key_F4: "f4",
            Qt.Key_F5: "f5",
            Qt.Key_F6: "f6",
            Qt.Key_F7: "f7",
            Qt.Key_F8: "f8",
            Qt.Key_F9: "f9",
            Qt.Key_F10: "f10",
            Qt.Key_F11: "f11",
            Qt.Key_F12: "f12",
            # 添加更多特殊键的映射
        }
        return key_map.get(key, None)
