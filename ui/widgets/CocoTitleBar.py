"""
自定义标题栏
"""

import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QApplication

import resources_rc

# 全局常量
TITLE_BAR_HEIGHT = 35  # 标题栏高度
TITLE_BUTTON_SIZE = 35  # 标题栏按钮尺寸
TITLE_LABEL_SIZE = 35  # 标题栏标签尺寸
TITLE_BUTTON_WIDTH = 35  # 标题栏按钮宽度
TITLE_BUTTON_HEIGHT = 35  # 标题栏按钮高度
TITLE_ICON_MAG = 10  # 标题栏图标缩放

TITLE_MIN_ICON = ':/icons/titlebar-min'
TITLE_MAX_ICON = ':/icons/titlebar-max'
TITLE_RESTORE_ICON = ':/icons/titlebar-restore'
TITLE_CLS_ICON = ':/icons/titlebar-close-white'

TITLE_BUTTON_COLOR = "rgb(42,41,43)"
TITLE_BUTTON_HOVER_COLOR = "rgb(58,58,58)"


def set_button_color(color: str = TITLE_BUTTON_COLOR):
    """设置按钮背景颜色"""
    global TITLE_BUTTON_COLOR
    TITLE_BUTTON_COLOR = color


def set_button_hover_color(color: str = TITLE_BUTTON_HOVER_COLOR):
    """设置按钮 hover 颜色"""
    global TITLE_BUTTON_HOVER_COLOR
    TITLE_BUTTON_HOVER_COLOR = color


def set_button_style():
    """设置按钮样式"""
    return f"""
    QPushButton {{
        border: none;
        background-color: {TITLE_BUTTON_COLOR};
    }}
    QPushButton:hover {{
        background-color: {TITLE_BUTTON_HOVER_COLOR};
    }}
    """


class TitleBar(QWidget):
    """
    自定义标题栏
    """

    def __init__(self, parent):
        super(TitleBar, self).__init__()
        self.win = parent
        self.isPressed = False  # 标题栏是否被按下
        self.setFixedHeight(TITLE_BAR_HEIGHT)  # 设置标题栏高度

        self.init_views()

    def init_views(self):
        """ 初始化控件 """
        self.iconLabel = QLabel(self)  # 标题栏图标
        self.titleLabel = QLabel(self)  # 标题栏标题

        self.minButton = QPushButton(self)  # 最小化按钮
        self.restoreButton = QPushButton(self)  # 还原按钮
        self.closeButton = QPushButton(self)  # 关闭按钮

        self.minButton.setFixedSize(TITLE_BUTTON_SIZE, TITLE_BUTTON_SIZE)
        self.restoreButton.setFixedSize(TITLE_BUTTON_SIZE, TITLE_BUTTON_SIZE)
        self.closeButton.setFixedSize(TITLE_BUTTON_SIZE, TITLE_BUTTON_SIZE)

        self.iconLabel.setFixedSize(TITLE_LABEL_SIZE, TITLE_LABEL_SIZE)
        self.titleLabel.setFixedHeight(TITLE_LABEL_SIZE)

        self.iconLabel.setAlignment(Qt.AlignCenter)
        self.titleLabel.setAlignment(Qt.AlignCenter)

        self.minButton.setIcon(QIcon(TITLE_MIN_ICON))
        self.minButton.setStyleSheet(set_button_style())
        self.restoreButton.setIcon(QIcon(TITLE_MAX_ICON))
        self.restoreButton.setStyleSheet(set_button_style())
        self.closeButton.setIcon(QIcon(TITLE_CLS_ICON))
        self.closeButton.setStyleSheet(f"""
        QPushButton {{
            border: none;
            background-color: {TITLE_BUTTON_COLOR};
        }}
        QPushButton:hover {{
            background-color: rgb(232,17,35);
        }}""")
        # 设置信号与槽
        self.minButton.clicked.connect(self.ShowMinimizedWindow)
        self.restoreButton.clicked.connect(self.ShowRestoreWindow)
        self.closeButton.clicked.connect(self.CloseWindow)

        self.lay = QHBoxLayout(self)
        self.setLayout(self.lay)

        self.lay.setSpacing(0)
        self.lay.setContentsMargins(0, 0, 0, 0)

        self.lay.addWidget(self.iconLabel)
        self.lay.addWidget(self.titleLabel)
        self.lay.addWidget(self.minButton)
        self.lay.addWidget(self.restoreButton)
        self.lay.addWidget(self.closeButton)

    def ShowMinimizedWindow(self):
        """ 最小化窗口 """
        self.win.showMinimized()

    def ShowMaximizedWindow(self):
        """ 最大化窗口 """
        self.win.showMaximized()

    def ShowRestoreWindow(self):
        """ 还原窗口 """
        if self.win.isMaximized():
            self.win.showNormal()
            self.restoreButton.setIcon(QIcon(TITLE_MAX_ICON))
        else:
            self.win.showMaximized()
            self.restoreButton.setIcon(QIcon(TITLE_RESTORE_ICON))

    def CloseWindow(self):
        """ 关闭窗口 """
        self.win.close()

    def SetTitle(self, string: str):
        """ 设置标题 """
        self.titleLabel.setText(string)

    def SetIcon(self, pix: QPixmap):
        """ 设置标题栏图标 """
        self.iconLabel.setPixmap(pix.scaled(self.iconLabel.size() - QSize(TITLE_ICON_MAG, TITLE_ICON_MAG)))

    def mouseDoubleClickEvent(self, event):
        """ 双击标题栏最大化窗口 """
        self.ShowRestoreWindow()
        return QWidget().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        """ 按下标题栏 """
        self.isPressed = True
        self.startPos = event.globalPos()
        return QWidget().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """ 松开标题栏 """
        self.isPressed = False
        return QWidget().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """ 移动标题栏 """
        if self.isPressed:
            if self.win.isMaximized:
                self.win.showNormal()

            movePos = event.globalPos() - self.startPos
            self.startPos = event.globalPos()
            self.win.move(self.win.pos() + movePos)

        return QWidget().mouseMoveEvent(event)


# 测试
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     win = TitleBar(None)
#     win.show()
#     sys.exit(app.exec_())
