"""
@author: 54Coconi
@date: 2025-01-25
@version: 1.0.0
@path: core/auto_executor_manager.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    自动执行管理界面
"""
import os
import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread, QDateTime, QTimer
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QCheckBox, QFileDialog, QListWidget,
                             QListWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QDialogButtonBox, QMessageBox, QMenu, QDateTimeEdit, QSpinBox)
from core.commands.base_command import STATUS_COMPLETED, STATUS_PENDING
from core.commands.trigger_commands import ProcessTriggerCmd, NetworkConnectionTriggerCmd, DateTimeTriggerCmd
from core.script_executor import executor  # 引入全局脚本执行器实例

from ui.widgets.coco_toast.toast import ToastService

# 配置常量
WORK_TASKS_ROOT = Path(os.path.abspath("work/work_tasks"))
CONFIG_FILE = r"config\auto_config.json"  # 独立配置文件

TRIGGER_TYPES = {
    "无触发器": None,
    "进程状态监控": {
        "class": ProcessTriggerCmd,
        "params": ["name", "process_name", "trigger_type"]
    },
    "网络连接监控": {
        "class": NetworkConnectionTriggerCmd,
        "params": ["name", "host", "port"]
    },
    "时间到达监控": {
        "class": DateTimeTriggerCmd,
        "params": ["name", "target_time"]
    }
}
TRIGGER_TYPES_TO_ENGLISH = {
    "无触发器": None,
    "进程状态监控": "processTrigger",
    "网络连接监控": "networkTrigger",
    "时间到达监控": "timeTrigger"
}
TRIGGER_DEFAULT_PARAMS = {
    "processTrigger": {
        "name": "进程状态监控",
        "process_name": "",
        "trigger_type": "start"
    },
    "networkTrigger": {
        "name": "网络连接监控",
        "host": "8.8.8.8",
        "port": 53
    },
    "timeTrigger": {
        "name": "时间到达监控",
        "target_time": "2024-12-31 23:59:59"
    }
}

# 同时触发的判断延时(ms)
SIMULTANEOUS_TRIGGER_CHECK_DELAY = 1000

# 样式
STYLESHEET = """
QPushButton {
    font-size: 16px;
}

QLabel {
    font-size: 16px;
}

QComboBox {
    font-size: 16px;
}

QListWidget {
    outline: 0px;
    background-color: #F0F0F0;
    border: 1px solid rgb(212, 212, 212);
    border-radius: 5px;
    padding: 0px;
}

QListWidget::item {
    height: 80px;
    background-color: #F0F0F0;
    border-bottom: 1px solid rgb(212, 212, 212);
    border-radius: 0px;
    margin: 0px;
}

QListWidget::item:hover {
    background-color: #6AB2BC;
}

QListWidget::item:selected {
    background-color: #4D8B93;  /* 选中项的背景颜色 */
}
"""


# 通过字典的键值（value）获取对应的键（key）
def get_dict_key(my_dict, value):
    """
    通过字典的键值（value）获取对应的键（key）
    :param my_dict: 字典
    :param value: 值
    :return: 键
    """
    return [k for k, v in my_dict.items() if v == value][0]


