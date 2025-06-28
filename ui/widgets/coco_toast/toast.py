"""
自定义弹窗通知

@Author: 54Coconi
@version: 0.0.1

"""
import os
import json
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtSignal, QEvent
from ui.widgets.coco_toast.toast_ui import Ui_notification

# 消息级别配置
TOAST_CONFIG = 'config.json'
# toast 主题
TOAST_THEMES = {
    "default": "themes/default.css",
    "cool_blue": "themes/cool_blue.css",
    "cool_purple": "themes/cool_purple.css",
}


class ToastWidget(QWidget):
    """
    自定义弹窗通知类

    Args:
        title (str): 弹窗标题
        message (str): 弹窗消息
        message_type (str): 消息级别
        duration (int): 弹窗显示时长（ms），0 表示一直显示
        parent (QWidget): 父窗口
        position (str): 弹窗位置
        theme (str): 弹窗主题
    """
    closed = pyqtSignal(object)

    _cached_configs = {}  # 缓存消息级别配置
    _cached_themes = {}  # 缓存主题

    def __init__(self, title, message, message_type="info", duration=3000, parent=None, position="top",
                 theme="default"):
        super().__init__(parent)
        self.ui = Ui_notification()
        self.ui.setupUi(self)
        self.title = title
        self.message = message
        self.message_type = message_type
        self.duration = duration
        self.remaining_time = duration  # toast 显示剩余时间
        self.parent_window = parent
        self.position = position
        self.theme = theme
        self.msg_type_config = None  # 消息级别配置
        # 设置窗口属性
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMaximumSize(300,150)

        # 设置消息级别支持富文本（用于显示图标）
        self.ui.lbl_level.setTextFormat(Qt.RichText)

        # 设置标题支持富文本
        self.ui.lbl_title.setTextFormat(Qt.RichText)
        self.ui.lbl_title.setText(self.title)

        # 设置消息支持富文本
        self.ui.lbl_message.setTextFormat(Qt.RichText)
        self.ui.lbl_message.setText(self.message)

        # 关闭按钮
        self.ui.btn_close.setStyleSheet("""border-radius: 12px;""")
        self.ui.btn_close.clicked.connect(self.close)

        self._load_config()  # 加载消息级别配置
        self._apply_theme()  # 加载主题
        self._apply_message_type()  # 加载消息级别图标和背景

        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)

        self.fade_out = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.finished.connect(self.close)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade_out)

        if parent:
            parent.installEventFilter(self)
        self.installEventFilter(self)

    def _load_config(self):

        if self.theme in ToastWidget._cached_configs:  # 如果缓存中有配置，直接从缓存中获取
            print(f"(_load_config) - 当前主题【{self.theme}】的消息类型配置已缓存，直接加载")
            self.msg_type_config = ToastWidget._cached_configs[self.theme]
            return

        cfg_path = os.path.join(os.path.dirname(__file__), TOAST_CONFIG)
        if os.path.exists(cfg_path) and os.path.isfile(cfg_path):
            with open(cfg_path, encoding="utf-8") as f:
                self.msg_type_config = json.load(f)
        else:
            self.msg_type_config = {
                "info": {"color": "#41CD52", "icon": "icons/info.svg"},
                "show_success": {"color": "#3CB371", "icon": "icons/show_success.svg"},
                "warning": {"color": "#FFA500", "icon": "icons/warning.svg"},
                "error": {"color": "#FF4500", "icon": "icons/error.svg"}
            }

        ToastWidget._cached_configs[self.theme] = self.msg_type_config

    def _apply_theme(self):
        if self.theme in ToastWidget._cached_themes:
            print(f"(_apply_theme) - 当前主题【{self.theme}】的样式已缓存，直接加载")
            self.setStyleSheet(ToastWidget._cached_themes[self.theme])
            return
        css_path = os.path.join(os.path.dirname(__file__), TOAST_THEMES.get(self.theme, ''))
        if os.path.exists(css_path) and os.path.isfile(css_path):
            with open(css_path, encoding="utf-8") as f:
                style = f.read()
                self.setStyleSheet(style)
                ToastWidget._cached_themes[self.theme] = style
        else:  # 默认样式
            print(f"(_apply_theme) - 当前主题【{self.theme}】样式不存在，使用默认样式")
            if 'default' in ToastWidget._cached_themes:
                self.setStyleSheet(ToastWidget._cached_themes['default'])

    def _apply_message_type(self):
        message_type = self.msg_type_config.get(self.message_type, {})
        msg_level_color = message_type.get("color", "#00efff")
        msg_level_icon = message_type.get("icon", ":icons/info")
        print(f"(_apply_message_type) - 消息级别{self.message_type}|背景{msg_level_color}|图标{msg_level_icon}")

        icon = f"<img src='{msg_level_icon}' width='30' height='30'>"
        bg = f"background-color: {msg_level_color};"
        self.ui.lbl_level.setText(icon)
        self.ui.lbl_level.setStyleSheet(bg)

    def showEvent(self, event):
        """ 显示事件 """
        super().showEvent(event)
        self.fade_in.start()
        self.reposition()
        if self.duration > 0:
            self.timer.start(self.duration)

    def start_fade_out(self):
        """ 开始淡出动画 """
        self.fade_out.start()

    def reposition(self):
        """ 重新定位弹窗 """
        if self.parent_window:
            parent_geom = self.parent_window.geometry()
            x = parent_geom.center().x() - self.width() // 2
            if self.position == "top":
                y = parent_geom.top() + 10
            elif self.position == "center":
                y = parent_geom.center().y() - self.height() // 2
            elif self.position == "bottom":
                y = parent_geom.bottom() - self.height() - 10
            else:
                y = parent_geom.top() + 10
            self.move(x, y)

    def eventFilter(self, obj, event):
        """ 事件过滤器 """
        # 窗口移动时重新定位
        if obj == self.parent_window and event.type() == event.Move:
            self.reposition()
        # 鼠标移入时停止计时，记录剩余时间
        elif obj == self and event.type() == QEvent.Enter:
            if self.timer.isActive():
                self.remaining_time = self.timer.remainingTime()
                self.timer.stop()
        # 鼠标移出时继续计时
        elif obj == self and event.type() == QEvent.Leave:
            if self.remaining_time > 0:
                self.timer.start(self.remaining_time)
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """ 关闭弹窗时发射closed信号 """
        self.closed.emit(self)
        super().closeEvent(event)


