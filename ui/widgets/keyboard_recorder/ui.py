"""
键盘录制器UI模块
"""
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget

from .keyboard_record_ui import Ui_keyboard_recorder


class RecorderWidget(QWidget):
    """
    键盘录制器

    Attributes:
        closed: 关闭信号

    Args:
        stop_tip_text: 停止录制提示信息
    """
    closed = pyqtSignal()

    def __init__(self, stop_tip_text="Tab + Esc: 退出", parent=None):
        super().__init__(parent)
        self.theme = "default"
        self.ui = Ui_keyboard_recorder()
        self.ui.setupUi(self)

        # 设置无边框、置顶、无任务栏图标、透明背景
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 设置主题
        self._apply_theme()
        # 设置提示信息
        self.setToolTip("键盘录制器")
        # 设置位置
        self.move(0, 0)

        self.ui.lbl_info.setText(stop_tip_text)
        self.ui.lbl_op.setText("操作记录")

    def set_operation(self, text: str):
        """更新操作文本显示"""
        self.ui.lbl_op.setText(text)

    def closeEvent(self, event):
        """关闭事件"""
        self.closed.emit()
        super().closeEvent(event)

    def _apply_theme(self):
        css_path = os.path.join(os.path.dirname(__file__), 'themes', f'{self.theme}.css')
        if os.path.exists(css_path) and os.path.isfile(css_path):
            with open(css_path, encoding="utf-8") as f:
                style = f.read()
                self.setStyleSheet(style)
        else:  # 默认样式
            from config.app_config import warning
            warning(f"找不到主题文件：{css_path}")
            pass
