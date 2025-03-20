""" HTML页面显示类 """

from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QDialog, QDesktopWidget, QVBoxLayout, QTextBrowser
from screeninfo import screeninfo


class CocoDialog(QDialog):
    """ HTML页面显示类 """
    def __init__(self, title, html_path, parent=None):
        super().__init__(parent)
        self.title = title
        self.html_path = html_path
        self.parent = parent
        # 设置窗口标题
        self.setWindowTitle(self.title)
        self.setGeometry(0, 0, 650, 700)

        # 获取屏幕的大小和位置用于居中显示
        monitor = screeninfo.get_monitors()[0]
        x = (monitor.width - self.width()) // 2
        y = (monitor.height - self.height()) // 2
        self.move(x, y)

        layout = QVBoxLayout()
        # 移除内容区域边距
        layout.setContentsMargins(0, 0, 0, 0)

        # 设置窗口图标
        # self.setWindowIcon(QIcon(":icons/logo"))

        text_browser = QTextBrowser(self.parent)
        text_browser.setOpenExternalLinks(True)
        baseURL = QUrl.fromLocalFile(html_path)
        text_browser.setSource(baseURL)
        # text_browser.setHtml(open(self.html_path, 'r', encoding='utf-8').read())
        layout.addWidget(text_browser)
        self.setLayout(layout)