# -------------------- 自定义组件 --------------------
class TriggerItemWidget(QWidget):
    """ 自定义列表项组件 """
    trigger_changed = pyqtSignal(str, str)  # (脚本路径, 触发器类型)
    swh_enable_changed = pyqtSignal(str, bool)  # (脚本路径, 状态)

    def __init__(self, script_path: str, parent=None):
        super(TriggerItemWidget, self).__init__(parent)
        self.script_path = script_path
        self.parent = parent
        self._is_initializing = True  # 标记是否正在初始化
        self._last_trigger_type = None  # 记录上一次的触发器类型
        self._last_trigger_params = None  # 记录上一次的触发器参数

        # 左侧下拉框
        self.cmb_trigger = QComboBox()
        # 触发器实例显示标签
        self.lbl_trigger_instance = QLabel()
        # 中间路径标签
        self.lbl_path = QLabel('~\\' + str(Path(self.script_path).relative_to(WORK_TASKS_ROOT)))
        # 右侧状态开关
        self.swh_enable = QCheckBox()

        self.init_ui()
        self.load_trigger()
        self._is_initializing = False  # 初始化完成

    def init_ui(self):
        """ 初始化界面 """
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 3, 2, 3)  # 设置内边距

        # 触发器类型下拉框
        self.cmb_trigger.addItems(TRIGGER_TYPES.keys())
        self.cmb_trigger.currentIndexChanged.connect(self.on_trigger_changed)
        self.cmb_trigger.setStyleSheet("border: 1px solid rgb(212, 212, 212); border-radius: 2px;")
        # 触发器实例显示标签
        self.lbl_trigger_instance.setStyleSheet("color: #666666; font-style: italic; font-size: 14px;")
        # 脚本路径标签
        self.lbl_path.setToolTip(self.script_path)
        self.lbl_path.setStyleSheet("color: #0000FF; text-decoration: underline;")  # 蓝色字，下划线
        # 状态开关
        self.swh_enable.setVisible(False)
        self.swh_enable.stateChanged.connect(self.on_enable_changed)

        # 设置布局
        layout.addWidget(self.cmb_trigger, 2)  # 2: 伸展
        layout.addWidget(self.lbl_trigger_instance, 3)  # 3: 伸展
        layout.addWidget(self.lbl_path, 4)  # 4: 伸展
        layout.addStretch(1)  # 伸展
        layout.addWidget(self.swh_enable)

        # 设置最小宽度
        self.cmb_trigger.setMinimumWidth(140)
        self.cmb_trigger.setMinimumHeight(30)
        self.lbl_trigger_instance.setMinimumWidth(190)
        self.lbl_path.setMinimumWidth(215)
        self.setLayout(layout)

    def load_trigger(self):
        """ 加载当前脚本的触发器 """
        try:
            with open(self.script_path, encoding='utf-8') as f:
                config = json.load(f)
                steps = config.get("steps", [])
                if steps and steps[0].get("type") == "trigger":
                    trigger_type = steps[0].get("action")  # 获取触发器类型（英文）
                    params = steps[0].get("params", {})

                    # 保存当前触发器状态，用于取消时恢复
                    self._last_trigger_type = trigger_type
                    self._last_trigger_params = params.copy()

                    # 先设置下拉框选中项
                    index = self.cmb_trigger.findText(get_dict_key(TRIGGER_TYPES_TO_ENGLISH, trigger_type))
                    if index > 0:
                        # 阻止信号触发，避免调用 on_trigger_changed
                        self.cmb_trigger.blockSignals(True)
                        self.cmb_trigger.setCurrentIndex(index)
                        self.cmb_trigger.blockSignals(False)

                        # 更新触发器实例显示
                        self._update_trigger_instance(trigger_type, params)
                        self.swh_enable.setVisible(True)  # 设置状态开关可见
                        self.swh_enable.setChecked(False)  # 设置状态开关默认未选中
        except Exception as e:
            print("加载触发器失败:", e)
            self.lbl_trigger_instance.clear()

    def on_trigger_changed(self, index):
        """ 处理触发器类型变更 
        
        :param index: 当前选中的下拉框索引
        """
        if self._is_initializing:
            return  # 初始化时不处理

        trigger_type = self.cmb_trigger.currentText()  # 获取触发器类型（列表项显示的文字，中文）
        eng_trigger_type = TRIGGER_TYPES_TO_ENGLISH.get(trigger_type, "")  # 获取触发器类型（英文）
        is_trigger_selected = index > 0
        self.swh_enable.setVisible(is_trigger_selected)

        # 更新触发器实例显示
        if is_trigger_selected:
            # 获取默认参数
            default_params = TRIGGER_DEFAULT_PARAMS.get(eng_trigger_type, {})
            self._update_trigger_instance(eng_trigger_type, default_params)

            # 触发信号，通知父组件处理触发器变更
            self.trigger_changed.emit(self.script_path, eng_trigger_type)
        else:
            self.lbl_trigger_instance.clear()
            self.trigger_changed.emit(self.script_path, None)  # None 表示无触发器

    def restore_previous_trigger(self):
        """ 恢复到上一次的触发器状态 """
        if self._last_trigger_type is None:
            # 如果之前没有触发器，则设置为无触发器
            self.cmb_trigger.blockSignals(True)
            self.cmb_trigger.setCurrentIndex(0)
            self.cmb_trigger.blockSignals(False)
            self.lbl_trigger_instance.clear()
            self.swh_enable.setVisible(False)
        else:
            # 恢复之前的触发器类型和参数
            trigger_name = get_dict_key(TRIGGER_TYPES_TO_ENGLISH, self._last_trigger_type)
            index = self.cmb_trigger.findText(trigger_name)
            if index > 0:
                self.cmb_trigger.blockSignals(True)
                self.cmb_trigger.setCurrentIndex(index)
                self.cmb_trigger.blockSignals(False)
                self._update_trigger_instance(self._last_trigger_type, self._last_trigger_params)
                self.swh_enable.setVisible(True)

    def _update_trigger_instance(self, trigger_type: str, params: dict):
        """ 更新触发器实例显示 

        :param trigger_type: 触发器类型（英文）
        :param params: 触发器参数字典
        """
        if trigger_type == "processTrigger":
            process_name = params.get("process_name", "")
            trigger_action = params.get("trigger_type", "start")
            action_text = "启动时" if trigger_action == "start" else "关闭时"
            self.lbl_trigger_instance.setText(f"进程 {process_name} ({action_text})")
        elif trigger_type == "networkTrigger":
            host = params.get("host", "")
            port = params.get("port", "")
            self.lbl_trigger_instance.setText(f"连接 {host}:{port} 时")
        elif trigger_type == "timeTrigger":
            target_time = params.get("target_time", "")
            self.lbl_trigger_instance.setText(f"到达 {target_time} 时")
        else:
            self.lbl_trigger_instance.clear()

    def on_enable_changed(self, state):
        """ 处理状态开关变更 """
        self.swh_enable_changed.emit(self.script_path, state == Qt.Checked)


