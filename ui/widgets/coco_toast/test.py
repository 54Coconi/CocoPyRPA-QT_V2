"""
MainWindow 示例窗口用于测试自定义 Toast 通知组件
"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from toast import ToastService


class MainWindow(QWidget):
    """
    示例主窗口，展示 ToastManager 的使用方式。
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Toast 通知测试")
        self.resize(800, 800)

        # 初始化 Toast 管理器，支持主题配置和底部显示位置
        self.current_theme = "default"  # 可扩展为从设置读取
        self.toast_manager = ToastService(self, position="top", theme=self.current_theme)

        layout = QVBoxLayout(self)

        # 主题切换按钮
        self.theme_options = ["default", "cool_blue", "cool_purple", "light"]  # 这里故意添加一个不存在的light主题
        self.theme_index = 0
        switch_btn = QPushButton("切换主题")
        switch_btn.clicked.connect(self.switch_theme)
        layout.addWidget(switch_btn)

        # 注册按钮用于测试不同类型的通知
        for level in ["info", "success", "warning", "error"]:
            btn = QPushButton(f"显示 {level} 通知")
            btn.clicked.connect(lambda _, l=level: self.toast_manager.show(l,
                f"<b>{l.upper()} 通知</b>",
                f"这是 <i>{l}</i> 类型的消息内容。", 4000))
            layout.addWidget(btn)

        # 异步触发（模拟后台线程中调用 UI 提示）
        async_btn = QPushButton("模拟异步触发通知")
        async_btn.clicked.connect(self.trigger_async_toast)
        layout.addWidget(async_btn)

    def switch_theme(self):
        self.theme_index = (self.theme_index + 1) % len(self.theme_options)
        self.current_theme = self.theme_options[self.theme_index]
        print(f"切换主题：{self.current_theme}")
        self.toast_manager.theme = self.current_theme

    def trigger_async_toast(self):
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self.toast_manager.show_success(
            "异步通知", "已有脚本 '{active_script}' 正在执行中，且未勾选【排队执行】", 5000))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
