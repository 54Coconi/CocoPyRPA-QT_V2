"""
@author: 54Coconi
@data: 2024-11-18
@version: 2.0.2
@path: ui/main_window.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    CocoPyRPA_v2 全新版本，完全重写

    该模块是 CocoPyRPA-QT 应用程序的主窗口实现，模块主要承担了应用程序的核心界面布局、任务管理、事件绑定和系统集成等职责。
    模块初始化时加载配置文件并根据配置设置全局样式主题，支持深色、浅色、默认和护眼四种主题风格切换，并通过信号机制与配置管理器联动实时更新 UI 样式。
    它还负责创建和初始化多个核心组件，如任务编辑器、指令库、属性表格、截图工具、OCR 模型加载器等。

    模块包括但不限于以下用户操作功能：
        - 支持新建、打开、保存任务文件（JSON 格式），具备撤销/重做机制，可对任务树结构进行回退或恢复。
        - 提供右键菜单支持的任务目录管理功能，包括新建、重命名、复制、粘贴、删除等操作。
        - 任务编辑采用拖拽方式，支持多种类型的指令节点（鼠标操作、键盘操作、图片识别、脚本执行、流程控制等），并通过属性表格动态展示和修改节点参数。
        - 内置 OCR 引擎（PaddleOCR）、图像识别、屏幕截图、鼠标及键盘录制工具，增强了自动化任务的构建能力。
        - 支持运行当前选中节点、从指定节点开始运行、运行全部指令等多种运行模式，并提供日志输出和节点高亮功能，便于调试。
        - 实现了系统托盘图标与菜单，允许最小化运行并提供快捷入口用于触发录制操作。
        - 提供条件逻辑构建器，方便用户为 if 判断节点编写复杂的判断表达式。
        - 集成版本检查功能，能够自动连接 GitHub 获取最新发布版本号，并提示用户是否前往下载页面升级。
        - 允许执行自定义 Python 脚本，拓展了 RPA 的灵活性和功能性。

    此外，模块中使用了多线程技术来处理耗时操作，例如 OCR 模型加载、GitHub 版本检测等，保证了主界面的流畅响应。同时，模块内实现了良好的异常处理机制和用户交互设计，提升了整体的稳定性和用户体验。
"""

import sys
import json
import os.path

import keyboard
import requests
import qdarkstyle
import webbrowser

from typing import Optional
from datetime import datetime

from PyQt5 import QtGui
from PyQt5.QtCore import QDir, QModelIndex, Qt, QLocale, pyqtSignal, QThread, QPoint
from PyQt5.QtGui import QIcon, QStandardItemModel, QFont, QWheelEvent
from PyQt5.QtWidgets import QMainWindow, QFileSystemModel, QMessageBox, QTreeWidgetItem, \
    QInputDialog, QLineEdit, QMenu, QFileDialog, QTreeWidgetItemIterator, QDialog, QVBoxLayout, QHBoxLayout, \
    QPushButton, QTableWidgetItem, QSystemTrayIcon, QApplication, QAction

from .CocoPyRPA_v2_ui import Ui_MainWindow
from .task_editor_controller import TaskEditorCore

from .widgets.BindPropertyDialog import BindPropertyDialog
from .widgets.CocoHtmlDialog import CocoDialog
from .widgets.CocoJsonView import JSONHighlighter
from .widgets.CocoPlainTextEdit import CoPlainTextEdit
from .widgets.CocoCmdLibWidget import CmdLibAndSearchBar
from .widgets.CocoIndicator import CustomTreeIndicatorStyle
from .widgets.CocoSettingWidget import SettingsWindow as SettingDialog, config_manager
from .widgets.IfCmdConditionBuilder import ConditionBuilder
from .widgets.CodeEditor import CodeEditor
from .widgets.MouseRecord import MouseRecorder
from .widgets.KeyboardRecord import KeyboardRecorder

from utils.ocr_tools import OCRTool
from utils.debug import print_func_time
from utils.check_input import validate_input
from utils.screen_capture import CaptureScreen
from utils.QSSLoader import QSSLoader as QL
from utils.stop_executor import stop_running_thread

from core.script_executor import executor
from core.cmd_executor import CommandExecutor
from core.auto_executor_manager import AutoExecutorManager

_DEBUG = True

# 控制台LOGO
LOGO1 = "      ______                 ____       ____   ____  ___                        "
LOGO2 = "     / ____/___  _________  / __ \__ __/ __ \ / __ \/   |       _      __ ___   "
LOGO3 = "    / /   / __ \/ ___/ __ \/ /_/ / / / / /_/ / /_/ / /| |      | |    / / ___ \\"
LOGO4 = "   / /___/ /_/ / /__/ /_/ / ____/ /_/ / _, _/ ____/ ___ |      | |   / / ___/ / "
LOGO5 = "   \____/\____/\___/\____/_/    \__, /_/ |_/_/   /_/  |_|      | |  / / / ___/  "
LOGO6 = "                               /____/                          | ___ / /_____/  "

# 版本信息
__version__ = '2.0.2'
__author__ = '54Coconi'
__copyright__ = 'Copyright 2024-present 54Coconi'
__license__ = 'MIT'
__status__ = 'Development'

# 配置文件（用于设置功能）
CONFIG_FILE = 'config.ini'
# 指令库配置（用于加载预设的指令）
CMD_LIB_JSON_FILE = 'config/CocoCmdLib.json'
# 工作空间根目录
WORK_SPACE = './work'
TASK_HOME = WORK_SPACE + '/work_tasks'
# HTML文件
cmd_desc_path = 'ui/static/feature.html'
about_path = 'ui/static/about.html'

# OCR 模型
DET_MODEL_DIR = './models/det/ch/ch_PP-OCRv4_det_infer'
REC_MODEL_DIR = './models/rec/ch/ch_PP-OCRv4_rec_infer'
CLS_MODEL_DIR = './models/cls/ch/ch_PP-OCRv4_cls_infer'

# 全局配置（用于保存config.ini文件配置）
GLOBAL_CONFIG = {}


def update_global_config(self, new_config):
    """更新全局配置变量"""
    global GLOBAL_CONFIG
    GLOBAL_CONFIG.clear()
    GLOBAL_CONFIG.update(new_config)

    theme = new_config.get("General", {}).get("Theme", "默认")
    # is_top_hint = new_config.get("General", {}).get("Window", {}).get("StaysOnTopHint", False)
    # print(f"主题: {theme}, 窗口置顶: {is_top_hint}")
    # if is_top_hint:
    #     self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    if theme == "深色":
        self.setStyleSheet(QL.read_qss_file('resources/theme/dark/main.css'))
    elif theme == "浅色":
        self.setStyleSheet(QL.read_qss_file('resources/theme/light/main.css'))
    elif theme == "护眼":
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    else:
        self.setStyleSheet(QL.read_qss_file('resources/theme/default/main.css'))