class PropertyEditor(QDialog):
    """ 触发器属性编辑器 """

    def __init__(self, params: Dict, parent=None):
        super(PropertyEditor, self).__init__(parent)
        self.parent = parent
        self.params = params.copy()
        self.table = QTableWidget(self.parent)
        self.btn_box = QHBoxLayout()
        self.init_ui()

    def init_ui(self):
        """ 初始化界面 """
        self.setWindowTitle("编辑触发器属性")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self.parent)

        # 属性表格
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["属性", "值"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)  # 隐藏行号

        # 填充数据
        self.populate_table()

        # 按钮组
        but_save = QPushButton("保存")
        but_save.clicked.connect(self.accept)
        but_cancel = QPushButton("取消")
        but_cancel.clicked.connect(self.reject)
        self.btn_box.addWidget(but_save)
        self.btn_box.addStretch()
        self.btn_box.addWidget(but_cancel)

        layout.addWidget(self.table)
        layout.addLayout(self.btn_box)
        self.setLayout(layout)

    def populate_table(self):
        """ 填充参数到表格 """
        self.table.setRowCount(len(self.params))
        for row, (key, value) in enumerate(self.params.items()):
            # 设置属性名列
            key_item = QTableWidgetItem(key)
            # 设置属性名列不可编辑
            key_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 0, key_item)

            # 设置属性值列
            if key == "target_time":
                # 使用Qt自带的日期时间编辑器
                date_time_editor = QDateTimeEdit(self)
                date_time_editor.setCalendarPopup(True)  # 使用日历弹窗
                date_time_editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 设置显示格式
                date_time_editor.setDateTime(QDateTime.fromString(value, "yyyy-MM-dd HH:mm:ss"))
                self.table.setCellWidget(row, 1, date_time_editor)
            elif key == "trigger_type":
                # 使用下拉框
                combo_box = QComboBox()
                combo_box.addItems(["启动", "关闭"])
                combo_box.setCurrentText("启动" if value == "start" else "关闭")
                self.table.setCellWidget(row, 1, combo_box)
            elif key == "port":
                # 使用整数输入框
                int_editor = QSpinBox()
                int_editor.setRange(1, 65535)
                int_editor.setValue(int(value))
                self.table.setCellWidget(row, 1, int_editor)
            else:
                value_item = QTableWidgetItem(str(value))
                self.table.setItem(row, 1, value_item)

        # 调整列宽
        self.table.resizeColumnsToContents()

    def get_params(self):
        """ 获取编辑后的参数 """
        params = {}
        for row in range(self.table.rowCount()):
            key = self.table.item(row, 0).text()
            # 获取属性值
            value_widget = self.table.cellWidget(row, 1)
            if isinstance(value_widget, QDateTimeEdit):
                value = value_widget.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            elif isinstance(value_widget, QComboBox):
                value = "start" if value_widget.currentText() == "启动" else "stop"
            elif isinstance(value_widget, QSpinBox):
                value = value_widget.value()
            elif value_widget is None and self.table.item(row, 1) is not None:
                value = self.table.item(row, 1).text()
            else:
                value = "未知类型"
            params[key] = value
        return params


