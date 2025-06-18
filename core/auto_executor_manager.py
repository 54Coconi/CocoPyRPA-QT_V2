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
    "进程状态监控": {
        "name": "进程状态监控",
        "process_name": "",
        "trigger_type": "start"
    },
    "网络连接监控": {
        "name": "网络连接监控",
        "host": "8.8.8.8",
        "port": 53
    },
    "时间到达监控": {
        "name": "时间到达监控",
        "target_time": "2024-12-31 23:59:59"
    }
}

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
        # 左侧下拉框
        self.cmb_trigger = QComboBox()
        # 中间路径标签
        self.lbl_path = QLabel(str(Path(self.script_path).relative_to(WORK_TASKS_ROOT)))
        # 右侧状态开关
        self.swh_enable = QCheckBox()

        self.init_ui()
        self.load_trigger()

    def init_ui(self):
        """ 初始化界面 """
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 3, 2, 3)  # 设置内边距

        # 触发器类型下拉框
        self.cmb_trigger.addItems(TRIGGER_TYPES.keys())
        self.cmb_trigger.currentIndexChanged.connect(self.on_trigger_changed)

        # 脚本路径标签
        self.lbl_path.setToolTip(self.script_path)

        # 状态开关
        self.swh_enable.setVisible(False)
        self.swh_enable.stateChanged.connect(self.on_enable_changed)

        layout.addWidget(self.cmb_trigger, 1)  # 1: 伸展
        layout.addWidget(self.lbl_path, 3)  # 3: 伸展
        layout.addStretch(1)  # 伸展
        layout.addWidget(self.swh_enable)
        self.setLayout(layout)

    def load_trigger(self):
        """ 加载当前脚本的触发器 """
        try:
            with open(self.script_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                steps = config.get("steps", [])
                if steps and steps[0].get("type") == "trigger":
                    trigger_type = steps[0].get("action")  # 获取触发器类型（英文）
                    index = self.cmb_trigger.findText(get_dict_key(TRIGGER_TYPES_TO_ENGLISH, trigger_type))
                    if index > 0:
                        self.cmb_trigger.setCurrentIndex(index)
                        self.swh_enable.setVisible(True)
        except Exception as e:
            logging.error(f"加载触发器失败: {str(e)}")

    def on_trigger_changed(self, index):
        """ 处理触发器类型变更 """
        trigger_type = self.cmb_trigger.currentText()
        self.swh_enable.setVisible(index > 0)
        self.trigger_changed.emit(self.script_path, trigger_type)

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
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)

        layout.addWidget(self.table)
        layout.addWidget(self.btn_box)
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
                    return json.load(f)
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
        return {"tasks": []}

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
        """ 增强的移除任务方法 """
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
        # ---------------- 新增队列执行相关属性 ----------------
        self.exec_queues: Dict[str, list] = {}  # {trigger_key: [script_path, ...]}
        self.executor = executor  # 全局脚本执行器实例

        self.list_widget = None  # 任务列表
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
        # 新增：排队执行复选框
        self.chk_queue_exec = QCheckBox("排队执行")

        control_layout.addWidget(self.btn_add)
        control_layout.addWidget(self.btn_remove)
        control_layout.addWidget(self.chk_queue_exec)
        control_layout.addStretch()

        # 任务列表
        self.list_widget = QListWidget(self.parent)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.list_widget)

        # 信号连接
        self.btn_add.clicked.connect(self.add_script)
        self.btn_remove.clicked.connect(self.remove_script)

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
            # --------------- 新增：从队列中移除 ---------------
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

    def handle_trigger_change(self, script_path: str, trigger_type: str):
        """ 处理触发器变更 """
        if trigger_type == "无触发器":
            self.remove_trigger_from_script(script_path)
            return

        # 获取默认参数
        default_params = TRIGGER_DEFAULT_PARAMS.get(trigger_type, {})

        # 编辑属性
        editor = PropertyEditor(default_params, self.parent)
        if editor.exec_() == QDialog.Accepted:
            new_params = editor.get_params()
            self.update_script_trigger(script_path, trigger_type, new_params)
        else:
            # 恢复选择状态
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                widget = self.list_widget.itemWidget(item)
                if widget.script_path == script_path:
                    widget.cmb_trigger.setCurrentIndex(0)
                    break

    def update_script_trigger(self, script_path: str, trigger_type: str, params: Dict):
        """ 更新脚本触发器 """
        try:
            with open(script_path, 'r+', encoding='utf-8') as f:
                config = json.load(f)
                steps = config.get("steps", [])

                # 移除旧触发器
                if steps and steps[0].get("type") == "trigger":
                    steps.pop(0)

                # 插入新触发器
                new_trigger = {
                    "type": "trigger",
                    "action": TRIGGER_TYPES_TO_ENGLISH[trigger_type],
                    "icon": "",
                    "params": params
                }
                steps.insert(0, new_trigger)

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
                        self.update_script_trigger(
                            widget.script_path,
                            widget.cmb_trigger.currentText(),
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

    def on_triggered(self, script_path: str):
        """ 触发任务执行 """
        # 如果未勾选排队执行，则有脚本正在执行时直接失败
        if not self.chk_queue_exec.isChecked():
            # 已有脚本在执行
            if self.executor.active_scripts:
                active_script = os.path.basename(list(self.executor.active_scripts.keys())[0])
                QMessageBox.warning(self, "触发执行失败", f"已有脚本 '{active_script}' 正在执行中，且未勾选【排队执行】！")
                return
            # 无脚本执行，直接触发
            self.script_executor_on_triggered_signal.emit(script_path)
            return

        # ---- 以下为排队执行逻辑 ----
        trigger_cfg = self.manager.active_tasks.get(script_path, {}).get("config")
        trigger_key = self._make_trigger_key(trigger_cfg)
        queue = self.exec_queues.setdefault(trigger_key, [])  # 获取或创建队列
        # 避免重复加入同一队列
        if script_path not in queue:
            queue.append(script_path)

        print(f"\n(on_triggered) -- 触发器触发\n"
              f"  - 【trigger_cfg】: {trigger_cfg} \n"
              f"  - 【trigger_key】: {trigger_key} \n"
              f"  - 【queue】: {queue}\n"
              f"  - 【self.exec_queues】: {self.exec_queues}\n")

        # 如果当前没有脚本在执行，则立即启动队列中的下一个脚本
        if not self.executor.active_scripts:
            self._start_next_in_queue()

    def _get_script_row(self, script_path: str) -> int:
        """ 获取脚本在列表中的行号，用于排序，若不存在返回一个较大值 """
        item = self.task_items.get(script_path)
        if item is None:
            return 10 ** 6  # 放在最后
        return self.list_widget.row(item)

    def _start_next_in_queue(self):
        """ 从队列中启动下一个脚本（按脚本列表顺序） """
        # 遍历各个触发器队列
        for key in list(self.exec_queues.keys()):
            queue = self.exec_queues[key]
            # 清理空队列
            if not queue:
                self.exec_queues.pop(key, None)
                continue
            # 按列表顺序排序
            queue.sort(key=self._get_script_row)
            next_script = queue.pop(0)  # 取出列表序最靠前的脚本
            self.script_executor_on_triggered_signal.emit(next_script)
            # 队列为空则移除
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
        self.resize(500, 600)

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