class ToastService:
    """ 弹窗管理服务

    Args:
        parent: 父窗口
        position: 弹窗位置
        theme: 弹窗主题
    """

    def __init__(self, parent, position="top", theme="default"):
        self.parent = parent
        self.position = position
        self.theme = theme
        self.active_toasts = []
        self.queue = []
        self.max_toasts = 3

    def show(self, message_type, title, message, duration=3000):
        """ 显示弹窗 """
        toast = ToastWidget(title, message, message_type, duration, self.parent, self.position, self.theme)
        toast.closed.connect(self._on_closed)
        if len(self.active_toasts) < self.max_toasts:
            self._show(toast)
        else:
            self.queue.append(toast)

    def _show(self, toast):
        toast.show()
        self.active_toasts.append(toast)
        self._reposition()

    def _on_closed(self, toast):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
            self._reposition()
        if self.queue:
            self._show(self.queue.pop(0))

    def _reposition(self):
        spacing = 10
        parent_geom = self.parent.geometry()
        for i, toast in enumerate(self.active_toasts):
            x = parent_geom.center().x() - toast.width() // 2
            if self.position == "top":
                base_y = parent_geom.top() + 10
                y = base_y + i * (toast.height() + spacing)
            elif self.position == "center":
                total = len(self.active_toasts)
                start_y = parent_geom.center().y() - ((toast.height() + spacing) * total // 2)
                y = start_y + i * (toast.height() + spacing)
            elif self.position == "bottom":
                base_y = parent_geom.bottom() - (toast.height() + spacing) * len(self.active_toasts)
                y = base_y + i * (toast.height() + spacing)
            else:
                y = parent_geom.top() + 10 + i * (toast.height() + spacing)
            toast.move(x, y)

    # 快捷方法
    def show_success(self, title, message, duration=3000):
        """ 显示成功弹窗 """
        self.show("success", title, message, duration)

    def show_info(self, title, message, duration=3000):
        """ 显示信息弹窗 """
        self.show("info", title, message, duration)

    def show_warning(self, title, message, duration=3000):
        """ 显示警告弹窗 """
        self.show("warning", title, message, duration)

    def show_error(self, title, message, duration=3000):
        """ 显示错误弹窗 """
        self.show("error", title, message, duration)
