"""
@Author
加载 `mouse_record_ui.py` 并将其与 `core.MouseRecorderCore` 绑定。

该类专注界面：实时 RGB 预览、操作预览文本、操作完成弹窗，以及根据操作创建树节点

"""

from __future__ import annotations

import os
from typing import List

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox

from . import mouse_record_ui as ui_gen
from .core import MouseRecorderCore
from .tree_build_api import create_tree_item


class MouseRecorderWindow(QtWidgets.QWidget):
    """完整 UI 封装，可直接在主程序中实例化并调用"""
    closed = pyqtSignal()

    def __init__(self,
                 cmd_treeWidget: QtWidgets.QTreeWidget = None,
                 system_tray: QtWidgets.QSystemTrayIcon = None,
                 registry=None,
                 record_key: str = "enter",
                 exit_key: str = "esc"):
        super().__init__(flags=Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.ui = ui_gen.Ui_mouse_record()
        self.ui.setupUi(self)
        self.cmd_treeWidget = cmd_treeWidget
        self.system_tray = system_tray
        self.registry = registry
        self.theme = "default"

        # 背景透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 无任务栏图标
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.setWindowIcon(QIcon(":/icons/mouse-record"))
        # 移动到屏幕左上角
        self.move(0, 0)

        # 初始化核心逻辑
        self.recorder = MouseRecorderCore(record_key, exit_key)
        self.recorder.rgb_changed.connect(self.update_rgb)
        self.recorder.preview_changed.connect(self.ui.lbl_op.setText)
        self.recorder.command_created.connect(self._on_command_created)
        self.recorder.finished.connect(self.close_window)
        self.recorder.start()

        # 加载主题
        self._apply_theme()

        # lbl_info 显示快捷键
        self._update_info_label()

        # 缓存操作列表，用于最后生成树节点
        self._operations: List[dict] = []

    # -------------------------------- 信号槽 --------------------------------

    def update_rgb(self, rgb: tuple):
        """
        更新 RGB 预览
        :param rgb: (r, g, b)三元组
        """
        r, g, b = rgb
        # 标签颜色
        self.ui.lbl_rgbshow.setStyleSheet(f"background-color: rgb({r},{g},{b});")
        # 文本
        self.ui.lbl_rgbtext.setText(f"RGB:({r}, {g}, {b})")

    def _on_command_created(self, cmd: dict):
        # 仅在用户按 Enter 时 recorder.operations 已追加
        self._operations = self.recorder.get_operations()
        print("[INFO] - 记录指令：", cmd)
        # print("记录的操作列表：", self._operations)
        # 系统托盘提示
        if self.system_tray:
            self.system_tray.showMessage("鼠标录制器",
                                         f"已记录一次操作\n操作类型：{cmd.get('action')}",
                                         QtWidgets.QSystemTrayIcon.Information, 2000)

    # ------------------------------------------------------------------------
    # 退出 / 生成树控件节点
    # ------------------------------------------------------------------------

    def close_window(self):
        """关闭鼠标录制器标签窗口"""
        if self._operations and self.cmd_treeWidget:
            self._build_tree_items()
        self.close()

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.recorder.mouse_thread.isRunning():
            print("(closeEvent) - 鼠标监听线程还在运行中")
            self.recorder.mouse_thread.quit()
        if self.recorder.mouse_thread.listener.is_alive():
            print("(closeEvent) - 鼠标监听器还在运行中")
            self.recorder.mouse_thread.listener.stop()
        if self.recorder.keyboard_thread.isRunning():
            print("(closeEvent) - 键盘监听线程还在运行中")
        print("(closeEvent) - 关闭鼠标录制器标签窗口")

        self.closed.emit()
        super().closeEvent(event)

    def _build_tree_items(self):
        # 如操作列表为空不创建指令
        if not self._operations:
            return
        # 如果当前指令编辑器内容不为空则提示覆盖/追加
        if self.cmd_treeWidget.topLevelItemCount() > 0:
            msg = QMessageBox(self.cmd_treeWidget)
            btn_cover = msg.addButton("覆盖", QMessageBox.YesRole)
            btn_add = msg.addButton("追加", QMessageBox.NoRole)
            btn_cancel = msg.addButton("取消", QMessageBox.RejectRole)
            msg.setWindowTitle("提示")
            msg.setText("当前指令编辑器不为空，是否覆盖或追加?\n"
                        "【覆盖】：覆盖当前指令编辑器内容\n"
                        "【追加】：追加到当前指令编辑器内容后面")
            msg.setDefaultButton(btn_cover)
            msg.exec_()
            if msg.clickedButton() == btn_cover:
                self.cmd_treeWidget.clear()
            elif msg.clickedButton() == btn_cancel:
                return
        # 解析并创建
        for op in self._operations:
            self._create_tree_item(op)

    def _create_tree_item(self, record: dict):
        create_tree_item(self.cmd_treeWidget, record)

    # -------------------------------- util ----------------------------------

    def _update_info_label(self):
        record_key = self.recorder.record_key.title()
        exit_key = self.recorder.exit_key.title()
        self.ui.lbl_info.setText(f"{record_key}: 记录当前操作\n{exit_key}: 退出录制")

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