# -------------------- 配置管理类 --------------------
class ConfigManager:
    """ 配置管理单例类 """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config_path = Path(CONFIG_FILE)
            cls._instance.config = cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> Dict:
        """ 加载配置文件 """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保配置中包含默认的队列执行状态
                    if "settings" not in config:
                        config["settings"] = {"queue_execution": False}
                    return config
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
        return {"tasks": [], "settings": {"queue_execution": False}}

    def save_config(self):
        """ 保存配置文件 """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"保存配置文件失败: {str(e)}")

    def add_task(self, task_data: Dict):
        """ 添加新任务配置 """
        if not any(t["script_path"] == task_data["script_path"]
                   for t in self.config["tasks"]):
            self.config["tasks"].append(task_data)
            self.save_config()

    def remove_task(self, script_path: str):
        """ 移除任务方法 """
        # 先备份原始配置
        original_tasks = self.config["tasks"].copy()

        try:
            # 从配置中移除
            self.config["tasks"] = [
                t for t in self.config["tasks"]
                if t["script_path"] != script_path
            ]
            self.save_config()

            # 清理脚本文件中的触发器
            self._clean_script_trigger(script_path)
        except Exception as e:
            # 回滚配置
            self.config["tasks"] = original_tasks
            self.save_config()
            raise e

    @staticmethod
    def _clean_script_trigger(script_path: str):
        """ 清理脚本文件中的触发器 """
        if not Path(script_path).exists():
            return

        try:
            with open(script_path, 'r+', encoding='utf-8') as f:
                config = json.load(f)
                steps = config.get("steps", [])

                # 检查并移除触发器
                if steps and steps[0].get("type") == "trigger":
                    # 创建备份副本
                    modified_steps = steps[1:]  # 跳过第一个元素

                    # 验证步骤完整性
                    if len(modified_steps) == 0:
                        config["steps"] = []
                    else:
                        config["steps"] = modified_steps

                    # 写回文件
                    f.seek(0)
                    json.dump(config, f, indent=4, ensure_ascii=False)
                    f.truncate()
        except json.JSONDecodeError:
            logging.error(f"无效的JSON文件：{script_path}")
        except Exception as e:
            logging.error(f"清理触发器失败：{str(e)}")
            raise

    def update_task_status(self, script_path: str, enabled: bool):
        """ 更新任务启用状态 """
        print("(update_task_status) -  更新当前任务状态为: ", enabled)
        for task in self.config["tasks"]:
            if task["script_path"] == script_path:
                task["enabled"] = enabled  # 确保使用布尔值
                break
        self.save_config()

    def get_queue_execution(self) -> bool:
        """ 获取队列执行状态 """
        return self.config.get("settings", {}).get("queue_execution", False)

    def set_queue_execution(self, enabled: bool):
        """ 设置队列执行状态 """
        if "settings" not in self.config:
            self.config["settings"] = {}
        self.config["settings"]["queue_execution"] = enabled
        self.save_config()


class TriggerManager(QObject):
    """ 触发器管理类"""
    triggered = pyqtSignal(str)  # 参数为脚本路径
    set_item_status = pyqtSignal(str, bool)  # 设置列表项状态，参数为(脚本路径, 状态)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_tasks: Dict[str, Any] = {}  # {script_path: {trigger: Trigger, thread: QThread, config: Dict}}
        self.load_tasks()

    def load_tasks(self):
        """ 从配置文件加载任务 """
        config = ConfigManager().config
        for task in config["tasks"]:
            if task.get("enabled", False):
                self._start_monitoring(task["script_path"])

    def toggle_task(self, script_path: str, enable: bool):
        """ 切换任务状态 """
        print("(toggle_task) -  切换当前任务状态为: ", enable)
        if enable:
            self._start_monitoring(script_path)
        else:
            self._stop_monitoring(script_path)
        ConfigManager().update_task_status(script_path, enable)

    def restart_task(self, script_path: str):
        """ 重启任务 """
        print("(restart_task) -  重启当前任务: ", script_path)
        self._stop_monitoring(script_path)
        self._start_monitoring(script_path)

    def on_trigger_status(self, status: int, script_path: str):
        """ 处理触发状态变更 """
        print("(on_trigger_status) -  状态变更为: ", status, " - 当前脚本: ", script_path)
        if status == STATUS_COMPLETED:
            self.triggered.emit(script_path)
            # 重新启动监控
            task = self.active_tasks.get(script_path)
            if task:
                self.restart_task(script_path)
        if status == STATUS_PENDING:
            self.set_item_status.emit(script_path, False)

    def _start_monitoring(self, script_path: str):
        """ 启动任务监控 """
        # 检查是否已经启动
        if script_path in self.active_tasks:
            return

        # 加载脚本配置
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_config = json.load(f)
        except Exception as e:
            logging.error(f"加载脚本失败: {str(e)}")
            return

        # 解析触发器配置
        trigger_config = self._parse_trigger_config(script_config)
        if not trigger_config:
            return

        # 创建触发器实例
        trigger_class = trigger_config["class"]
        trigger = trigger_class(**trigger_config["params"])
        thread = QThread()

        # 将Qt对象移动到线程
        trigger.q_obj.moveToThread(thread)

        # 信号连接
        thread.started.connect(trigger.execute)
        trigger.q_obj.status_changed.connect(
            lambda s: self.on_trigger_status(s, script_path)
        )

        self.active_tasks[script_path] = {
            "trigger": trigger,
            "thread": thread,
            "config": trigger_config
        }
        thread.start()
        print(f"(_start_monitoring) -  脚本 '{script_path}' 已启动监控")

    def _stop_monitoring(self, script_path: str):
        """ 停止任务监控 """
        task = self.active_tasks.get(script_path)
        if task:
            task["thread"].quit()  # 停止线程
            task["trigger"].stop()  # 停止触发器
            del self.active_tasks[script_path]  # 移除任务
            print(f"(_stop_monitoring) -  脚本 '{script_path}' 已停止监控")

    @staticmethod
    def _parse_trigger_config(script_config: Dict) -> Optional[Dict]:
        """ 解析触发器配置（适配新格式） """
        # 获取指令步骤列表
        steps = script_config.get("steps", [])
        if not steps:
            return None
        # 获取第一个指令（判断是否为触发器）
        first_step = steps[0]
        if first_step.get("type") != "trigger":
            return None
        # 获取具体的触发器类型（英文）
        action = first_step.get("action")
        # 获取触发器类型
        trigger_class = TRIGGER_TYPES.get(get_dict_key(TRIGGER_TYPES_TO_ENGLISH, action)).get("class", None)
        if not trigger_class:
            return None

        return {
            "class": trigger_class,
            "params": first_step.get("params", {})
        }