class CocoPyRPA_v2(QMainWindow, Ui_MainWindow):
    """
    继承自 :class:`QMainWindow` 和 :class:`Ui_MainWindow`
    主窗口类，负责整个程序的主要逻辑

    Attributes:
        current_version (str): 当前版本号
    """
    current_version = __version__

    def __init__(self, parent=None):
        super(CocoPyRPA_v2, self).__init__(parent)
        self.setupUi(self)
        self.retranslateUi(self)  # 设置界面的国际化

        # --------------- 在 self.setupUi(self) 之后使用父类属性 ---------------
        # 加载配置管理器
        self.config_manager = config_manager
        GLOBAL_CONFIG.update(self.config_manager.config)  # 读取配置文件,初始化全局配置变量
        print(f"[INFO] - (CocoPyRPA_v2) - 当前配置为：{GLOBAL_CONFIG}") if _DEBUG else None
        self.config_manager.config_changed.connect(
            lambda new_config: update_global_config(self, new_config))  # 连接配置改变信号

        # 监听 "Q+Esc" 组合键
        self.stop_running_thread = stop_running_thread
        self.stop_running_thread.stopSignal.connect(self.stop_executor_thread)  # 停止指令前台执行线程
        self.stop_running_thread.start()  # 启动线程

        # 加载 ocr 模型(PaddleOCR)
        self._ocr = None
        self._load_ocr = LoadOcrModel(model=GLOBAL_CONFIG["ImageOcr"]["ModelName"], parent=self)
        self._load_ocr.ocr_model_signal.connect(self.set_ocr_model)
        self._load_ocr.finished.connect(self._print_console_logo)
        self._load_ocr.start()  # 启动线程

        self._task_home = TASK_HOME  # 任务根目录
        self._clipboard_path = ''  # 剪贴板路径
        self.cmd_treeWidget.clear()  # 清空指令树

        # 检查 github 上的最新版本
        self.get_github_version = GetVersionThread(self)
        self.get_github_version.version_signal.connect(self.show_update_message)

        # 设置自定义的功能介绍、关于对话框
        self.cmd_introduction_dialog = CocoDialog("指令介绍", cmd_desc_path, parent=self)  # 指令介绍页面
        self.about_dialog = CocoDialog("关于", about_path, parent=self)  # 关于页面

        # 设置自定义的 QFileSystemModel
        self.file_model = FileSystemModel()  # 使用自定义的文件系统模型
        self.file_model.setRootPath(self._task_home)  # 设置根路径

        # 设置自定义的任务加载、编辑、属性编辑组件
        self.task_editor_ctrl = TaskEditorCore(self.cmd_treeWidget,
                                               self.attr_edit_tableWidget,
                                               self.tasks_view_treeView,
                                               self.op_view_treeWidget)
        # 连接任务组件发送的信号
        self.task_editor_ctrl.screenshot_signal.connect(self.screen_shot)  # 截图信号
        self.task_editor_ctrl.node_inserted_signal.connect(self.on_tree_row_inserted)  # 节点插入信号
        self.task_editor_ctrl.node_removed_signal.connect(self.on_tree_row_removed)  # 节点删除信号

        # 设置自定义的指令库组件
        self.coco_op_view = CmdLibAndSearchBar(self.op_search_line, self.op_view_treeWidget,
                                               json_path=CMD_LIB_JSON_FILE)

        # 设置自定义的截图窗口
        self.screenshot = CaptureScreen(parent=self)  # 截图类实例
        self.screenshot.setWindowModality(Qt.ApplicationModal)  # 设置截图窗口为模态
        self.screenshot.screen_shot_finish_signal.connect(self.get_template_img)  # 截图结束
        self.screenshot.screen_window_close_signal.connect(self.screenshot_window_close)  # 截图窗口关闭

        # 设置日志文本框的上下文菜单
        self.log_textEdit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log_textEdit.customContextMenuRequested.connect(self.show_log_context_menu)

        self.cmd_list = []  # 指令列表
        self.is_running = False  # 是否正在运行

        # executor.log_message.connect(lambda msg: print("【日志】：", msg, sep=''))
        executor.log_message.connect(self.log_textEdit.append)
        executor.progress_updated.connect(self.on_progress_updated)

        # 指令执行器
        self.executor_thread = None
        # 脚本自动执行管理器
        self.auto_executor_manager = AutoExecutorManager(parent=self)
        self.auto_executor_manager.script_executor_trigger.connect(self.start_script_executor)
        # If 判断条件 ”condition“ 的构建器
        self.condition_builder = None
        # Python 编辑器
        self.python_editor = None
        # 鼠标录制器
        self.mouse_recorder = None
        # 键盘录制器
        self.key_recorder = None

        # ---------------- 在 init_ui() 之前定义一些变量 ----------------
        self.init_ui()

    def init_ui(self):
        """ 初始化主窗口 """
        # 设置主窗口
        self.resize(1200, 800)
        self.setWindowTitle(f"CocoPyRPA-QT v{self.current_version}")  # 设置主窗口标题
        self.setWindowIcon(QIcon(":/icons/logo"))  # 设置主窗口图标

        self.setDefaultStyle()  # 设置默认样式

        # -------------- 属性编辑器、指令操作库停靠界面的设置 --------------
        self.action_menu_attrEditor.setChecked(True)  # 默认勾选,显示属性编辑器窗口
        self.action_menu_cmdLib.setChecked(True)  # 默认勾选,显示指令库窗口
        self.attr_edit_dockWidget.setMinimumWidth(330)  # 设置属性编辑器窗口最小宽度
        # 监听 DockWidget 的可见性变化
        self.attr_edit_dockWidget.visibilityChanged.connect(self.sync_menu_with_attr_edit_dock)
        self.op_view_dockWidget.visibilityChanged.connect(self.sync_menu_with_op_view_dock)

        # ----------------------- 主窗口分割器设置 -----------------------
        self.main_splitter.setStretchFactor(0, 2)  # 任务视图占比为 2
        self.main_splitter.setStretchFactor(1, 5)  # 指令编辑器占比为 5
        # ----------------- 指令编辑器和日志窗口分割器设置 -----------------
        self.cmd_and_log_splitter.setStretchFactor(0, 2)  # 指令编辑器占比
        self.cmd_and_log_splitter.setStretchFactor(1, 1)  # 日志窗口占比

        # ----------------------- 任务目录视图设置 -----------------------
        # 过滤器，仅显示文件夹和 .json 文件
        self.file_model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        self.file_model.setNameFilters(["*.json"])
        self.file_model.setNameFilterDisables(False)

        # 将 QFileSystemModel 绑定到 QTreeView
        self.tasks_view_treeView.setModel(self.file_model)  # 设置 QTreeView 的模型
        self.set_task_view_header()  # 设置 QTreeView 的表头
        self.tasks_view_treeView.setRootIndex(self.file_model.index(self._task_home))  # 设置 QTreeView 的根目录
        self.tasks_view_treeView.setIndentation(15)  # 设置缩进
        self.tasks_view_treeView.setSortingEnabled(False)  # 设置是否能够排序
        # TODO:设置任务视图默认展开，这里不知为何会失效？
        # self.tasks_view_treeView.expandAll()

        # ============================ 绑定菜单项的触发事件 ============================

        # 菜单项 - 文件
        self.action_menu_newTaskDir.triggered.connect(self.new_task_dir)  # 新建任务文件夹
        self.action_menu_newTaskFile.triggered.connect(  # 新建任务文件
            lambda: self.new_task_file(self.file_model.filePath(self.tasks_view_treeView.currentIndex())))
        self.action_menu_openTask.triggered.connect(self.open_task)  # 打开任务
        self.action_menu_saveTask.triggered.connect(self.save_task)  # 保存任务
        self.action_menu_setting.triggered.connect(self.setting)  # 设置
        # 菜单项 - 编辑
        self.action_menu_undo.triggered.connect(self.undo)  # 撤销
        self.action_menu_redo.triggered.connect(self.redo)  # 重做
        self.action_menu_clear.triggered.connect(self.clear)  # 清空
        # 菜单项 - 视图
        self.action_menu_attrEditor.triggered.connect(self.is_attr_editor)  # 是否显示属性编辑器
        self.action_menu_cmdLib.triggered.connect(self.is_cmd_lib)  # 是否显示指令库
        self.action_menu_attrBind.triggered.connect(self.open_attr_bind_dialog)  # 打开属性绑定
        self.action_menu_attrBind.setVisible(False)  # TODO: 暂时隐藏属性绑定，后续开发
        # 菜单项 - 运行
        self.action_menu_runAll.triggered.connect(self.run_all)  # 运行全部指令
        self.action_menu_runOne.triggered.connect(self.run_one)  # 运行当前选中指令
        self.action_menu_runNow.triggered.connect(self.run_now)  # 从当前选中的指令开始往后运行
        self.action_menu_runAuto.triggered.connect(self.run_auto)  # 自动运行
        # 菜单项 - 工具
        self.action_menu_screenShot.triggered.connect(self.screen_shot)  # 截图
        self.action_menu_mouseRecord.triggered.connect(self.mouse_record)  # 鼠标录制
        self.action_menu_keysRecord.triggered.connect(self.keys_record)  # 键盘录制
        self.action_menu_python.triggered.connect(self.exec_python)  # 执行 python
        # 菜单项 - 主题
        self.action_menu_defaultTheme.triggered.connect(self.is_default_theme)  # 默认主题
        self.action_menu_darkTheme.triggered.connect(self.is_dark_theme)  # 深色主题
        self.action_menu_lightTheme.triggered.connect(self.is_light_theme)  # 浅色主题
        self.action_menu_protectEyesTheme.triggered.connect(self.is_protect_eyes_theme)  # 护眼主题
        # 菜单项 - 帮助
        self.action_menu_cmdDesc.triggered.connect(self.show_cmd_desc)  # 显示指令描述界面
        self.action_menu_about.triggered.connect(self.show_about)  # 显示关于界面
        self.action_menu_checkUpdate.triggered.connect(self.check_update)  # 检查更新

        # =============================== 绑定点击信号  ===============================
        # 双击任务列表，展开任务目录或打开任务文件
        self.tasks_view_treeView.doubleClicked.connect(self.on_tasks_item_doubleClicked)
        # 任务列表右键菜单设置
        self.tasks_view_treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tasks_view_treeView.customContextMenuRequested.connect(self.on_tasks_context_menu)

        # 属性编辑器右键菜单设置
        self.attr_edit_tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.attr_edit_tableWidget.customContextMenuRequested.connect(self.on_attr_edit_context_menu)

        # 设置系统托盘
        self.setup_system_tray()

    @staticmethod
    def _print_console_logo():
        print(LOGO1, LOGO2, LOGO3, LOGO4, LOGO5, LOGO6, sep='\n')
        print(' ' * 30, "欢迎使用 CocoPyRPA_v%s" % __version__)
        print(' ' * 30, "作者: %s" % __author__)
        print('-' * 80, end='\n\n\n')

    # ====================================== 系统托盘  ====================================== #

    def setup_system_tray(self):
        """设置系统托盘"""
        # 检查系统是否支持系统托盘
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(self, "错误", "当前系统不支持系统托盘功能！")
            sys.exit(1)

        QApplication.setQuitOnLastWindowClosed(False)  # 防止关闭主窗口后退出程序

        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(":/icons/logo1"))  # 设置托盘图标
        self.tray_icon.setToolTip("CocoPyRPA V2")  # 设置托盘提示文字

        # 创建托盘菜单
        self.tray_menu = QMenu()

        # 添加“鼠标录制”菜单项
        self.mouse_record_action = QAction("鼠标录制")
        self.mouse_record_action.setIcon(QIcon(":/icons/mouse-record"))
        self.mouse_record_action.triggered.connect(self.mouse_record_action_triggered)
        self.tray_menu.addAction(self.mouse_record_action)

        # 添加“键盘录制”菜单项
        self.keys_record_action = QAction("键盘录制")
        self.keys_record_action.setIcon(QIcon(":/icons/keys-record"))
        self.keys_record_action.triggered.connect(self.keys_record_action_triggered)
        self.tray_menu.addAction(self.keys_record_action)

        # 添加“恢复”菜单项
        self.restore_action = QAction("恢复")
        self.restore_action.triggered.connect(self.restore_window)
        self.tray_menu.addAction(self.restore_action)

        # 添加“退出”菜单项
        self.exit_action = QAction("退出")
        self.exit_action.triggered.connect(self.exit_application)
        self.tray_menu.addAction(self.exit_action)

        # 设置托盘菜单
        self.tray_icon.setContextMenu(self.tray_menu)

        # 显示托盘图标
        self.tray_icon.show()

        # 绑定托盘图标单击事件
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        """托盘图标点击事件"""
        if reason == QSystemTrayIcon.Trigger:  # 单击托盘图标恢复窗口
            self.restore_window()

    def restore_window(self):
        """恢复主窗口"""
        self.showNormal()
        self.activateWindow()

    def mouse_record_action_triggered(self):
        """ 录制动作触发 """
        QMessageBox.information(self, "鼠标录制", "开始录制鼠标动作！\n按回车【Enter】记录当前动作\n按【Esc】退出录制")
        self.mouse_record()

    def keys_record_action_triggered(self):
        """ 键盘录制触发 """
        QMessageBox.information(self, "键盘录制", "开始录制键盘动作！\n按 【Tab + Esc】 退出录制")
        self.keys_record()

    def exit_application(self):
        """退出程序"""
        if not self.task_editor_ctrl.is_save:
            self.restore_window()  # 恢复主窗口
            num = self.show_maybe_save_msg_box()  # 显示是否保存消息框
            print(f"用户选择的按钮为：{num}") if _DEBUG else None
            if num == 0:  # 用户选择保存
                # 将当前任务保存到当前打开的 json 文件
                if self.task_editor_ctrl.current_json_path:
                    print(f"保存当前任务到当前打开的 json 文件 '{self.task_editor_ctrl.current_json_path}' ")
                    self.save_task(self.task_editor_ctrl.current_json_path)
                else:
                    # 构建 json 文件路径，获取当前任务列表项的父节点路径
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    json_path = os.path.join(TASK_HOME, f"未命名任务_{timestamp}.json")
                    # 保存当前任务
                    self.save_task(json_path)
                self.close_python_editor()  # 关闭代码编辑器
                self.close()  # 关闭主窗口
                self.tray_icon.hide()
                QApplication.quit()
            elif num == 1:  # 用户选择不保存
                self.close_python_editor()  # 关闭代码编辑器
                self.close()  # 关闭主窗口
                self.tray_icon.hide()
                QApplication.quit()
            elif num == 2:  # 用户选择取消
                return
        else:
            self.close_python_editor()  # 关闭代码编辑器
            self.close()  # 关闭主窗口
            self.tray_icon.hide()
            QApplication.quit()

    # ========================================= 主窗口事件 =================================== #

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        """ 重写显示事件 """
        super().showEvent(a0)
        # self.expand_all_nodes()
        # 检查工作目录是否存在
        if not os.path.exists(TASK_HOME):
            QMessageBox.information(self, "提示", "工作目录不存在，准备创建！", QMessageBox.Ok)
            os.mkdir(TASK_HOME)
        print("主窗口显示") if _DEBUG else None

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        """ 重写关闭事件 """
        close_mode = GLOBAL_CONFIG.get("General", {}).get("Window", {}).get("CloseMode", "normal")
        print(f"当前关闭模式为：{close_mode}") if _DEBUG else None
        if close_mode == "system_tray":
            self.hide()
            return

        if not self.task_editor_ctrl.is_save:
            num = self.show_maybe_save_msg_box()
            print(f"用户选择的按钮为：{num}") if _DEBUG else None
            if num == 0:  # 用户选择保存
                # 将当前任务保存到当前打开的 json 文件
                if self.task_editor_ctrl.current_json_path:
                    print(
                        f"保存当前任务到当前打开的 json 文件 '{self.task_editor_ctrl.current_json_path}' ") if _DEBUG else None
                    self.save_task(self.task_editor_ctrl.current_json_path)
                else:
                    # 构建 json 文件路径，获取当前任务列表项的父节点路径
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    json_path = os.path.join(TASK_HOME, f"未命名任务_{timestamp}.json")
                    self.save_task(json_path)
                self.close_python_editor()  # 关闭代码编辑器
                a0.accept()  # 关闭主窗口
                self.exit_application()  # 退出系统托盘
            elif num == 1:  # 用户选择不保存
                self.close_python_editor()  # 关闭代码编辑器
                a0.accept()  # 关闭主窗口
                self.exit_application()  # 退出系统托盘
            elif num == 2:  # 用户选择取消
                a0.ignore()  # 阻止关闭窗口
        else:
            self.close_python_editor()  # 关闭代码编辑器
            a0.accept()  # 任务已保存，允许关闭窗口
            self.exit_application()  # 退出系统托盘

    def show_maybe_save_msg_box(self) -> int:
        """ 显示可能保存消息框
        :return: 用户选择的按钮索引
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("提示")
        msg_box.setText("当前任务未保存，请先保存后再关闭，是否保存当前任务？")
        save_button = msg_box.addButton("保存", QMessageBox.YesRole)  # 添加保存按钮, 索引为0
        no_save_button = msg_box.addButton("不保存", QMessageBox.NoRole)  # 添加不保存按钮, 索引为1
        cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)  # 添加取消按钮, 索引为2
        return msg_box.exec_()

    def close_python_editor(self):
        """ 关闭代码编辑器 """
        if self.python_editor and self.python_editor.isVisible():
            self.python_editor.close()

    def set_ocr_model(self, ocr):
        """设置 OCR 模型
        :param ocr: OCR 模型对象
        """
        self._ocr = ocr
        executor.ocr = ocr
        print("加载 OCR 模型成功") if _DEBUG else None

    def setDefaultStyle(self):
        """ 主窗口初始化时设置的默认样式 """
        # 设置树型控件样式
        self.cmd_treeWidget.setStyle(CustomTreeIndicatorStyle())

        # 设置主窗口置顶
        is_top_hint = GLOBAL_CONFIG.get("General", {}).get("Window", {}).get("StaysOnTopHint", False)
        if is_top_hint:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # 设置撤销、重做按钮状态
        self.change_undo_redo_state()

    def expand_all_nodes(self):
        """递归展开所有节点"""

        def recursive_expand(index: QModelIndex):
            if not index.isValid():
                return

            self.tasks_view_treeView.expand(index)  # 展开当前节点
            for row in range(self.file_model.rowCount(index)):  # 遍历子节点
                child_index = self.file_model.index(row, 0, index)
                recursive_expand(child_index)

        root_index = self.tasks_view_treeView.rootIndex()
        recursive_expand(root_index)

    def sync_menu_with_attr_edit_dock(self, visible):
        """根据 属性编辑DockWidget 的可见性同步菜单项状态"""
        self.action_menu_attrEditor.setChecked(visible)

    def sync_menu_with_op_view_dock(self, visible):
        """根据 指令库DockWidget 的可见性同步菜单项状态"""
        self.action_menu_cmdLib.setChecked(visible)

    def set_task_view_header(self):
        """设置任务视图的表头"""
        self.headerModel = QStandardItemModel()
        self.headerModel.setColumnCount(4)  # 设置model的列数
        self.headerModel.setHeaderData(0, Qt.Horizontal, '任务', 0)
        self.headerModel.setHeaderData(1, Qt.Horizontal, '大小', 0)
        self.headerModel.setHeaderData(2, Qt.Horizontal, '文件类型', 0)
        self.headerModel.setHeaderData(3, Qt.Horizontal, '修改时间', 0)
        header = self.tasks_view_treeView.header()
        header.setModel(self.headerModel)  # 设置QTreeView 的Header的Model
        # 隐藏其他列，只显示文件名（列0）和创建时间（列3）
        for col in range(self.file_model.columnCount()):
            if col not in (0,):  # 0: 文件名, 3: 创建时间
                self.tasks_view_treeView.hideColumn(col)
        header.setSectionResizeMode(0, header.ResizeToContents)  # 文件名列宽自适应内容
        # header.setSectionResizeMode(3, header.ResizeToContents)  # 创建时间列宽自适应内容

    def on_tasks_item_doubleClicked(self, index: QModelIndex):
        """双击任务列表项目时触发"""
        # 先判断是否已经保存了当前的任务
        if not self.task_editor_ctrl.is_save and \
                os.path.isfile(self.file_model.filePath(index)):
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("提示")
            msg_box.setText("当前任务未保存，请先保存后再切换其它任务，是否保存当前任务？")
            msg_box.addButton("保存", QMessageBox.YesRole)
            msg_box.addButton("不保存", QMessageBox.NoRole)
            msg_box.addButton("取消", QMessageBox.RejectRole)
            # msg_box.finished.connect(self.on_msg_box_finished)
            msg_box.exec_()

            if msg_box.clickedButton().text() == "保存":
                # 将当前任务保存到当前打开的 json 文件
                if self.task_editor_ctrl.current_json_path:
                    print(f"(on_tasks_item_doubleClicked) - 保存当前任务到当前打开的 json 文件 "
                          f"'{self.task_editor_ctrl.current_json_path}' ") if _DEBUG else None
                    self.save_task(self.task_editor_ctrl.current_json_path)
                else:
                    # 构建 json 文件路径，获取当前任务列表项的父节点路径
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    json_path = os.path.join(TASK_HOME, f"未命名任务_{timestamp}.json")
                    # 保存当前任务
                    self.save_task(json_path)
            elif msg_box.clickedButton().text() == "取消":
                return
            else:  # 用户选择不保存
                self.task_editor_ctrl.is_save = True  # 设置任务为已保存

        # 清除撤销栈、重做栈
        self.task_editor_ctrl.undo_stack.clear()
        self.task_editor_ctrl.redo_stack.clear()
        # 设置撤销、重做按钮状态
        self.change_undo_redo_state()

        # 获取当前双击的任务列表节点文件路径
        file_path = self.file_model.filePath(index)
        # 判断是否为文件
        if os.path.isfile(file_path):
            if not file_path.endswith(".json"):
                QMessageBox.warning(self, "错误", "请选择一个 JSON 文件！")
                return
            else:
                # 清除属性编辑器, 不清除表头
                self.attr_edit_tableWidget.clearContents()
                # 加载 JSON 文件并显示
                try:
                    self.task_editor_ctrl.load_from_json(file_path)
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"加载任务 JSON 文件失败: \n{e}")

    # =================================  任务列表右键菜单  ================================= #

    def on_tasks_context_menu(self, position):
        """ 右键任务目录时触发 """
        # 获取点击位置的 QModelIndex
        index = self.tasks_view_treeView.indexAt(position)
        if not index.isValid():
            return
        # 获取当前右键点击的路径
        file_path = self.file_model.filePath(index)
        is_dir = os.path.isdir(file_path)

        # 创建右键菜单
        context_menu = QMenu(self)

        # 新建任务目录
        create_task_dir_action = context_menu.addAction("新建任务目录")
        create_task_dir_action.setIcon(QIcon(":/icons/new-task"))
        create_task_dir_action.triggered.connect(self.new_task_dir)
        # 新建任务文件
        create_task_file_action = context_menu.addAction("新建任务文件")
        create_task_file_action.setIcon(QIcon(":/icons/new-file"))
        create_task_file_action.triggered.connect(lambda: self.new_task_file(file_path))
        # 重命名
        rename_action = context_menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self.rename_task(file_path))
        # 复制
        copy_action = context_menu.addAction("复制")
        copy_action.setIcon(QIcon(":/icons/copy-item"))
        copy_action.triggered.connect(lambda: self.copy_task(file_path))
        # 粘贴
        paste_action = context_menu.addAction("粘贴")
        paste_action.setIcon(QIcon(":/icons/paste-item"))
        paste_action.setEnabled(hasattr(self, '_clipboard_path') and os.path.exists(self._clipboard_path))
        paste_action.triggered.connect(lambda: self.paste_task(file_path))
        # 删除
        delete_action = context_menu.addAction("删除")
        delete_action.setIcon(QIcon(":/icons/delete-item"))
        delete_action.triggered.connect(lambda: self.delete_task(file_path))

        # 分割线
        context_menu.addSeparator()

        # 判断是否为json文件，并显示查看文件内容
        if file_path.endswith(".json"):
            view_file_action = context_menu.addAction("查看文件内容")
            view_file_action.setIcon(QIcon(":/icons/view-file"))
            view_file_action.triggered.connect(lambda: self.view_task_file(file_path))

        # 显示菜单
        context_menu.exec(self.tasks_view_treeView.viewport().mapToGlobal(position))

    # =================================  属性表格右键菜单  ================================= #

    def on_attr_edit_context_menu(self, position):
        """显示右键菜单"""
        item = self.attr_edit_tableWidget.itemAt(position)
        tree_item = self.cmd_treeWidget.currentItem()
        # 判断当前节点是否为 if
        if not tree_item or not tree_item.data(0, Qt.UserRole) or \
                not tree_item.data(0, Qt.UserRole).get("action") == "if":
            return

        menu = QMenu(self)

        # 判断当前属性是否为 condition
        if item and self.attr_edit_tableWidget.currentColumn() == 1 \
                and self.attr_edit_tableWidget.currentRow() == 1:
            edit_condition_action = menu.addAction("编辑 If 判断条件")
            edit_condition_action.setIcon(QIcon(":/icons/if"))
            edit_condition_action.triggered.connect(lambda: self.open_condition_builder(tree_item))

        # 显示菜单
        menu.exec(self.attr_edit_tableWidget.viewport().mapToGlobal(position))

    # ===================================  条件构建器  ==================================== #

    def open_condition_builder(self, tree_item):
        """
        打开条件构建器
        :param tree_item: 当前选中的 if 判断指令
        """
        node_data = tree_item.data(0, Qt.UserRole)
        # 获取当前 if 判断指令之前的所有指令节点数据
        all_commands_data = self.get_preceding_commands(tree_item)
        for i, command_data in enumerate(all_commands_data):
            print(f"指令[{i}]的数据为：{command_data}") if _DEBUG else None

        # 打开条件编辑器
        self.condition_builder = ConditionBuilder(all_commands_data, self)
        if self.condition_builder.exec_() == QDialog.Accepted:
            condition = self.condition_builder.condition
            if condition:
                self.attr_edit_tableWidget.setItem(
                    self.attr_edit_tableWidget.currentRow(), 1,
                    QTableWidgetItem(condition))

    def get_preceding_commands(self, selected_item) -> list:
        """
        遍历指令树，找到用户选中的 if 判断指令之前的所有指令节点。
        :param selected_item: 当前选中的 if 判断指令节点
        :return: all_commands_data 包含所有当前 if 判断指令之前的节点的指令列表
        """
        all_commands_data = []
        iterator = QTreeWidgetItemIterator(self.cmd_treeWidget)

        while iterator.value():
            item = iterator.value()

            # 如果当前节点是选中的 if 指令，停止遍历
            if item == selected_item:
                break

            node_data = item.data(0, Qt.UserRole)  # 获取节点数据

            if node_data:  # 只添加有数据的节点
                node_type = node_data.get("type")  # 获取节点类型
                if node_type == "trigger":  # 跳过触发器节点
                    continue
                params = node_data.get('params')
                if params:  # 只添加有 params 参数字典的节点
                    all_commands_data.append(node_data)

            iterator += 1  # 移动到下一个节点

        return all_commands_data

    # ===============================  选中当前正在运行的节点  =============================== #

    def on_select_node(self, node: Optional[QTreeWidgetItem]):
        """ 选中当前节点 """

        # 清除之前选中的节点
        iterator = QTreeWidgetItemIterator(self.cmd_treeWidget)
        while iterator.value():
            item = iterator.value()
            item.setSelected(False)
            iterator += 1

        # 设置当前节点的选中
        if node:
            node.setSelected(True)
            # TODO: 选中节点后，自动滚动，待解决
            # ---------------- 方法 1 ----------------
            # # 临时禁用更新
            # self.cmd_treeWidget.setUpdatesEnabled(False)
            #
            # def do_scroll():
            #     # 重新启用更新
            #     self.cmd_treeWidget.setUpdatesEnabled(True)
            #     self.cmd_treeWidget.setCurrentItem(node)
            #     # 使用温和的滚动方式
            #     self.cmd_treeWidget.scrollToItem(node, QAbstractItemView.EnsureVisible)
            #     # 确保重新应用样式
            #     self.cmd_treeWidget.viewport().update()
            #
            # # 延迟执行滚动
            # QTimer.singleShot(1, do_scroll)

            # ---------------- 方法 2 ----------------
            # self.cmd_treeWidget.setCurrentItem(node)
            # QTimer.singleShot(0, lambda: self.cmd_treeWidget.scrollToItem(node))

            # ---------------- 方法 3 ----------------
            self.scroll_to_item_with_wheel(self.cmd_treeWidget, node)

    @staticmethod
    def scroll_to_item_with_wheel(tree_widget, item):
        """模拟鼠标滚轮滚动到指定节点"""
        view_rect = tree_widget.viewport().rect()
        item_rect = tree_widget.visualItemRect(item)

        # 判断节点是否已经在视图内
        if view_rect.contains(item_rect):
            return

        # 计算需要滚动的方向和距离
        scroll_direction = 1 if item_rect.top() > view_rect.bottom() else -1
        scroll_steps = abs(item_rect.top() - view_rect.center().y()) // 20  # 每次滚动的像素数

        # 模拟滚轮事件
        for _ in range(scroll_steps):
            delta = QPoint(0, scroll_direction * 40)  # 滚动的单位角度，符合滚轮事件的 `angleDelta` 格式
            pixel_delta = QPoint(0, scroll_direction * 10)  # 代表滚动的像素大小（可根据需要调整）
            event = QWheelEvent(
                QPoint(0, 0),  # 鼠标相对窗口的局部坐标
                QPoint(0, 0),  # 鼠标相对屏幕的全局坐标
                pixel_delta,  # 滚动的像素变化
                delta,  # 滚动的角度变化
                Qt.NoButton,  # 无鼠标按键
                Qt.NoModifier,  # 无修饰键
                Qt.ScrollPhase.ScrollUpdate,  # 滚动阶段
                False,  # 非反向滚动
                Qt.MouseEventNotSynthesized  # 非合成事件
            )
            tree_widget.wheelEvent(event)

    # ================================ 信号触发事件 ================================== #

    def get_template_img(self, image_path):
        """
        获取截图路径
        :param image_path:
        """
        # 获取图片路径
        print(f"(get_template_img) - 图片路径为：{image_path}")
        if os.path.exists(image_path) and image_path:
            print(f"(get_template_img) - 截图路径为：{image_path}")
            # 设置图片文件路径
            current_item = self.cmd_treeWidget.currentItem()
            if current_item is not None:
                item_data = current_item.data(0, Qt.UserRole)  # 获取当前节点的数据
                if item_data is not None:
                    params = item_data.get("params", {})  # 获取参数字典
                    if "template_img" not in params:
                        return
                    params["template_img"] = image_path  # 设置图片文件路径
                    item_data["params"] = params  # 更新节点数据
                    current_item.setData(0, Qt.UserRole, item_data)

                self.task_editor_ctrl.show_params_window(current_item, item_data)
                self.task_editor_ctrl.is_save = False
            else:
                print("(get_template_img) - 当前节点为空")

    def screenshot_window_close(self):
        """ 截图窗口关闭 """
        # 如果主窗口处于隐藏则显示
        if not self.isVisible():
            self.show()
        print("(screenshot_window_close) - 截图窗口关闭")

    def on_tree_row_inserted(self):
        """ 节点插入事件 """
        print("(on_tree_row_inserted) - 节点插入事件") if _DEBUG else None

        self.change_undo_redo_state()

    def on_tree_row_removed(self):
        """ 节点移除事件 """
        print("(on_tree_row_removed) - 节点移除事件") if _DEBUG else None

        self.change_undo_redo_state()

    def change_undo_redo_state(self):
        """
        撤销、重做按钮状态切换函数.

        Note:
            - 在指令编辑器内只要有节点被删除、插入，就会触发此函数
            - 主动撤销、重做操作也会触发此函数
            - 通过撤销栈(undo_stack)、重做栈(redo_stack)是否为空来设置撤销、重做按钮的状态（可用或不可用）
        """
        print("(change_undo_redo_state) - 撤销、重做按钮状态切换") if _DEBUG else None

        if self.task_editor_ctrl.undo_stack:
            # 设置撤销按钮可用
            self.action_menu_undo.setEnabled(True)
        else:
            # 设置撤销按钮不可用
            self.action_menu_undo.setEnabled(False)

        if self.task_editor_ctrl.redo_stack:
            # 设置重做按钮可用
            self.action_menu_redo.setEnabled(True)
        else:
            # 设置重做按钮不可用
            self.action_menu_redo.setEnabled(False)

    # ================================= 菜单项触发事件 ================================== #

    # ----------------  任务列表右键菜单  ----------------

    # 菜单 - 文件 - 新建任务文件
    def new_task_file(self, parent_dir):
        """
        新建任务文件（同时会检查输入的任务文件字符串的合法性）
        """
        if not self.tasks_view_treeView.selectionModel().hasSelection():
            print("没有选中项目")
            QMessageBox.warning(self, "错误", "请选择一个任务目录再创建文件！")
            return
        if not os.path.isdir(parent_dir):
            print("选择的项目不是目录")
            QMessageBox.warning(self, "错误", f" '{parent_dir}' 不是一个目录！\n请选择一个任务目录再创建文件！")
            return

        task_name, ok = QInputDialog.getText(self, "新建任务文件", "请输入任务名称：", QLineEdit.Normal)
        if ok and task_name.strip():
            # 检查任务名称是否合法
            if validate_input(task_name):
                # parent_dir = os.path.abspath(WORK_SPACE + '/work_tasks')
                task_file_path = os.path.join(parent_dir, f"{task_name}.json")
                if not os.path.exists(task_file_path):
                    with open(task_file_path, "w", encoding="utf-8") as f:
                        # 将包含任务名称和空步骤列表的字典以JSON格式写入文件
                        # 参数 ensure_ascii=False 确保非ASCII字符能够正确写入
                        # 参数 indent=4 使得输出的JSON格式化，更易于阅读
                        json.dump({"task_name": task_name, "steps": []}, f, ensure_ascii=False, indent=4)
                    QMessageBox.information(self, "成功", f"任务文件已创建，路径为:\n'{task_file_path}' ")
                else:
                    QMessageBox.warning(self, "失败", "任务文件已存在，请选择其他名称！")
            else:
                QMessageBox.warning(self, "错误", "目录名称包含不允许的字符 ('/' 或 '\\')", QMessageBox.Ok)

    # 右键菜单 - 重命名
    def rename_task(self, file_path):
        """
        重命名任务或目录
        此函数通过图形界面提示用户输入新的名称，并对选定的文件或目录进行重命名操作
        如果重命名成功，将弹出信息对话框显示新的路径，如果失败，则显示错误信息

        :param file_path: (str): 需要重命名的文件或目录的路径
        """
        # 分离文件路径、文件名和扩展名
        base_path, old_name = os.path.split(file_path)
        file_name, file_ext = os.path.splitext(old_name)  # 分离文件名和扩展名
        # 提示用户输入新的名称，默认值为原文件名（不包括扩展名）
        new_name, ok = QInputDialog.getText(self, "重命名", "请输入新名称：", QLineEdit.Normal, file_name)
        # 如果用户点击确定按钮且输入了新的名称，并且新名称与旧名称不同
        if ok and new_name.strip() and new_name != file_name:
            # 检查新名称是否合法
            if validate_input(new_name):
                # 拼接新的文件路径，保留原文件扩展名
                new_path = os.path.join(base_path, f"{new_name}{file_ext}")
                try:
                    # 判断是否是任务 JSON　文件，如果是则更新任务名称
                    if os.path.isfile(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json_text = json.load(f)
                        json_text['task_name'] = new_name
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(json_text, f, ensure_ascii=False, indent=4)
                    # 重命名文件或目录
                    os.rename(file_path, new_path)
                    QMessageBox.information(self, "成功", f"已重命名为：\n'{new_path}' ")
                except Exception as e:
                    QMessageBox.warning(self, "失败", f"重命名失败：{e}")
            else:
                QMessageBox.warning(self, "错误", "目录名称包含不允许的字符 ('/' 或 '\\')", QMessageBox.Ok)

    # 右键菜单 - 复制
    def copy_task(self, file_path):
        """复制任务或目录"""
        self._clipboard_path = file_path
        QMessageBox.information(self, "成功", f"已复制任务文件路径：\n'{file_path}' ")

    # 右键菜单 - 粘贴
    def paste_task(self, target_dir):
        """粘贴任务或目录"""
        if hasattr(self, '_clipboard_path') and os.path.exists(self._clipboard_path):
            base_name = os.path.basename(self._clipboard_path)
            new_path = os.path.join(target_dir, base_name)
            try:
                if os.path.isfile(self._clipboard_path):
                    import shutil
                    shutil.copy(self._clipboard_path, new_path)
                elif os.path.isdir(self._clipboard_path):
                    import shutil
                    shutil.copytree(self._clipboard_path, new_path)
                QMessageBox.information(self, "成功", f"已粘贴到：\n'{new_path}' ")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"粘贴失败：{e}")

    # 右键菜单 - 删除
    def delete_task(self, file_path):
        """删除任务或目录"""
        confirm = QMessageBox.question(self, "删除确认", f"确定要删除 '{file_path}' 吗？",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
                QMessageBox.information(self, "成功", f"已删除：'{file_path}' ")
                self.cmd_treeWidget.clear()  # 清空指令树
                self.attr_edit_tableWidget.clearContents()  # 清空属性编辑表格
            except Exception as e:
                QMessageBox.warning(self, "失败", f"删除失败：{e}")

    # 右键菜单 - 查看文件内容
    def view_task_file(self, file_path):
        """查看任务或目录"""
        if os.path.isfile(file_path):
            file_name = os.path.basename(file_path)
            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(f"查看文件[{file_name}]的数据")
            dialog.resize(500, 600)
            dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 移除默认帮助按钮

            # 布局
            layout = QVBoxLayout(dialog)

            # 创建文本编辑器
            json_text_edit = CoPlainTextEdit(dialog)
            with open(file_path, 'r', encoding='utf-8') as f:
                json_text = json.load(f)
            json_str = json.dumps(json_text, ensure_ascii=False, indent=4)
            json_text_edit.setPlainText(json_str)
            json_text_edit.setReadOnly(True)
            layout.addWidget(json_text_edit)

            # 设置高亮
            highlighter = JSONHighlighter(json_text_edit.document())
            # 设置字体样式
            font = QFont("Courier New")  # 设置字体为等宽字体
            # font.setPixelSize(11)  # 设置字体大小
            json_text_edit.setFont(font)  # 应用字体样式
            # 添加关闭按钮
            button_layout = QHBoxLayout()
            close_button = QPushButton("关闭(close)", dialog)
            close_button.clicked.connect(dialog.close)
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            layout.addLayout(button_layout)

            # 显示对话框
            dialog.exec()

    # 菜单 - 文件 - 新建任务目录
    def new_task_dir(self):
        """新建任务目录（同时会检查输入的目录字符串的合法性）"""
        # 弹出对话框，让用户输入新任务的名称
        task_dir_name, ok_pressed = QInputDialog.getText(self, "新建任务目录", "请输入任务目录名称:", QLineEdit.Normal,
                                                         "")
        if ok_pressed and task_dir_name.strip():
            # 检查目录名称是否合法
            if validate_input(task_dir_name):
                parent_path = os.path.abspath(WORK_SPACE + '/work_tasks')
                # 构建新任务目录的路径
                task_dir_path = os.path.join(parent_path, task_dir_name)
                # 检查目录是否已经存在
                if os.path.exists(task_dir_path):
                    QMessageBox.warning(self, "警告", f"任务目录 '{task_dir_name}' 已经存在！", QMessageBox.Ok)
                else:
                    try:
                        # 尝试创建新目录
                        os.makedirs(task_dir_path)
                        # 在这里可以添加一些额外的逻辑，例如显示成功消息
                        QMessageBox.information(self, "成功", f"任务目录 '{task_dir_name}' 创建成功！",
                                                QMessageBox.Ok)
                    except Exception as e:
                        # 如果目录创建失败，显示错误消息
                        QMessageBox.warning(self, "错误", f"无法创建任务目录:\n{str(e)}", QMessageBox.Ok)
            else:
                QMessageBox.warning(self, "错误", "目录名称包含不允许的字符 ('/' 或 '\\')", QMessageBox.Ok)

    # 菜单 - 文件 - 打开任务 json 文件到窗口
    def open_task(self):
        """ 打开资源管理器并选择任务 JSON 文件，加载任务内容到窗口"""
        # 打开文件选择对话框，默认路径为当前模型根目录
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择任务文件", self.file_model.rootPath(), "JSON Files (*.json)"
        )
        # 如果用户取消了选择
        if not file_path:
            return
        # 尝试加载 JSON 文件内容
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                task_data = json.load(f)
            # 将任务数据加载到窗口（这里假设用 cmd_treeWidget 显示任务）
            self.task_editor_ctrl.load_from_json(file_path)
            QMessageBox.information(self, "成功", f"任务文件\n'{file_path}'\n已加载：")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载文件：\n{e}")

    # 菜单 - 文件 - 保存窗口任务到 json 文件
    def save_task(self, json_path: str = None):
        """ 保存任务到 json 文件
        :param json_path: json文件路径
        """
        if json_path:
            self.task_editor_ctrl.save_to_json(json_path)
        else:
            index = self.tasks_view_treeView.currentIndex()
            _json_path = self.file_model.filePath(index)
            if os.path.isfile(_json_path):
                # 判断 json 文件是否为空
                with open(_json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    # 如果json文件的steps不为空且不是当前打开的json文件则提示用户
                    if json_data.get('steps') and _json_path != self.task_editor_ctrl.current_json_path:
                        json_name = os.path.basename(_json_path)
                        confirm = QMessageBox.question(self,
                                                       "保存确认", f"任务文件 '{json_name}' 不为空，是否覆盖？",
                                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if confirm == QMessageBox.No:  # 用户取消了保存
                            return
                        else:  # 用户确认覆盖
                            self.task_editor_ctrl.save_to_json(_json_path)
                    else:
                        self.task_editor_ctrl.save_to_json(_json_path)
            else:
                QMessageBox.warning(self, "错误", "请在左侧任务列表中选择一个任务文件后再进行保存操作！", QMessageBox.Ok)

    # 菜单 - 文件 - 设置
    def setting(self):
        """ 设置窗口 """
        setting_window = SettingDialog(self.config_manager, parent=self)
        setting_window.tree.expandAll()  # 打开所有节点
        setting_window.exec_()

    # 菜单 - 编辑 - 撤销
    def undo(self):
        """撤销上一步操作"""
        self.change_undo_redo_state()  # 撤销前更新撤销、重做按钮状态
        if not self.task_editor_ctrl.undo_stack:
            message = "[WARN] - 没有可以撤销的操作"
            formatted_message = f"<p align='left'><font color='#ffb700' size='3'>" \
                                f"{message}" \
                                f"</font></p>"
            self.log_textEdit.append(formatted_message)
            return

        self.task_editor_ctrl.undo()
        self.cmd_treeWidget.expandAll()
        self.change_undo_redo_state()  # 撤销后更新撤销、重做按钮状态

    # 菜单 - 编辑 - 重做
    def redo(self):
        """重做上一步操作"""
        self.change_undo_redo_state()  # 重做前更新撤销、重做按钮状态
        if not self.task_editor_ctrl.redo_stack:
            message = "[WARN] - 没有可以重做的操作"
            formatted_message = f"<p align='left'><font color='#ffb700' size='3'>" \
                                f"{message}" \
                                f"</font></p>"
            self.log_textEdit.append(formatted_message)
            return

        self.task_editor_ctrl.redo()
        self.cmd_treeWidget.expandAll()
        self.change_undo_redo_state()  # 重做后更新撤销、重做按钮状态

    # 菜单 - 编辑 - 清空
    def clear(self):
        """清空任务"""
        msg_box = QMessageBox(self)
        clear_button = msg_box.addButton("清空", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setWindowTitle("提示")
        msg_box.setText("是否清空当前任务, 清空后无法撤销!(即会删除所有历史操作)\n但是不会保存当前任务到文件中，确定清空指令吗？")
        msg_box.setDefaultButton(clear_button)  # 设置默认按钮
        msg_box.exec_()

        if msg_box.clickedButton() == cancel_button:
            return

        self.cmd_treeWidget.clear()  # 清空任务
        if self.attr_edit_tableWidget.rowCount() > 0:
            self.attr_edit_tableWidget.clearContents()  # 清空属性编辑表格
        self.task_editor_ctrl.undo_stack.clear()  # 清空撤销栈
        self.task_editor_ctrl.redo_stack.clear()  # 清空重做栈
        self.task_editor_ctrl.is_save = False  # 设置是否保存标志为 False
        self.change_undo_redo_state()  # 更新撤销、重做按钮状态

    # 菜单 - 视图 - 是否显示属性编辑器
    def is_attr_editor(self):
        """控制 attr_edit_dockWidget 的显示和隐藏"""
        if self.action_menu_attrEditor.isChecked():
            self.attr_edit_dockWidget.show()
        else:
            self.attr_edit_dockWidget.hide()

    # 菜单 - 视图 - 是否显示指令操作库
    def is_cmd_lib(self):
        """控制 op_view_dockWidget 的显示和隐藏"""
        if self.action_menu_cmdLib.isChecked():
            self.op_view_dockWidget.show()
        else:
            self.op_view_dockWidget.hide()

    # 菜单 - 视图 - 打开属性绑定窗口
    def open_attr_bind_dialog(self):
        """ 打开属性绑定窗口 """
        self.executor = CommandExecutor(self.cmd_treeWidget, "attr_bind", ocr=self._ocr)
        self.cmd_list = self.executor.extract_commands_from_tree()
        dialog = BindPropertyDialog(self.cmd_list)
        dialog.exec_()

    # 菜单 - 运行 - 运行全部指令
    def run_all(self):
        """运行全部指令"""
        if self.is_running:
            self.stop_executor_thread()
            return

        self.log_textEdit.clear()  # 清空日志

        if GLOBAL_CONFIG.get("General", {}).get("RunMode", "debug") != "debug":
            print("(run_all) - 当前为非 debug 模式")
            # 不是 debug 模式, 最小化窗口
            self.showMinimized()

        # 滚动到最上方
        self.cmd_treeWidget.verticalScrollBar().setValue(0)

        # 创建并启动线程
        self.executor_thread = CommandExecutor(self.cmd_treeWidget, "run_all", ocr=self._ocr)
        self.executor_thread.log_message.connect(self.log_textEdit.append)  # 连接日志信号
        self.executor_thread.select_node.connect(self.on_select_node)  # 连接选中信号
        # self.executor_thread.finished.connect(self.executor_thread.deleteLater)  # 自动释放线程资源
        self.executor_thread.start()

        # 设置菜单项状态
        self.is_running = True
        self.action_menu_runAll.setIcon(QIcon(":/icons/stop"))
        self.action_menu_runOne.setEnabled(False)
        self.action_menu_runNow.setEnabled(False)

        # 恢复菜单项状态
        self.executor_thread.finished.connect(self.on_executor_finished)

    # 菜单 - 运行 - 运行当前选中的指令
    def run_one(self):
        """运行当前选中指令"""
        if self.is_running:
            self.stop_executor_thread()
            return

        current_item = self.cmd_treeWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先单击选择要运行的指令后再运行！")
            return

        self.log_textEdit.clear()  # 清空日志

        if GLOBAL_CONFIG.get("General", {}).get("RunMode", "debug") != "debug":
            print("(run_all) - 当前为非 debug 模式")
            # 不是 debug 模式, 最小化窗口
            self.showMinimized()

        # 创建并启动线程
        self.executor_thread = CommandExecutor(self.cmd_treeWidget, "run_one", ocr=self._ocr)
        self.executor_thread.log_message.connect(self.log_textEdit.append)  # 连接日志信号
        self.executor_thread.select_node.connect(self.on_select_node)  # 连接选中信号
        # self.executor_thread.finished.connect(self.executor_thread.deleteLater)  # 自动释放线程资源
        self.executor_thread.start()

        # 设置菜单项状态
        self.is_running = True
        self.action_menu_runOne.setIcon(QIcon(":/icons/stop"))
        self.action_menu_runAll.setEnabled(False)
        self.action_menu_runNow.setEnabled(False)

        # 恢复菜单项状态
        self.executor_thread.finished.connect(self.on_executor_finished)

    # 菜单 - 运行 - 从当前指令开始运行
    def run_now(self):
        """从当前选中的指令开始往后运行"""
        if self.is_running:
            self.stop_executor_thread()
            return

        current_item = self.cmd_treeWidget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先单击选择要运行的指令后再运行！")
            return
        if current_item.parent() is not None:  # 当前节点不是顶层节点
            QMessageBox.warning(self, "警告", "当前节点不是顶层节点，无法从当前指令开始往后运行！")
            return
        index = self.cmd_treeWidget.indexOfTopLevelItem(current_item)
        if index < 0:
            QMessageBox.warning(self, "警告", "当前节点不存在，无法从当前开始运行")
            return

        self.log_textEdit.clear()  # 清空日志

        if GLOBAL_CONFIG.get("General", {}).get("RunMode", "debug") != "debug":
            print("(run_all) - 当前为非 debug 模式")
            # 不是 debug 模式, 最小化窗口
            self.showMinimized()

        # 创建并启动线程
        self.executor_thread = CommandExecutor(self.cmd_treeWidget, "run_now", ocr=self._ocr)
        self.executor_thread.log_message.connect(self.log_textEdit.append)  # 连接日志信号
        self.executor_thread.select_node.connect(self.on_select_node)  # 连接选中信号
        # self.executor_thread.finished.connect(self.executor_thread.deleteLater)  # 自动释放线程资源
        self.executor_thread.start()

        # 设置菜单项状态
        self.is_running = True
        self.action_menu_runNow.setIcon(QIcon(":/icons/stop"))
        self.action_menu_runAll.setEnabled(False)
        self.action_menu_runOne.setEnabled(False)

        # 恢复菜单项状态
        self.executor_thread.finished.connect(self.on_executor_finished)

    # 菜单 - 运行 - 自动运行
    def run_auto(self):
        """ 自动运行  """
        self.auto_executor_manager.show()

    def stop_executor_thread(self):
        """ 强制终止当前运行的线程 """
        if self.executor_thread and self.executor_thread.isRunning():
            print("(stop_executor_thread) 强制终止线程", self.executor_thread.isRunning())
            self.executor_thread.stop()
            self.executor_thread.wait()  # 等待线程完全退出
            self.executor_thread = None
            QMessageBox.information(self, "信息", "当前运行已被终止！")

        if self.cmd_treeWidget.currentItem():
            # 清除选中节点
            self.on_select_node(None)

        self.is_running = False
        self.action_menu_runAll.setIcon(QIcon(":/icons/run-all"))
        self.action_menu_runOne.setIcon(QIcon(":/icons/run-step"))
        self.action_menu_runNow.setIcon(QIcon(":/icons/run-now"))
        self.action_menu_runAll.setEnabled(True)
        self.action_menu_runOne.setEnabled(True)
        self.action_menu_runNow.setEnabled(True)

    def on_executor_finished(self):
        """ 当执行引擎运行结束时，恢复菜单项运行图标状态 """
        # 判断当前窗口状态
        if self.windowState() & Qt.WindowMinimized:
            self.showNormal()
        else:
            self.show()
        self.is_running = False
        self.action_menu_runAll.setIcon(QIcon(":/icons/run-all"))
        self.action_menu_runOne.setIcon(QIcon(":/icons/run-step"))
        self.action_menu_runNow.setIcon(QIcon(":/icons/run-now"))
        self.action_menu_runAll.setEnabled(True)
        self.action_menu_runOne.setEnabled(True)
        self.action_menu_runNow.setEnabled(True)
        self.executor_thread = None

    def start_script_executor(self, script_path: str):
        """ 启动脚本执行器 """
        print(f"(start_script_executor) -  开始执行脚本文件： ✨{script_path}✨")
        print("*" * 150)
        # 如果不是排队执行模式，则清空日志
        if not self.auto_executor_manager.gui.chk_queue_exec.isChecked():
            self.log_textEdit.clear()
        # self.hide()  # 隐藏主窗口
        self.log_textEdit.append(f"\n开始执行脚本文件：✨{os.path.basename(script_path)}✨")
        executor.current_script = script_path
        executor.start()

    @staticmethod
    def on_progress_updated(script_path: str, current_step: int, total_steps: int):
        """ 更新任务进度 """
        print(f"🔄当前进度：{current_step}/{total_steps},"
              f" stop_flag: {executor.stop_flags[script_path]}")

    # 菜单 - 工具 1 - 截图
    def screen_shot(self):
        """截图"""
        self.hide()  # 隐藏主窗口
        self.screenshot.show()

    # 菜单 - 工具 2 - 鼠标录制
    def mouse_record(self):
        """鼠标录制"""
        # 先保存当前树的状态
        pre_tree_state = self.task_editor_ctrl.export_tree_to_list()
        self.mouse_recorder = MouseRecorder(self.cmd_treeWidget, self.tray_icon)
        self.mouse_recorder.close_signal.connect(self.recover_recorder_status)
        self.mouse_recorder.close_signal.connect(lambda: self.whether_has_record(pre_tree_state))  # 判断是否添加新操作记录
        self.mouse_recorder.show()
        # 禁用主窗口的鼠标、键盘录制菜单项
        self.action_menu_keysRecord.setEnabled(False)
        self.action_menu_mouseRecord.setEnabled(False)
        # 禁用系统托盘的鼠标、键盘录制菜单项
        self.mouse_record_action.setEnabled(False)
        self.keys_record_action.setEnabled(False)

    # 菜单 - 工具 3 - 键盘录制
    def keys_record(self):
        """ 键盘录制 """
        # 先保存当前树的状态
        pre_tree_state = self.task_editor_ctrl.export_tree_to_list()
        self.key_recorder = KeyboardRecorder(self.cmd_treeWidget)
        self.key_recorder.close_signal.connect(self.recover_recorder_status)
        self.key_recorder.close_signal.connect(lambda: self.whether_has_record(pre_tree_state))  # 判断是否添加新操作记录
        self.key_recorder.show()
        # 禁用主窗口的鼠标、键盘录制菜单项
        self.action_menu_keysRecord.setEnabled(False)
        self.action_menu_mouseRecord.setEnabled(False)
        # 禁用系统托盘的鼠标、键盘录制菜单项
        self.mouse_record_action.setEnabled(False)
        self.keys_record_action.setEnabled(False)

    def recover_recorder_status(self):
        """ 恢复鼠标、键盘录制器菜单项状态 """
        # 恢复主窗口的鼠标、键盘录制菜单项状态
        self.action_menu_keysRecord.setEnabled(True)
        self.action_menu_mouseRecord.setEnabled(True)
        # 恢复系统托盘的鼠标、键盘录制菜单项状态
        self.mouse_record_action.setEnabled(True)
        self.keys_record_action.setEnabled(True)

    def whether_has_record(self, pre_tree_state):
        """ 判断录制结束后是否有操作记录 """
        # 如果录制前后树状态不一致，则保存录制前状态到撤销栈
        if pre_tree_state != self.task_editor_ctrl.export_tree_to_list():
            self.task_editor_ctrl.save_tree_state(pre_tree_state)
            self.change_undo_redo_state()  # 更新撤销、重做按钮状态
            self.task_editor_ctrl.node_changed_signal.emit()  # 发送节点改变信号
            print("(whether_has_record) - 保存录制前状态到撤销栈") if _DEBUG else None

    # 菜单 - 工具 4 - 运行 python 脚本
    def exec_python(self):
        """
        执行 python 脚本
        """
        self.python_editor = CodeEditor()  # TODO:这里不能传递父窗口
        self.python_editor.show()

    # 菜单 - 主题 1 - 默认主题
    def is_default_theme(self):
        """ 默认主题 """
        # 加载主窗口样式
        self.setStyleSheet(QL.read_qss_file('resources/theme/default/main.css'))
        # 修改配置文件
        self.config_manager.config["General"]["Theme"] = "默认"
        # 刷新属性编辑窗口
        self.attr_edit_tableWidget.viewport().update()

    # 菜单 - 主题 2 - 深色主题
    def is_dark_theme(self):
        """ 深色主题 """
        # 加载主窗口样式
        self.setStyleSheet(QL.read_qss_file('resources/theme/dark/main.css'))
        # 修改配置文件
        self.config_manager.config["General"]["Theme"] = "深色"
        # 刷新属性编辑窗口
        self.attr_edit_tableWidget.viewport().update()

    # 菜单 - 主题 3 - 浅色主题
    def is_light_theme(self):
        """
        浅色主题
        """
        # 加载主窗口样式
        self.setStyleSheet(QL.read_qss_file('resources/theme/light/main.css'))
        # 修改配置文件
        self.config_manager.config["General"]["Theme"] = "浅色"
        # 刷新属性编辑窗口
        self.attr_edit_tableWidget.viewport().update()

    # 菜单 - 主题 4 - 护眼主题
    def is_protect_eyes_theme(self):
        """
        护眼主题
        """
        self.setStyleSheet(qdarkstyle.load_stylesheet_from_environment())
        # 修改配置文件
        self.config_manager.config["General"]["Theme"] = "护眼"
        # 刷新属性编辑窗口
        self.attr_edit_tableWidget.viewport().update()

    # 菜单 - 帮助 - 指令描述
    def show_cmd_desc(self):
        """ 功能介绍 """
        self.cmd_introduction_dialog.show()

    # 日志窗口右键菜单
    def show_log_context_menu(self, position):
        """
        显示日志文本框的上下文菜单
        :param position: 鼠标位置
        """
        # 创建菜单
        menu = QMenu(self)

        # 添加菜单项
        copy_action = menu.addAction("复制")
        export_action = menu.addAction("导出日志")
        clear_action = menu.addAction("清空日志")

        # 如果没有选中文本，禁用复制选项
        copy_action.setEnabled(self.log_textEdit.textCursor().hasSelection())

        # 显示菜单并获取用户选择
        action = menu.exec_(self.log_textEdit.mapToGlobal(position))

        # 处理菜单项点击
        if action == copy_action:
            self.log_textEdit.copy()
        elif action == export_action:
            self.export_log()
        elif action == clear_action:
            self.log_textEdit.clear()

    def export_log(self):
        """导出日志到文件"""
        # 获取日志内容
        log_content = self.log_textEdit.toPlainText()
        if not log_content.strip():
            QMessageBox.information(self, "提示", "日志内容为空，无需导出！")
            return

        # 获取保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出日志",
            f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                QMessageBox.information(self, "成功", f"日志已成功导出到：\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出日志时出错：{str(e)}")

    # 菜单 - 帮助 - 关于
    def show_about(self):
        """
        显示关于界面
        """
        self.about_dialog.show()

    # 菜单 - 帮助 - 检查更新
    def check_update(self):
        """
        显示更新信息对话框
        """
        self.get_github_version.start()

    def show_update_message(self, version):
        """
        显示更新信息
        :param version: 版本
        """
        if version is not None and version > __version__:
            msg = f"有新版本 {version} 可用，你想更新吗？"
            reply = QMessageBox.question(self, "可用更新", msg, QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                QMessageBox.information(self, "更新", "下载完成后，请解压后覆盖整个软件根目录")
                # 让用户跳转到浏览器下载链接
                webbrowser.open("https://github.com/54Coconi/CocoPyRPA-QT/releases/")
                # TODO: 这里可以添加下载更新文件和安装更新的代码
                ...
        elif version is not None and version <= __version__:
            msg = f"获取的版本为 '{version}'\n当前已是最新版本。"
            print(msg)
            QMessageBox.information(self, "无新版本", msg)
        elif version is None:
            QMessageBox.warning(self, "警告", "无法获取最新版本信息！")


class StopRunningThread(QThread):
    """ 停止指令运行线程 """
    stopSignal = pyqtSignal()

    def run(self):
        # 监听全局的 "Q + Esc" 组合键
        keyboard.add_hotkey('q+esc', self.on_combination_pressed)
        # 进入线程的主循环
        self.exec_()

    def on_combination_pressed(self):
        """Q + Esc 组合键被按下 """
        # 发出停止信号
        self.stopSignal.emit()
        print("Q + Esc 组合键被按下")


class FileSystemModel(QFileSystemModel):
    """自定义 QFileSystemModel 来格式化创建时间"""

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        # 格式化时间为本地化字符串
        if role == Qt.DisplayRole and index.column() == 3:
            file_info = self.fileInfo(index)
            # 获取文件的创建时间
            created_time = file_info.created()
            # 使用 QLocale 格式化时间
            locale = QLocale(QLocale.Chinese)  # 设置为中文格式
            formatted_time = locale.toString(created_time, "yyyy-MM-dd HH:mm:ss")
            return formatted_time
        return super().data(index, role)


class GetVersionThread(QThread):
    """ 检查 github 上的最新版本 """
    version_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    @staticmethod
    def get_github_version():
        """
        检查 github 上的最新版本，并与当前版本进行比较
        :return: latest_version: 最新版本号，如果没有更新则返回 None
        """
        github_api_url = 'https://api.github.com/repos/{owner}/{repo}/releases/latest'
        owner = '54Coconi'  # 仓库所有者
        repo = 'CocoPyRPA-QT'  # 仓库名称

        try:
            response = requests.get(github_api_url.format(owner=owner, repo=repo))
            if response.status_code == 200:  # 如果请求成功
                data = response.json()
                latest_version = data['tag_name'].split('v')[-1]
                print("最新版本: ", latest_version)
                return latest_version
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"获取最新版本时出错: {e}")
            return None

    def run(self):
        version = self.get_github_version()
        self.version_signal.emit(version)


class LoadOcrModel(QThread):
    """ 加载 OCR 模型 """
    ocr_model_signal = pyqtSignal(OCRTool)

    def __init__(self, model="PaddleOCR", parent=None):
        super().__init__(parent)
        self.parent = parent
        self.model = model

    @print_func_time(debug=_DEBUG)
    def run(self):
        if self.model == "PaddleOCR":
            ocr = OCRTool(
                lang='ch',
                det_model_dir=DET_MODEL_DIR,
                rec_model_dir=REC_MODEL_DIR,
                cls_model_dir=CLS_MODEL_DIR,
                use_angle_cls=False
            )
            self.ocr_model_signal.emit(ocr)
        else:
            self.ocr_model_signal.emit(None)
