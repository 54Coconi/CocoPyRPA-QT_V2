from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPlainTextEdit


class CoPlainTextEdit(QPlainTextEdit):
    """
    自定义 :class:`QPlainTextEdit` 类，继承自 :class:`QPlainTextEdit`，
    支持通过鼠标滚轮调整字体大小
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.font_size = 11  # 默认字体大小
        self.max_font_size = 24  # 最大字体大小
        self.min_font_size = 8   # 最小字体大小
        self.update_font_size()  # 初始化字体大小

    def update_font_size(self):
        """
        根据当前字体大小更新文本编辑器的字体。
        """
        font = self.font()
        font.setPointSize(self.font_size)
        self.setFont(font)

    def wheelEvent(self, event):
        """
        重写滚轮事件，用于调整字体大小。
        """
        if event.modifiers() == Qt.ControlModifier:  # 检测 Ctrl 键是否按下
            delta = event.angleDelta().y()  # 获取滚轮滚动值
            if delta > 0 and self.font_size < self.max_font_size:  # 向上滚动
                self.font_size += 1
            elif delta < 0 and self.font_size > self.min_font_size:  # 向下滚动
                self.font_size -= 1
            self.update_font_size()  # 更新字体大小
            event.accept()
        else:
            super().wheelEvent(event)  # 默认处理其他滚轮事件