# -------------------- 主界面 --------------------
class TriggerManagerGUI(QWidget):
    """ 触发器管理 GUI 界面"""
    script_executor_on_triggered_signal = pyqtSignal(str)

    def __init__(self, manager: TriggerManager, ocr=None, parent=None):
        super(TriggerManagerGUI, self).__init__(parent)
        self.manager = manager
        self._ocr = ocr
        self.parent = parent
        self.current_script_path = None  # 当前脚本路径
        self.is_stop = False  # 是否停止
        self.work_tasks_root = Path(WORK_TASKS_ROOT).absolute()  # 自动化脚本任务的根目录
        self.task_items: Dict[str, QListWidgetItem] = {}  # 任务列表项
        # 队列执行相关属性
        self.exec_queues: Dict[str, list] = {}  # 执行队列 {trigger_key: [script_path, ...]}
        self.pending_trigger_events: Dict[
            str, tuple[list, QTimer]] = {}  # 待处理触发事件 {trigger_key: ([script_paths], timer)}
        self.executor = executor  # 全局脚本执行器实例
        # toast 通知
        self.toast = ToastService(self.parent)
        self.list_widget = QListWidget(self.parent)  # 任务列表
        self.init_ui()
        self.manager.triggered.connect(self.on_triggered)
        # 连接脚本执行器信号以便在脚本结束后继续队列
        self.executor.execution_finished.connect(self.on_execution_finished)

    def init_ui(self):
        """ 初始化界面 """

        # 主布局
        main_layout = QVBoxLayout(self.parent)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 控制栏
        control_layout = QHBoxLayout(self.parent)
        control_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_add = QPushButton("添加脚本")
        self.btn_remove = QPushButton("移除脚本")
        self.chk_queue_exec = QCheckBox("排队执行")  # 排队执行复选框

        # 加载保存的队列执行状态
        self.chk_queue_exec.setChecked(ConfigManager().get_queue_execution())

        control_layout.addWidget(self.btn_add)
        control_layout.addWidget(self.btn_remove)
        control_layout.addWidget(self.chk_queue_exec)
        control_layout.addStretch()

        # 任务列表
#         self.list_widget.setStyleSheet("""
#         QListWidget {
#     background-color: #222831; /* 设置背景颜色 */
#     border-style: solid; /* 设置边框样式 */
#     border-width: 1px; /* 设置边框宽度 */
#     border-color: #4a5562; /* 设置边框颜色 */
#     border-radius: 2px; /* 设置边框圆角 */
#     font-size: 14px; /* 设置字体大小 */
#     padding: 2px 0px; /* 设置内边距 */
#     color: #ffffff;
# }
#
# QListWidget::item {
#     background-color: #222831; /* 设置背景颜色 */
# 	border-style: solid; /* 设置边框样式 */
#     border-bottom-width: 1px; /* 设置边框宽度 */
#     border-color: #4a5562; /* 设置边框颜色 */
#     border-radius: 0px; /* 设置边框圆角 */
#     font-size: 14px; /* 设置字体大小 */
#     color: #ffffff;
# }
#
# QListWidget::item::hover{
#     background: #8ae6f3;
# }
#         """)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.list_widget)

        # 信号连接
        self.btn_add.clicked.connect(self.add_script)
        self.btn_remove.clicked.connect(self.remove_script)
        self.chk_queue_exec.stateChanged.connect(self._on_queue_exec_changed)

        self.setLayout(main_layout)
        self.load_tasks()

    def add_script(self):
        """ 添加新脚本 """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择自动化脚本",
            str(self.work_tasks_root),  # 默认从工作目录开始选择
            "JSON Files (*.json)"
        )
        if file_path:
            # 存储绝对路径
            abs_path = Path(file_path).absolute().as_posix()

            # 检查是否已存在
            existing_paths = self.task_items.keys()
            if abs_path in existing_paths:
                QMessageBox.warning(self, "提示", "该脚本已存在于任务列表中！")
                return

            # 添加到配置文件(auto_config.json)
            ConfigManager().add_task({
                "script_path": abs_path,
                "enabled": False
            })

            self._add_list_item(file_path, False)

    def remove_script(self):
        """ 移除脚本 """
        current_item = self.list_widget.currentItem()
        if not current_item:
            return
        # 获取脚本路径
        script_path = next(
            k for k, v in self.task_items.items()
            if v == current_item
        )
        # 获取当前列表项的自定义组件
        widget = self.list_widget.itemWidget(current_item)

        confirm = QMessageBox.question(
            self,
            "确认移除",
            f"确定要移除脚本吗？\n{widget.script_path}",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # 从配置文件移除
            ConfigManager().remove_task(script_path)
            # 切换脚本文件状态
            self.manager.toggle_task(script_path, False)
            # 移除脚本列表项
            self.list_widget.takeItem(self.list_widget.row(current_item))
            # 从内存中移除
            del self.task_items[script_path]
            # 同步移除脚本文件内的触发器指令
            self.remove_trigger_from_script(widget.script_path)
            # 从队列中移除
            for q in self.exec_queues.values():
                if script_path in q:
                    q.remove(script_path)

    def _add_list_item(self, script_path: str, enabled: bool):
        """ 添加列表项 """
        item = QListWidgetItem()
        widget = TriggerItemWidget(script_path, self.parent)

        # 设置状态开关
        widget.swh_enable.setChecked(enabled)
        # 信号连接
        widget.trigger_changed.connect(self.handle_trigger_change)
        widget.swh_enable_changed.connect(self.manager.toggle_task)

        item.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        # 存储列表项
        self.task_items[script_path] = item

    def handle_trigger_change(self, script_path: str, eng_trigger_type: str | None):
        """ 处理触发器变更信号
        :param script_path: 脚本路径
        :param eng_trigger_type: 触发器类型(英文) 或 None(表示无触发器)
        """
        # 查找对应的列表项
        item_widget = None
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget.script_path == script_path:
                item_widget = widget
                break

        if item_widget is None:
            return
        # tip: 通过信号传递进来的 eng_trigger_type 不是 None 而是 ''
        if eng_trigger_type is None or eng_trigger_type == '':  # 无触发器
            self.remove_trigger_from_script(script_path)
            return
        else:  # 保存当前触发器状态，用于取消时恢复
            pass

        # 获取默认参数
        default_params = TRIGGER_DEFAULT_PARAMS.get(eng_trigger_type, {})

        # 创建属性编辑器对象
        editor = PropertyEditor(default_params, self.parent)
        if editor.exec_() == QDialog.Accepted:
            # 用户点击确定，更新脚本文件的触发器配置
            new_params = editor.get_params()
            self.update_script_trigger(script_path, eng_trigger_type, new_params)
            # 更新最后一次有效的触发器类型和参数
            item_widget._last_trigger_type = eng_trigger_type
            item_widget._last_trigger_params = new_params.copy()
        else:
            # 用户点击取消，恢复到之前的触发器状态
            item_widget.restore_previous_trigger()

    def update_script_trigger(self, script_path: str, eng_trigger_type: str, params: Dict):
        """ 更新脚本文件里的触发器配置
        :param script_path: 脚本路径
        :param eng_trigger_type: 触发器类型(英文)
        :param params: 触发器参数配置
        """
        try:
            with open(script_path, 'r+', encoding='utf-8') as f:
                config = json.load(f)
                steps = config.get("steps", [])

                # 移除旧触发器配置
                if steps and steps[0].get("type") == "trigger":
                    steps.pop(0)

                # 插入新触发器配置
                new_trigger_config = {
                    "type": "trigger",
                    "action": eng_trigger_type,
                    "icon": "",
                    "params": params
                }
                steps.insert(0, new_trigger_config)

                f.seek(0)
                json.dump(config, f, indent=4, ensure_ascii=False)
                f.truncate()

            # 刷新界面
            self.refresh_item(script_path)

            QMessageBox.information(self, "成功", "触发器已更新！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新失败: {str(e)}")

    def refresh_item(self, script_path: str):
        """ 刷新指定列表项 """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget.script_path == script_path:
                widget.load_trigger()
                break

    def change_item_status(self, script_path: str, enabled: bool):
        """ 切换指定列表项启用状态 """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget.script_path == script_path:
                widget.swh_enable.setChecked(enabled)
                widget.swh_enable.setVisible(True)
                break

    def show_context_menu(self, pos):
        """ 显示右键菜单 """
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        widget = self.list_widget.itemWidget(item)
        if widget.cmb_trigger.currentIndex() > 0:
            menu = QMenu(self.parent)
            edit_action = menu.addAction("编辑触发器属性")
            edit_action.triggered.connect(lambda: self.edit_trigger_properties(widget))
            menu.exec_(self.list_widget.mapToGlobal(pos))

    def edit_trigger_properties(self, widget: TriggerItemWidget):
        """ 编辑触发器属性 """
        try:
            with open(widget.script_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                steps = config.get("steps", [])
                if steps and steps[0].get("type") == "trigger":
                    params = steps[0].get("params", {})
                    editor = PropertyEditor(params, self.parent)
                    if editor.exec_() == QDialog.Accepted:
                        new_params = editor.get_params()
                        # 更新脚本触发器配置
                        # 获取触发器类型（英文）
                        eng_trigger_type = TRIGGER_TYPES_TO_ENGLISH[widget.cmb_trigger.currentText()]
                        self.update_script_trigger(
                            widget.script_path,
                            eng_trigger_type,
                            new_params
                        )
                        if widget.swh_enable.isChecked():
                            # 重启监控
                            self.manager.restart_task(widget.script_path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开属性失败: {str(e)}")

    def remove_trigger_from_script(self, script_path):
        """ 移除脚本里的触发器 """
        try:
            with open(script_path, 'r+', encoding='utf-8') as f:
                config = json.load(f)
                steps = config.get("steps", [])
                if steps and steps[0].get("type") == "trigger":
                    steps.pop(0)

                f.seek(0)
                json.dump(config, f, indent=4, ensure_ascii=False)
                f.truncate()

            # 刷新界面
            self.refresh_item(script_path)
            QMessageBox.information(self, "成功", "触发器已移除！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"移除失败: {str(e)}")

    def load_tasks(self):
        """ 加载配置文件中的任务 """
        config = ConfigManager().config
        for task in config["tasks"]:
            self._add_list_item(task["script_path"], task.get("enabled", False))

    @staticmethod
    def _on_queue_exec_changed(state):
        """ 处理队列执行状态改变事件 """
        enabled = state == Qt.Checked
        ConfigManager().set_queue_execution(enabled)
        logging.info(f"队列执行状态已更新: {'启用' if enabled else '禁用'}")

    def on_triggered(self, script_path: str):
        """ 触发任务执行 """
        # 如果未勾选排队执行，则有脚本正在执行时直接失败
        if not self.chk_queue_exec.isChecked():
            if self.executor.active_scripts:  # 已有脚本在执行
                active_script = os.path.basename(list(self.executor.active_scripts.keys())[0])
                self.toast.show_warning('触发执行失败',
                                        f"已有脚本 '{active_script}' 正在执行中，且未勾选【排队执行】",
                                        5000)
                # QMessageBox.warning(self, "触发执行失败", f"已有脚本 '{active_script}' 正在执行中，且未勾选【排队执行】！")
                return
            # 无脚本执行，直接触发
            self.script_executor_on_triggered_signal.emit(script_path)
            return

        # 如果勾选排队执行
        trigger_cfg = self.manager.active_tasks.get(script_path, {}).get("config")
        trigger_key = self._make_trigger_key(trigger_cfg)

        # 如果当前的触发器不在待处理触发事件中，则添加
        if trigger_key not in self.pending_trigger_events:
            # 新建一个延迟执行定时器
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._process_trigger_events(trigger_key))  # 延迟执行
            timer.start(SIMULTANEOUS_TRIGGER_CHECK_DELAY)  # 1000ms 的延迟窗口
            self.pending_trigger_events[trigger_key] = ([script_path], timer)
        else:
            # 将当前脚本添加到现有的触发器待执行列表
            scripts, _ = self.pending_trigger_events[trigger_key]
            if script_path not in scripts:  # 避免重复添加
                scripts.append(script_path)

        print(f"\n😎(on_triggered) -- 触发器触发\n"
              f"    - 当前触发脚本(script_path): {os.path.basename(script_path)}\n"
              f"    - 触发器键(trigger_key): {trigger_key} \n"
              f"    - 待处理触发事件(pending_trigger_events): {self.pending_trigger_events}\n")

    def _process_trigger_events(self, trigger_key: str):
        """ 处理延迟窗口内收集到的所有触发事件 """
        # 如果当前的触发器不在待处理触发事件中则返回
        if trigger_key not in self.pending_trigger_events:
            return

        scripts, timer = self.pending_trigger_events.pop(trigger_key)
        timer.deleteLater()  # 清理定时器

        if not scripts:
            return

        # 按界面列表顺序排序
        scripts.sort(key=self._get_script_row)

        # 添加到执行队列
        queue = self.exec_queues.setdefault(trigger_key, [])
        queue.extend(scripts)

        print(f"\n🚩(process_trigger_events) -- 处理延迟事件\n"
              f"    - 触发器键(trigger_key): {trigger_key}\n"
              f"    - 待执行脚本(scripts): {scripts}\n"
              f"    - 执行队列(exec_queue): {self.exec_queues}\n")

        # 如果没有脚本在执行，则开始执行队列
        if not self.executor.active_scripts:
            self._start_next_in_queue()

    def _get_script_row(self, script_path: str) -> int:
        """ 获取脚本在列表中的行号，用于排序，若不存在返回一个较大值 """
        item = self.task_items.get(script_path)
        if item is None:
            return 10 ** 6  # 放在最后
        return self.list_widget.row(item)

    def _start_next_in_queue(self):
        """ 从队列中启动下一个脚本 """
        # 遍历队列字典，找到有待执行脚本的队列
        for key in list(self.exec_queues.keys()):
            queue = self.exec_queues[key]
            if queue:
                next_script = queue.pop(0)  # 取出下一个脚本
                self.script_executor_on_triggered_signal.emit(next_script)
                # 清理空队列
                if not queue:
                    self.exec_queues.pop(key, None)
                break

    @staticmethod
    def _make_trigger_key(cfg: Optional[Dict]) -> str:
        """ 根据触发器配置生成唯一键 """
        if not cfg:
            return "unknown"
        cls_name = getattr(cfg.get("class"), "__name__", "unknown")
        return f"{cls_name}:{json.dumps(cfg.get('params', {}), ensure_ascii=False, sort_keys=True)}"

    def on_execution_finished(self, script_path: str, success: bool):
        """ 脚本执行结束后处理队列 """
        # 如果排队执行已启用，则继续下一项
        if self.chk_queue_exec.isChecked():
            # 延迟调用以确保执行器状态已更新
            QTimer.singleShot(100, self._start_next_in_queue)


# -------------------- 主界面 --------------------
class AutoExecutorManager(QDialog):
    """ 自动执行管理器主界面 """
    script_executor_trigger = pyqtSignal(str)

    def __init__(self, ocr=None, parent=None):
        super(AutoExecutorManager, self).__init__(parent)
        self.ocr = ocr
        self.parent = parent

        self.manager = TriggerManager(self.parent)  # 触发器管理器
        self.gui = TriggerManagerGUI(self.manager, self.ocr, self.parent)  # 触发器管理界面
        self.manager.set_item_status.connect(self.gui.change_item_status)

        # 信号传递给主界面(main_window.py)
        self.gui.script_executor_on_triggered_signal.connect(self.script_executor_trigger.emit)

        self.init_ui()

    def init_ui(self):
        """ 初始化界面 """
        self.setWindowTitle("自动执行管理器")
        self.resize(700, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 去除帮助按钮

        layout = QVBoxLayout(self.parent)
        layout.addWidget(self.gui)
        self.setLayout(layout)

        self.set_style()

    def set_style(self):
        """ 设置样式 """
        self.gui.setStyleSheet(STYLESHEET)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        """ 重写显示事件 """
        super().showEvent(a0)
        # 刷新页面
        self.set_style()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        """ 重写关闭事件 """
        super().closeEvent(a0)
        # 清除列表选中状态
        self.gui.list_widget.clearSelection()
