"""
指令编辑器模块
"""

import copy
import os
import json

from collections import OrderedDict
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QColor, QFont, QDropEvent, QCursor, QMouseEvent
from PyQt5.QtWidgets import QTreeWidget, QTableWidget, QWidget, QTreeWidgetItem, QTableWidgetItem, QCheckBox, \
    QHeaderView, QMenu, QMessageBox, QHBoxLayout, QPushButton, QVBoxLayout, QDialog, QSpinBox, \
    QDoubleSpinBox, QComboBox, QFileDialog, QApplication, QTreeView

from core.register import registry

from .CocoPositionXY import PositionXY  # 导入自定义坐标控件
from .CocoJsonView import JSONHighlighter  # 导入 JSON 数据高亮器
from .CocoPlainTextEdit import CoPlainTextEdit  # 导入自定义文本编辑器
from .CocoSettingWidget import config_manager  # 导入配置管理器单例
from .CocoTableItemShowImg import ImageWidget  # 导入图片显示控件
from .KeyListenerButton import KeyCaptureButton  # 导入自定义按键捕获按钮

import resources_rc

_DEBUG = True

KEY_CAPTURE_BUTTON_CSS = {
    "默认": """
           KeyCaptureButton {
                border: 1px solid rgb(64,64,64);
                border-radius: 3px;
                color: rgb(200,200,200);
                background-color: rgb(80,64,80);
                selection-color: rgb(255, 255, 255);
                selection-background-color: rgb(47, 100, 182);
                font-family: "Microsoft Yahei";
                font-size: 19px;
           }
           KeyCaptureButton:hover {
                background-color: #775F77FF;
           }
           """,
    "深色": """
            KeyCaptureButton {
                border: 1px solid rgb(64,64,64);
                border-radius: 3px;
                color: rgb(230,230,230);
                background-color: rgb(34,40,49);
                selection-color: rgb(255, 255, 255);
                selection-background-color: rgb(83,121,180);
                font-family: "Microsoft Yahei";
                font-size: 19px;
            }
            KeyCaptureButton:hover {
                background-color: rgb(51, 60, 73);
            }
            """,
    "浅色": """
            KeyCaptureButton {
                border: 1px solid rgb(240, 240, 240);
                border-radius: 1px;
                color: rgb(0, 0, 0);                  /*字体颜色*/
                background-color: rgb(240,240,240);   /*背景颜色*/
                selection-color: rgb(183, 183, 183);  /*选中字体颜色*/
                selection-background-color: rgb(204, 224, 255);  /*选中背景颜色*/
                font-family: "Microsoft Yahei";
                font-size: 19px;
            }
            KeyCaptureButton:hover {
                background-color: rgb(215, 215, 215);
            }
            """,
    "护眼": """
            KeyCaptureButton {
                border: 1px solid rgb(69,83,100);
                border-radius: 1px;
                color: rgb(220, 220, 220);         /*字体颜色*/
                background-color: rgb(25,35,45);   /*背景颜色*/
                selection-color: rgb(255, 255, 255);  /*选中字体颜色*/
                selection-background-color: rgb(204, 224, 255);  /*选中背景颜色*/
                font-family: "Microsoft Yahei";
                font-size: 19px;
            }
            KeyCaptureButton:hover {
                background-color: rgb(55,65,79);
            }
    """
}


def load_key_capture_button_theme() -> str:
    """ 加载 `键盘捕捉按钮` 组件的主题 """
    theme = config_manager.config.get("General", {}).get("Theme", "深色")
    return KEY_CAPTURE_BUTTON_CSS[theme]


def load_edit_mode() -> set:
    """ 加载编辑模式, 返回需要排除的字段集合 """
    edit_mode = config_manager.config.get("General", {}).get("EditMode", "normal")
    if edit_mode == "advanced":
        print("高级编辑模式") if _DEBUG else None
        # 高级编辑模式排除的字段
        return {"type", "action", "icon", "cmd_id", "hold_time"}
    else:
        print("普通编辑模式") if _DEBUG else None
        # 普通编辑模式排除的字段
        return {"type", "action", "icon", "cmd_id", "hold_time", "id", "status", "is_ignore_case", "use_regex"}


def load_json_with_order(file_path) -> OrderedDict:
    """
    加载 JSON 文件并保留原始键的顺序
    :param file_path: JSON 文件路径
    :return: 有序字典 (OrderedDict)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def simulate_mouse_move(tree_widget):
    """ 模拟鼠标移动事件以强制触发绘制刷新

        用于在拖动指令节点后刷新，消除拖拽指示器渲染残留
    """
    cursor_pos = tree_widget.mapFromGlobal(QCursor.pos())
    mouse_event = QMouseEvent(
        QMouseEvent.MouseMove,
        cursor_pos,
        Qt.NoButton,
        Qt.NoButton,
        Qt.NoModifier
    )
    tree_widget.mouseMoveEvent(mouse_event)


class CustomTaskWidget(QWidget):
    """
    自定义指令编辑器树型控件、属性表格控件、指令库树型控件之间的业务逻辑

    """
    # 属性名称 英文->中文 映射字典
    ATTRIBUTE_MAPPING = {
        "name": "指令",
        "is_active": "是否启用",
        "retries": "重复次数",
        "error_retries": "错误重试次数",
        "error_retries_time": "错误重试间隔",
        "status": "执行状态",
        "id": "指令 ID",

        "target_pos": "目标坐标",
        "offset": "相对坐标",
        "clicks": "点击次数",
        "interval": "点击间隔",
        "button": "鼠标按键",
        "duration": "持续时间",
        "scroll_units": "滚动单位",
        "use_pynput": "使用Pynput",

        "key": "按键",
        "keys": "组合热键",
        "text_str": "文本字符串",

        "template_img": "模板图片",
        "text": "匹配文字",
        "match_mode": "匹配模式",
        "is_ignore_case": "忽略大小写",
        "use_regex": "使用正则",

        "dos_cmd": "DOS 命令",
        "working_dir": "工作目录",
        "timeout": "超时时间",
        "code": "Python 脚本",

        "delay_time": "延时",
        "condition": "判断条件",
        "then_commands": "成立执行",
        "else_commands": "不成立执行",
        "count": "循环次数",
        "loop_commands": "被循环指令",

        "subtask_file": "子任务文件",
    }
    # 普通指令类型(鼠标、键盘、脚本、图片)
    NORMAL_TYPES = ["mouse", "keyboard", "script", "image"]
    MAX_UNDO_STACK_SIZE = 50  # 限制最大存储的历史操作数
    # 节点标志
    NODE_FLAG = {
        "only_drag": ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled,
        "only_drop": ~Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled,
        "no_drag_drop": ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled
    }

    # 设置截图信号
    screenshot_signal = pyqtSignal()
    # 设置节点发生改变信号
    node_changed_signal = pyqtSignal()
    # 节点插入信号
    node_inserted_signal = pyqtSignal()
    # 节点删除信号
    node_removed_signal = pyqtSignal()

    def __init__(self, tree_widget: QTreeWidget, attr_edit_table: QTableWidget,
                 tasks_view_treeView: QTreeView, op_view_treeWidget: QTreeWidget):
        """
        :param tree_widget: 主程序的 QTreeWidget, 指令编辑器
        :param attr_edit_table: 主程序的 QTableWidget, 属性编辑表
        :param tasks_view_treeView: 主程序的 QTreeView, 任务列表
        :param op_view_treeWidget: 主程序的 QTreeWidget, 指令库
        """
        super().__init__()
        self.config_manager = config_manager  # 配置管理器
        self.treeWidget = tree_widget  # 指令编辑器
        self.attr_edit_table = attr_edit_table  # 属性编辑表
        self.tasks_view_treeView = tasks_view_treeView  # 任务列表
        self.op_view_treeWidget = op_view_treeWidget  # 指令库
        self.cmd_registry = registry  # 指令注册表

        # ---------------- 设置撤销、重做栈 ----------------
        self.undo_stack = []  # 用于撤销的操作栈
        self.redo_stack = []  # 用于重做的操作栈
        self.previous_tree_state = None  # 上一次的有效树状态
        self.is_save = True  # 是否保存标志

        # 绑定右键菜单信号
        self.treeWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeWidget.customContextMenuRequested.connect(self.on_context_menu)

        # 创建 ImageWidget 对象并传入图片路径参数
        self.image_widget = ImageWidget(image_path='', parent=self.treeWidget)

        self.copied_node_data = None  # 用于存储复制的节点数据
        self.current_json_path = None  # 当前选中的任务 JSON 文件路径
        self.current_item = None  # 当前选中的指令节点
        self.current_item_data = {}  # 当前选中的指令节点数据

        self.treeWidget.itemChanged.connect(self.onTreeItemChanged)  # 监听指令编辑器节点内容变更
        self.treeWidget.itemDoubleClicked.connect(self.onTreeItemDoubleClicked)  # 监听指令编辑器节点双击
        self.treeWidget.itemClicked.connect(self.onTreeItemClicked)  # 监听指令编辑器节点单击
        self.treeWidget.model().rowsAboutToBeRemoved.connect(self.onRowsAboutToBeRemoved)  # 监听指令编辑器即将删除的节点
        self.treeWidget.model().rowsRemoved.connect(self.onTreeRowRemoved)  # 监听指令编辑器节点删除
        self.treeWidget.model().rowsInserted.connect(self.onTreeRowInserted)  # 监听指令编辑器节点插入

        self.op_view_treeWidget.itemDoubleClicked.connect(self.onOpItemDoubleClicked)  # 指令库节点双击

        self.attr_edit_table.cellChanged.connect(self.onAttrTableChanged)  # 监听属性表格变化
        self.attr_edit_table.cellDoubleClicked.connect(self.onAttrTableCellDoubleClicked)  # 监听属性表格双击

        # 在节点变更后自动检查
        # self.treeWidget.itemChanged.connect(self.test_item_changed)
        # 在节点数据发生变化后修改是否保存标志为 False
        self.node_changed_signal.connect(self.on_node_changed)

        # 添加指令节点图标的映射字典
        self.icon_mapping = {
            'mouse': {
                'clickL': ':/icons/mouse-click-left',
                'clickR': ':/icons/mouse-click-right',
                'clickM': ':/icons/mouse-click-middle',
                'moveRel': ':/icons/mouse-rel-move',
                'moveTo': ':/icons/mouse-move',
                'dragRel': ':/icons/mouse-rel-drag',
                'dragTo': ':/icons/mouse-drag',
                'scrollV': ':/icons/wheel-v',
                'scrollH': ':/icons/wheel-h',
            },
            'keyboard': {
                'keyPress': ':/icons/key-press',
                'keyRelease': ':/icons/key-release',
                'keyTap': ':/icons/key-tap',
                'hotkey': ':/icons/key-hotkey',
                'keyType': ':/icons/key-type',
            },
            'image': {
                'imageMatch': ':/icons/img-match',
                'imageClick': ':/icons/img-click',
                'imageOcr': ':/icons/img-ocr',
                'imageOcrClick': ':/icons/img-ocr-click',
            },
            'flow': {
                'delay': ':/icons/delay',
                'if': ':/icons/if',
                'loop': ':/icons/loop',
            },
            'script': {
                'dos': ':/icons/script-dos',
                'python': ':/icons/script-python',
            },
            'system': ':/icons/os',
            'subtask': ':/icons/subtask',
            'trigger': {
                'processTrigger': ':/icons/trigger-process',  # 进程状态监控
                'networkTrigger': ':/icons/trigger-network',  # 网络连接监控
                'timeTrigger': ':/icons/trigger-time',  # 时间到达监控
            }
        }

        # TODO: 连接拖放事件
        self.treeWidget.dragEnterEvent = self.treeDragEnterEvent
        self.treeWidget.dragMoveEvent = self.treeDragMoveEvent
        self.treeWidget.dropEvent = self.treeDropEvent

    def on_node_changed(self):
        """
        当节点数据发生变化时,修改是否保存标志为 False, 即未保存
        """
        self.is_save = False

    # ====================================== 拖拽事件相关 ===================================== #

    def treeDragEnterEvent(self, event):
        """处理拖拽进入事件"""
        # 调用基类的 `dragEnterEvent` 以确保默认行为生效，例如拖拽指示器
        super(QTreeWidget, self.treeWidget).dragEnterEvent(event)
        # 允许来自指令操作库或指令编辑器自身的拖动
        if event.source() in [self.op_view_treeWidget, self.treeWidget]:
            self.treeWidget.expandAll()  # 展开所有节点
            print("(Drag Enter) 允许拖拽") if _DEBUG else None
            event.accept()
        else:
            event.ignore()

    def treeDragMoveEvent(self, event):
        """处理拖拽移动事件"""
        # 调用基类的 `dragMoveEvent` 以确保默认行为生效，例如拖拽指示器样式
        super(QTreeWidget, self.treeWidget).dragMoveEvent(event)
        source_widget = event.source()
        if source_widget not in [self.op_view_treeWidget, self.treeWidget]:
            event.ignore()
            return

        target = self.treeWidget.itemAt(event.pos())
        if not target:
            # 没有放到目标节点上时是否需要接受
            event.accept()

        # 1、外部拖入
        if source_widget == self.op_view_treeWidget:
            print("(Move Event) 外部拖动") if _DEBUG else None
            source_item = self.op_view_treeWidget.currentItem()
            source_data = source_item.data(0, Qt.UserRole) if source_item else None
            print(f"(Move Event) 拖拽项数据: {source_data}") if _DEBUG else None
            event.accept()
        # 2、内部拖动
        else:
            dragged_items = self.treeWidget.selectedItems()
            print("(Move Event) 内部拖动") if _DEBUG else None
            if not dragged_items:
                event.ignore()
                return

            dragged_item = dragged_items[0]
            # 防止拖到自身或其子节点
            current = target
            while current:
                if current == dragged_item:
                    event.ignore()
                    return
                current = current.parent()

            event.accept()

    def treeDropEvent(self, event):
        """处理拖拽释放事件"""
        # 先保存当前树的状态，以便撤销
        self.whether_save_tree_state()

        source_widget = event.source()  # 获取拖拽的源组件
        if source_widget not in [self.op_view_treeWidget, self.treeWidget]:
            event.ignore()  # 忽略指令编辑器、指令库以外的组件
            return

        # 获取被拖入的目标节点
        target_item = self.treeWidget.itemAt(event.pos())

        # 1、从指令操作库拖入
        if source_widget == self.op_view_treeWidget:
            print("(treeDropEvent) 外部拖入")
            # 获取拖拽源节点
            source_item = self.op_view_treeWidget.currentItem()
            if not source_item:
                event.ignore()
                return
            new_item = self.create_new_item(source_item)

            if target_item is not None:
                print(f"(treeDropEvent) 外部拖动到目标节点：{target_item.text(0)}")
                self.add_dropped_item(event, target_item, new_item)
            else:
                self.treeWidget.addTopLevelItem(new_item)

        # 2、内部拖动
        else:
            print("(treeDropEvent) 内部拖动")
            dragged_items = self.treeWidget.selectedItems()
            if not dragged_items:
                event.ignore()
                return

            dragged_item = dragged_items[0]

            # 添加到新位置
            if target_item is not None:
                print(f"(treeDropEvent) 内部拖动到目标节点：{target_item.text(0)}")
                self.add_dropped_item(event, target_item, dragged_item, is_inside=True)  # 内部拖动
            else:
                self.treeWidget.addTopLevelItem(dragged_item)

        # ----------------------------------------------------------------------
        print("(treeDropEvent) 拖动结束")
        if self.validate_tree():  # 验证整个树的结构
            pass
        self.treeWidget.expandAll()  # 展开所有节点
        # self.node_changed_signal.emit()  # 发送节点改变信号
        event.accept()

        self.treeWidget.clearSelection()  # 清空选中状态
        self.treeWidget.viewport().update()  # 强制刷新视图
        simulate_mouse_move(self.treeWidget)  # 模拟鼠标移动事件以确保拖拽指示器消失
        QApplication.processEvents()  # 处理事件队列

    # ===================================== 创建并添加指令 ===================================== #

    def create_new_item(self, item):
        """ 创建指令节点 """
        # 获取拖拽源节点数据
        source_data = copy.deepcopy(item.data(0, Qt.UserRole))
        print(f"添加的指令数据: {source_data}") if _DEBUG else None

        source_item_type = source_data.get("type")  # 获取拖拽源节点类型
        source_item_action = source_data.get("action")  # 获取拖拽源节点动作
        source_item_icon = QIcon(source_data.get("icon"))  # 获取拖拽源节点图标
        source_item_params = source_data.get("params")  # 获取拖拽源节点参数
        # 创建新节点并复制数据
        new_item = QTreeWidgetItem([item.text(0)])
        new_item.setData(0, Qt.UserRole, source_data)
        new_item.setIcon(0, source_item_icon)

        # TODO: 注册指令, 返回指令ID
        cmd_id = self.cmd_registry.register_command(new_item)
        print(f"注册指令id：{cmd_id}") if _DEBUG else None
        print(f"注册后指令数据: {new_item.data(0, Qt.UserRole)}") if _DEBUG else None

        # 判断节点类型, 处理不同类型的节点
        if source_item_type in self.NORMAL_TYPES:
            new_item.setFlags(new_item.flags() & self.NODE_FLAG['only_drag'])
        if source_item_type == "flow":
            self.add_flow(new_item, source_item_action, source_item_params)
        elif source_item_type == "subtask":
            self.add_subtask(new_item, source_item_params)

        return new_item

    def delete_old_item(self, item):
        """ 删除指令树中的某个节点 """
        old_parent = item.parent()
        if old_parent:  # 如果有父节点
            old_parent.takeChild(old_parent.indexOfChild(item))
        else:  # 如果没有父节点
            self.treeWidget.takeTopLevelItem(
                self.treeWidget.indexOfTopLevelItem(item))

    def add_dropped_item(self, event, target_item, dragged_item, is_inside=False):
        """
        添加拖入的节点
        :param event: 拖入事件
        :param target_item: 目标节点
        :param dragged_item: 拖拽节点
        :param is_inside: 是否是内部拖动
        """
        if target_item.data(0, Qt.UserRole) and target_item.data(0, Qt.UserRole).get('type', '') == 'trigger':
            QMessageBox.warning(self.treeWidget, "添加失败", "触发器节点不支持添加任何指令")
            return

        if target_item.text(0).startswith("子任务文件: ") or \
                target_item.parent() and target_item.parent().text(0).startswith("子任务文件: "):
            QMessageBox.warning(self.treeWidget, "添加失败", "子任务节点不支持添加任何指令")
            self.cmd_registry.unregister_command(dragged_item)
            return

        if is_inside:  # 内部拖动，删除原节点
            self.delete_old_item(dragged_item)

        # 判断插入位置
        rect = self.treeWidget.visualItemRect(target_item)
        print(f"(add_dropped_item) 目标节点矩形: {rect}")
        # rect 矩形的比例
        rect_ratio = rect.height() / 4
        # 上半部分和下半部分的分割线
        above_y = rect.y() + rect_ratio  # 上半部分
        bellow_y = rect.y() + rect_ratio * 3  # 下半部分
        target_parent = target_item.parent()
        # 在上半部分插入
        if event.pos().y() < above_y:
            print("(add_dropped_item) 在上半部分插入")
            if target_parent:
                target_parent.insertChild(target_parent.indexOfChild(target_item), dragged_item)
            else:
                index = self.treeWidget.indexOfTopLevelItem(target_item)
                self.treeWidget.insertTopLevelItem(index, dragged_item)
        # 在下半部分插入
        elif event.pos().y() > bellow_y:
            print("(add_dropped_item) 在下半部分插入")
            if target_parent:
                target_parent.insertChild(target_parent.indexOfChild(target_item) + 1, dragged_item)
            else:
                index = self.treeWidget.indexOfTopLevelItem(target_item)
                self.treeWidget.insertTopLevelItem(index + 1, dragged_item)
        # 在中间部分插入
        else:
            print("(add_dropped_item) 添加为目标节点的子节点")
            target_item.addChild(dragged_item)
            target_item.setExpanded(True)

    # ====================================== 节点右键菜单 ===================================== #

    def on_context_menu(self, position):
        """
        右键菜单事件
        """
        # 获取右键点击的节点
        current_item = self.treeWidget.itemAt(position)
        if not current_item:
            return
        # 获取节点数据
        current_item_data = current_item.data(0, Qt.UserRole)

        print(f"(on_context_menu) - 右键点击的节点为：{current_item.text(0)}")

        # 创建右键菜单
        menu = QMenu(self.treeWidget)

        # 菜单项 - 删除任务节点
        delete_action = menu.addAction("删除指令节点")
        delete_action.setIcon(QIcon(":/icons/delete-item"))
        if current_item_data:
            delete_action.setEnabled(True)  # 仅当有数据时启用
        else:
            delete_action.setEnabled(False)
        delete_action.triggered.connect(lambda: self.delete_task_node(current_item))

        # 菜单项 - 复制任务节点
        copy_action = menu.addAction("复制指令节点")
        copy_action.setIcon(QIcon(":/icons/copy-item"))
        if current_item_data:  # 仅当有数据时启用
            copy_action.setEnabled(True)
        else:
            copy_action.setEnabled(False)
        copy_action.triggered.connect(lambda: self.copy_task_node(current_item))

        # 菜单项 - 粘贴任务节点
        paste_action = menu.addAction("粘贴指令节点")
        paste_action.setIcon(QIcon(":/icons/paste-item"))
        if current_item.text(0) in ["成立", "不成立"] or "重复" in current_item.text(0):
            paste_action.setEnabled(True)  # 仅当当前节点是 “成立/不成立/重复“ 时启用
        else:
            paste_action.setEnabled(False)
        paste_action.setEnabled(self.copied_node_data is not None)  # 仅当有复制数据时启用
        paste_action.triggered.connect(lambda: self.paste_task_node(current_item))

        # 添加分割线
        menu.addSeparator()

        # 菜单项 - 选择子任务文件
        # 检查当前节点是否是子任务节点，如果是，添加选择子任务文件的菜单项
        if current_item_data and current_item_data.get('type', '') == 'subtask':
            # print("当前节点是子任务节点")
            choose_subtask_action = menu.addAction("选择子任务文件")
            choose_subtask_action.setIcon(QIcon(":/icons/import-subtask"))
            choose_subtask_action.triggered.connect(lambda: self.choose_subtask_file(current_item))

        # 菜单项 - 选择图片文件 、菜单项 - 截图
        # 检查当前节点是否是图片类型节点
        if current_item_data and current_item_data.get('type', '') == 'image' \
                and current_item_data.get('action', '') in ['imageMatch', 'imageClick']:
            # 创建选择图片文件的菜单项
            choose_image_action = menu.addAction("选择图片文件")
            choose_image_action.setIcon(QIcon(":/icons/import-image"))
            choose_image_action.triggered.connect(lambda: self.choose_image_file(current_item))
            # 创建截图的菜单项
            screen_shot_action = menu.addAction("截图")
            screen_shot_action.setIcon(QIcon(":/icons/screen-shot"))
            screen_shot_action.triggered.connect(self.screen_shot)

        # 添加分割线
        menu.addSeparator()

        # 菜单项 - 查看节点数据
        view_data_action = menu.addAction("查看节点数据")
        view_data_action.setIcon(QIcon(":/icons/view-item"))
        view_data_action.triggered.connect(lambda: self.view_task_node_data(current_item))

        # 检查当前节点是否是触发器
        if current_item_data and current_item_data.get('type', '') == 'trigger':
            delete_action.setVisible(False)  # 不显示删除菜单
            copy_action.setVisible(False)  # 不显示复制菜单
            paste_action.setVisible(False)  # 不显示粘贴菜单

        # 显示菜单
        menu.exec(self.treeWidget.viewport().mapToGlobal(position))

    # 菜单项 - 删除
    def delete_task_node(self, item):
        """
        删除选中的任务节点
        :param item: 选中的任务节点
        """
        confirm = QMessageBox.question(self.treeWidget, "删除确认", f"确定要删除指令节点 '{item.text(0)}' 吗？",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            # 清空当前的属性表内容
            self.attr_edit_table.clearContents()

            # TODO: 注销指令
            self.cmd_registry.unregister_command(item)

            # 先保存当前树的状态，以便撤销
            self.whether_save_tree_state()

            # 从树中删除节点
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.treeWidget.indexOfTopLevelItem(item)
                self.treeWidget.takeTopLevelItem(index)

    # 菜单项 - 复制
    def copy_task_node(self, item):
        """
        复制选中的任务节点及其子节点数据
        :param item: 选中的任务节点
        """
        node_data = self.export_single_node(item)
        self.copied_node_data = node_data
        QMessageBox.information(self.treeWidget, "复制成功", f"已复制任务节点 '{item.text(0)}'")

    # 菜单项 - 粘贴
    def paste_task_node(self, item):
        """
        粘贴任务节点为选中节点的子节点
        :param item: 选中的任务节点
        """
        if not self.copied_node_data:
            QMessageBox.warning(self.treeWidget, "粘贴失败", "没有复制的数据可粘贴")
            return

        # 先保存当前树的状态，以便撤销
        self.whether_save_tree_state()

        # 粘贴复制的数据为子节点
        new_node = self.import_single_node(self.copied_node_data)
        item.addChild(new_node)
        QMessageBox.information(self.treeWidget, "粘贴成功", f"已将复制的任务节点粘贴到 '{item.text(0)}'")

    # 菜单项 - 查看节点数据
    def view_task_node_data(self, item):
        """
        查看任务节点的完整数据,包括 type 和 action,使用可调整大小的窗口
        :param item: 当前任务节点
        """
        node_data = item.data(0, Qt.UserRole)
        if not node_data:
            QMessageBox.information(self.treeWidget, "节点数据", "该任务节点没有附加数据")
            return

        # 重新排列键顺序, 确保 type 和 action 在顶部
        ordered_data = OrderedDict()
        for key in ['type', 'action']:
            if key in node_data:
                ordered_data[key] = node_data[key]
        # 其他键保持原顺序
        ordered_data.update(node_data)

        # 创建对话框
        dialog = QDialog(self.treeWidget)
        dialog.setWindowTitle(f"查看节点 {item.text(0)} 的数据")
        dialog.resize(500, 600)  # 默认大小

        # 布局
        layout = QVBoxLayout(dialog)

        # 创建文本编辑器
        json_text_edit = CoPlainTextEdit(dialog)
        # 将排序好的数据转换为 JSON 格式
        json_text = json.dumps(ordered_data, ensure_ascii=False, indent=4)
        # print("查看节点数据 json_text: ",json_text)
        json_text_edit.setPlainText(json_text)
        json_text_edit.setReadOnly(True)  # TODO:设置 json_text_edit 为只读
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

    # TODO: 导出单个任务节点
    def export_single_node(self, item):
        """
        导出任务节点及其子节点数据
        :param item: 当前任务节点
        :return: 当前节点数据(包含字节点的各种数据)
        """
        if item.text(0) == "成立":
            icon = ":/icons/if-true"
        elif item.text(0) == "不成立":
            icon = ":/icons/if-false"
        elif item.data(0, Qt.UserRole):
            icon = item.data(0, Qt.UserRole).get("icon", "")
        else:
            icon = ""

        node_data = {
            "name": item.text(0),
            "icon": icon,
            "item_data": copy.deepcopy(item.data(0, Qt.UserRole)) or {},
            "children": []
        }
        for i in range(item.childCount()):
            child_item = item.child(i)
            node_data["children"].append(self.export_single_node(child_item))
        return node_data

    # TODO: 导入单个任务节点，需要处理节点的标志 flag
    def import_single_node(self, node_data) -> QTreeWidgetItem:
        """
        导入任务节点数据并创建对应的节点
        :param node_data: 节点数据
        :return: 创建的单个节点
        """
        _node_name = node_data.get("name", "未命名节点")
        _node_icon = node_data.get("icon", "")
        _node_data = node_data.get("item_data", {})
        _node_children = node_data.get("children", [])

        _node_type = _node_data.get("type", "")  # 获取节点类型
        _node_action = _node_data.get("action", "")  # 获取节点动作

        new_item = QTreeWidgetItem([_node_name])  # 创建节点
        new_item.setIcon(0, QIcon(_node_icon))  # 设置节点图标
        new_item.setData(0, Qt.UserRole, _node_data)  # 设置节点数据

        # 处理节点的标志 flag
        if _node_name in ["成立", "不成立"] or "重复" in _node_name:
            new_item.setFlags(new_item.flags() & self.NODE_FLAG['only_drop'])
        else:
            # 普通节点、delay 节点、if 节点、loop 节点、subtask 节点
            if (_node_type in self.NORMAL_TYPES) or \
                    (_node_type == "flow" and _node_action in ["delay", "if", "loop"]) or \
                    (_node_type == "subtask"):
                new_item.setFlags(new_item.flags() & self.NODE_FLAG['only_drag'])
            else:
                # 默认处理逻辑
                new_item.setFlags(new_item.flags() & self.NODE_FLAG['no_drag_drop'])

        # 处理节点是否启用
        # 获取该步骤节点是否启用，并设置禁用状态
        is_active = _node_data.get('params', {}).get('is_active', True)
        new_item.setDisabled(False) if is_active else new_item.setDisabled(True)

        for child_data in _node_children:
            child_item = self.import_single_node(child_data)
            new_item.addChild(child_item)
        return new_item

    # 菜单项 - 选择子任务文件
    def choose_subtask_file(self, item):
        """
        选择子任务文件,并创建子任务节点
        :param item: 当前任务节点
        """
        subtask_file_path = self.get_subtask_file_path()
        if subtask_file_path:
            # 删除子节点
            if item.childCount() > 0:
                # 删除所有子节点
                for i in range(item.childCount() - 1, -1, -1):
                    item.removeChild(item.child(i))
            # 设置子任务文件路径
            item_data = item.data(0, Qt.UserRole)  # 获取当前节点的数据
            params = item_data.get("params", {})  # 获取参数字典
            params["subtask_file"] = subtask_file_path  # 设置子任务文件路径
            item_data["params"] = params  # 更新节点数据
            item.setData(0, Qt.UserRole, item_data)
            # 读取子任务文件
            self.add_subtask(item, {"subtask_file": subtask_file_path})

    def get_subtask_file_path(self):
        """
        获取子任务文件路径
        :return: 子任务文件路径
        """
        default_dir = "./work/work_tasks"
        file_path, _ = QFileDialog.getOpenFileName(self.treeWidget, "选择子任务文件", default_dir,
                                                   "JSON Files (*.json)")
        return file_path

    # 菜单项 - 选择图片文件
    def choose_image_file(self, item):
        """
        选择图片文件
        :param item: 当前任务节点
        """
        image_file_path = self.get_image_file_path()
        if image_file_path:
            # 设置图片文件路径
            item_data = item.data(0, Qt.UserRole)  # 获取当前节点的数据
            params = item_data.get("params", {})  # 获取参数字典
            params["template_img"] = image_file_path  # 设置图片文件路径
            item_data["params"] = params  # 更新节点数据
            item.setData(0, Qt.UserRole, item_data)
            # 显示属性表格
            self.show_params_window(item, item_data)

    def get_image_file_path(self):
        """
        获取图片文件路径
        :return: 图片文件路径
        """
        default_dir = "./work/work_images"
        file_path, _ = QFileDialog.getOpenFileName(self.treeWidget, "选择图片文件", default_dir,
                                                   "Image Files (*.png *.jpg *.jpeg)")
        return file_path

    # 菜单项 - 截图
    def screen_shot(self):
        """
        发送截图信号，触发主程序的截图
        """
        self.screenshot_signal.emit()

    # ================================= 节点单击、双击、插入、移除事件 ================================ #

    def onTreeItemChanged(self, item):
        """
        处理节点改变事件
        """
        print(f"(onTreeItemChanged) - 当前改变的节点为：", item.text(0)) if _DEBUG else None

    def onTreeItemClicked(self, item):
        """处理单击事件"""
        print(f"(onTreeItemClicked) - 当前点击的节点为：", item.text(0)) if _DEBUG else None
        # 获取存储在项目中的参数数据
        item_data = item.data(0, Qt.UserRole)
        print(f"(onTreeItemClicked) - 当前点击的节点数据为：", item_data) if _DEBUG else None
        if item_data:
            self.current_item = item
            self.current_item_data = item_data.copy()  # 拷贝防止直接修改原始数据
            item_type = item_data.get("type", "")
            if item_type == "trigger":
                return
            self.show_params_window(item, item_data)

    def onTreeItemDoubleClicked(self, item):
        """处理双击事件"""
        pass

    def onRowsAboutToBeRemoved(self, parent, rows):
        """处理节点即将被删除事件"""
        # 检查rows的类型，如果是整数，转换为列表
        if isinstance(rows, int):
            rows = [rows]
        for row in rows:
            index = self.treeWidget.model().index(row, 0, parent)
            item = self.treeWidget.itemFromIndex(index)
            print(f"(onRowsAboutToBeRemoved) - 即将被删除的节点: {item.text(0)}") if _DEBUG else None

    def onTreeRowRemoved(self, parent, first, last):
        """处理节点已删除事件"""
        print(f"(onTreeRowRemoved) - 已删除节点") if _DEBUG else None
        self.node_changed_signal.emit()  # 发送节点改变信号
        self.node_removed_signal.emit()  # 发送节点删除信号

    def onTreeRowInserted(self, parent, first, last):
        """处理节点插入事件"""
        if not parent.isValid():
            # 插入的是顶层节点
            for row in range(first, last + 1):
                item = self.treeWidget.topLevelItem(row)
                print(f"(onTreeRowInserted) - 插入顶层节点: {item.text(0)}") if _DEBUG else None
        else:
            # 插入的是子节点
            parent_item = self.treeWidget.itemFromIndex(parent)
            for row in range(first, last + 1):
                index = self.treeWidget.model().index(row, 0, parent)
                inserted_item = self.treeWidget.itemFromIndex(index)
                print(f"(onTreeRowInserted) - 插入子节点: {inserted_item.text(0)}") if _DEBUG else None
        self.node_inserted_signal.emit()  # 发送节点插入信号

    def onOpItemDoubleClicked(self, item):
        """ 指令库节点双击事件 """
        item_data = item.data(0, Qt.UserRole)
        if item_data:
            print("(onOpItemDoubleClicked) - 当前双击的指令库节点数据为：", item_data) if _DEBUG else None
            new_item = self.create_new_item(item)
            # 先保存当前树的状态，以便撤销
            self.whether_save_tree_state()
            # 添加新节点
            self.treeWidget.addTopLevelItem(new_item)

    # =================================== 属性表格单元格变化事件 =================================== #

    def onAttrTableChanged(self, row, column):
        """
        属性值发生变化时自动更新对应的指令数据
        """
        print(f"(onAttrTableChanged) - 属性表格发生变化: row={row}, col={column}") if _DEBUG else None
        if column != 1 or not self.current_item or not self.current_item_data:
            return

        # 获取键和新值
        key_item = self.attr_edit_table.item(row, 0)
        value_item = self.attr_edit_table.item(row, column)
        if not key_item or not value_item:  # 如果键或值不存在
            return

        # 提取英文键名（括号中的内容）,通过切片操作 [start:end] 提取括号内的内容
        key_text = key_item.text()
        key = key_text[key_text.find('(') + 1:key_text.rfind(')')]  # 提取括号中的英文名
        # key = next((k for k, v in self.ATTRIBUTE_MAPPING.items() if v == key_item.text().split('(')[0]), key_item.text())

        # 获取新值
        new_value = value_item.text()
        # 获取当前节点的参数字典
        item_params = self.current_item_data.get('params', {})

        print(f"(onAttributeChanged) - 修改前节点属性为：{item_params}") if _DEBUG else None
        print(f"(onAttributeChanged) - 修改的键为：{key}, 新值为：{new_value}") if _DEBUG else None

        # 尝试转换值类型（根据原始数据类型）
        if key in item_params:
            original_value = item_params[key]
            if isinstance(original_value, int):
                new_value = int(new_value)
            elif isinstance(original_value, float):
                new_value = float(new_value)
            elif isinstance(original_value, bool):
                new_value = new_value.lower() in ('true', '1', 'yes')
            elif isinstance(original_value, list) and "+" in new_value:
                new_value = new_value.split("+")
                pass

        print(f"(onAttributeChanged) - 转换后的新值为：{new_value}") if _DEBUG else None

        # 更新属性字典
        item_params[key] = new_value

        # 同步到当前节点数据的参数字典 params{} 中
        self.current_item_data['params'] = item_params  # 更新参数字典
        self.current_item.setData(0, Qt.UserRole, self.current_item_data)

    # ================================== 属性表格单元格双击事件 ==================================== #

    def onAttrTableCellDoubleClicked(self, row, column):
        """ 属性表格单元格双击事件 """

        print(f"(onAttrTableCellDoubleClicked) - 属性表格单元格双击事件: {row}, {column}") if _DEBUG else None
        if column == 1:  # 第一列为属性值
            self.current_item = self.treeWidget.currentItem()
            if not self.current_item:
                return  # 如果当前节点为空，则退出
            self.current_item_data = self.current_item.data(0, Qt.UserRole)
            if self.current_item_data:
                # 处理图片匹配指令
                if self.current_item_data.get('type') == 'image' and \
                        self.current_item_data.get('action') == 'imageMatch':
                    params = self.current_item_data.get('params', {})
                    img = params.get('template_img', None)
                    print(f"(onAttrTableCellDoubleClicked) - 图片路径为：{img}") if _DEBUG else None
                    if img and row == 1:
                        self.image_widget.preview_image(img)

    # =================================== 保存节点编辑器的状态 ==================================== #

    def save_tree_state(self):
        """
        保存当前树的状态到撤销栈
        """
        tree_state = self.export_tree_to_list()
        print(f"(save_tree_state) - 保存当前树的状态到撤销栈: \n{tree_state}") if _DEBUG else None
        self.undo_stack.append(tree_state)  # 添加到撤销栈
        if len(self.undo_stack) > self.MAX_UNDO_STACK_SIZE:
            self.undo_stack.pop(0)  # 超出限制时，移除最早的历史记录
            QMessageBox.warning(self.treeWidget, "警告",
                                f"撤销栈已达到最大限制 {self.MAX_UNDO_STACK_SIZE} 次，已自动删除最早的历史记录")
        self.redo_stack.clear()  # 清空重做栈
        # self.previous_tree_state = tree_state  # 保存当前树的状态到上一次的有效树状态

    def whether_save_tree_state(self):
        """ 判断是否保存当前树的状态到撤销栈 """
        # 如果撤销栈为空就直接保存
        if not self.undo_stack:
            self.save_tree_state()
            self.node_changed_signal.emit()  # 发送节点改变信号
        # 如果撤销栈不为空，且最后一个状态与当前状态不同，则保存当前状态
        elif self.undo_stack and self.undo_stack[-1] != self.export_tree_to_list():
            self.save_tree_state()
            self.node_changed_signal.emit()  # 发送节点改变信号
        else:
            print("(whether_save_tree_state) - 当前树的状态与撤销栈最后一个状态相同，不保存") if _DEBUG else None

    # ===================================== 撤销、重做 ======================================== #

    def undo(self):
        """
        撤销上一步操作
        """
        # 撤销前必须清空属性表, 避免因为节点被删除导致的错误
        self.attr_edit_table.clearContents()
        print("(undo) - 撤销上一步操作, 当前的撤销栈为：\n", "\n".join(map(str, self.undo_stack))) if _DEBUG else None

        # 将当前状态保存到重做栈
        current_state = self.export_tree_to_list()
        self.redo_stack.append(current_state)
        # TODO: 将当前状态保存为上一次的有效状态
        self.previous_tree_state = current_state
        # 恢复上一个状态
        previous_state = self.undo_stack.pop()  # 从撤销栈中弹出最后一个状态，即回到上一个状态
        self.import_tree_from_list(previous_state)  # 将上一个状态导入到树

    def redo(self):
        """
        重做上一次撤销的操作
        """
        # 重做前必须清空属性表, 避免因为节点被删除导致的错误
        self.attr_edit_table.clearContents()
        print("(redo) - 重做上一步操作, 当前的重做栈为：\n", "\n".join(map(str, self.redo_stack))) if _DEBUG else None

        # 将当前状态保存到撤销栈
        current_state = self.export_tree_to_list()
        self.undo_stack.append(current_state)

        # 恢复下一个状态
        next_state = self.redo_stack.pop()  # 从重做栈中弹出最后一个状态(最近的状态)，即回到下一个状态
        self.import_tree_from_list(next_state)  # 将下一个状态导入到树

    # ================================== 检查树节点的正确性 ==================================== #

    def validate_tree(self) -> bool:
        """
        检查树节点的正确性
        """

        def validate_node(node):
            """
            检查节点的正确性
            :param node: 当前节点
            :return: 是否正确，错误信息
            """
            node_data = node.data(0, Qt.UserRole) or {}
            step_type = node_data.get("type", "")
            action = node_data.get("action", "")

            # TODO：普通指令不允许有子节点
            if step_type in self.NORMAL_TYPES and node.childCount() > 0:
                return False, f"普通类指令 '{node.text(0)}' 不允许包含子节点"

            # If 判断指令
            elif step_type == "flow" and action == "if":
                # 检查子节点是否只有 "成立" 和 "不成立"
                child_texts = []
                child_count = node.childCount()
                if child_count != 2:
                    return False, "If 指令的子节点数量必须为 2, 即只能为 '成立' 和 '不成立' 两个子节点"
                for i in range(node.childCount()):
                    child_texts.append(node.child(i).text(0))
                    print(f"(validate_node) - if 指令的第{i + 1}个子节点为{child_texts[i]}")
                if child_texts != ["成立", "不成立"]:
                    return False, "If 指令的直接子节点必须是 '成立' 和 '不成立'," \
                                  "\n当前为" + ", ".join(child_texts)

            # Loop 循环指令
            elif step_type == "flow" and action == "loop":
                count = node_data.get("params", {}).get("count", 1)
                expected_text = f"重复 {count} 次"
                child_texts = [node.child(i).text(0) for i in range(node.childCount())]
                if child_texts != [expected_text]:
                    return False, f"Loop 指令的直接子节点必须是 '{expected_text}'"

            # delay 延时指令不允许有子节点
            elif step_type == "flow" and action == "delay" and node.childCount() > 0:
                return False, "延时指令不允许包含子节点"

            # subtask 子任务节点检查
            elif step_type == "subtask":
                for i in range(node.childCount()):
                    child_data = node.child(i).data(0, Qt.UserRole)
                    if not child_data or "subtask_file" not in child_data:
                        return False, "子任务节点下只能包含具有 'subtask_file' 属性的节点"

            # 递归检查子节点
            for i in range(node.childCount()):
                is_valid, error_msg = validate_node(node.child(i))
                if not is_valid:
                    return is_valid, error_msg

            return True, ""

        # 遍历所有顶层节点
        for i in range(self.treeWidget.topLevelItemCount()):
            root_item = self.treeWidget.topLevelItem(i)
            is_valid, error_msg = validate_node(root_item)
            if not is_valid:  # 检查失败，输出错误信息
                # QMessageBox.warning(self.treeWidget, "节点检查失败, 恢复到上一次的有效状态", error_msg)
                print(f"(validate_tree) - 节点检查失败，错误信息为：{error_msg}") if _DEBUG else None
                # 恢复到上一次的有效状态
                if self.previous_tree_state:
                    self.import_tree_from_list(self.previous_tree_state)
                return False

        # 检查通过后保存当前树的状态为上一次的有效状态
        self.previous_tree_state = self.export_tree_to_list()
        print("(validate_tree) - 节点检查通过") if _DEBUG else None
        return True

    # ================================= 导出树的结构为嵌套列表 =================================== #

    def export_tree_to_list(self):
        """
        导出树的结构为嵌套列表
        """

        def deepcopy_node_data(node):
            """
            深拷贝节点数据
            :param node:
            :return:
            """
            node_data = copy.deepcopy(self.export_single_node(node))
            return node_data

        return [deepcopy_node_data(self.treeWidget.topLevelItem(i)) for i in range(self.treeWidget.topLevelItemCount())]

    # ================================= 从嵌套列表恢复树的结构 =================================== #

    # TODO: 从嵌套列表恢复树的结构，需要处理节点的标志 flag
    def import_tree_from_list(self, tree_list):
        """
        从嵌套列表恢复树的结构,同时设置节点的图标
        """
        # 导入前必须清空属性表, 避免因为节点被删除导致的错误
        self.attr_edit_table.clearContents()
        self.treeWidget.clear()  # 清空现有树

        # print("(import_tree_from_list) - 从嵌套列表恢复树的结构: \n", "\n".join(map(str, tree_list)))

        def create_node(_data):
            """
            创建节点
            :param _data: 节点数据
            :return: 节点
            """
            # 创建节点
            node = self.import_single_node(_data)
            return node

        for data in tree_list:
            self.treeWidget.addTopLevelItem(create_node(data))

    # =================================== 加载任务 json 文件 ==================================== #

    def load_from_json(self, json_path: str):
        """ 从 JSON 文件加载任务 """
        # TODO: 加载任务时清空已复制的节点数据和撤销栈，并保存当前选中的 JSON 文件路径
        self.copied_node_data = None  # 清空已复制的节点数据
        self.undo_stack.clear()  # 清空撤销栈
        self.current_json_path = json_path  # 保存当前选中的 JSON 文件路径
        task_data = load_json_with_order(json_path)

        # 清空现有树
        self.treeWidget.clear()

        # 添加任务步骤到树形控件
        self.add_steps(None, task_data.get('steps', []))

        # 展开所有节点
        self.treeWidget.expandAll()

        # 保存树状态
        self.previous_tree_state = self.export_tree_to_list()
        # self.treeWidget.itemChanged.connect(self.validate_tree)

    # ================================== 添加任务步骤到树形控件 =================================== #

    def add_steps(self, parent: Optional[QTreeWidgetItem], steps: list):
        """
        添加任务步骤，包括递归处理嵌套指令、子任务
        :param parent: （父）节点
        :param steps: 任务步骤列表
        """
        if not steps:
            print("(add_steps) - 步骤列表为空，无法添加节点。")
            return
        for step in steps:
            step_type = step.get('type', '')  # 获取当前指令步骤的类型
            action = step.get('action', '')  # 获取当前指令步骤的动作
            params = step.get('params', {})  # 获取当前指令步骤的参数字典

            # 获取节点名称, 默认为指令类型和动作,如 "mouse - clickL"
            node_name = params.get('name', f"{step_type} - {action}")
            step_item = QTreeWidgetItem([node_name])  # 创建节点

            # 获取图标
            icon_path = self.get_icon_path(step_type, action, params)
            step_item.setIcon(0, QIcon(icon_path))  # 设置节点图标

            # 存储指令节点数据, 包括图标路径，指令类型，动作类型和参数
            node_data = {
                "icon": icon_path,
                "type": step_type,
                "action": action,
                "params": params
            }
            step_item.setData(0, Qt.UserRole, node_data)

            # 获取该步骤节点是否启用，并设置禁用状态
            is_active = params.get('is_active', True)
            step_item.setDisabled(False) if is_active else step_item.setDisabled(True)

            # 添加指令步骤节点到树形控件
            if parent is None:
                self.treeWidget.addTopLevelItem(step_item)
            else:
                parent.addChild(step_item)

            # -------------------- 处理不同类型节点 --------------------

            # 1、普通节点
            if step_type in self.NORMAL_TYPES:
                # TODO: 设置普通节点为不可接受拖放，但可以被拖动
                step_item.setFlags(step_item.flags() & self.NODE_FLAG['only_drag'])

            # 2、流程控制类节点
            elif step_type == "flow":
                # 添加流程控制指令
                self.add_flow(step_item, action, params)

            # 3、子任务节点
            elif step_type == "subtask":
                # TODO: 设置 subtask 子任务根节点不可拖入，但是可以拖拽
                step_item.setFlags(step_item.flags() & self.NODE_FLAG['only_drag'])
                self.add_subtask(step_item, params)

            # 4、触发器节点
            elif step_type == "trigger":
                # TODO: 设置触发器节点不可拖入、拖拽
                step_item.setFlags(step_item.flags() & self.NODE_FLAG['only_drag'] & self.NODE_FLAG['only_drop'])

    def add_flow(self, item: QTreeWidgetItem, action: str, params: dict):
        """
        添加并处理流程控制节点
        :param item: 当前 flow(流程控制) 节点
        :param action: 当前 flow(流程控制) 节点的具体动作类型(if、loop、delay)
        :param params: 当前 flow(流程控制) 节点参数字典
        """
        if action == "if":
            # TODO: 设置 if 判断根节点不可拖入，但是可以拖拽
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)
            # ---- 添加 Then 分支 ----
            then_commands = params.get("then_commands", [])  # 获取 then 子指令
            then_item = QTreeWidgetItem(item, ["成立"])  # 创建 then 节点
            then_item.setIcon(0, QIcon(":/icons/if-true"))  # 设置图标
            # TODO: 设置 then 节点不可拖拽，但是可以接受拖入
            then_item.setFlags(then_item.flags() & self.NODE_FLAG['only_drop'])
            self.add_steps(then_item, then_commands)  # 递归处理 then 子指令，添加子步骤

            # ---- 添加 Else 分支 ----
            else_commands = params.get("else_commands", [])  # 获取 else 子指令
            else_item = QTreeWidgetItem(item, ["不成立"])  # 创建 else 节点
            else_item.setIcon(0, QIcon(":/icons/if-false"))  # 设置图标
            # TODO: 设置 else 节点不可拖拽，但是可以接受拖入
            else_item.setFlags(else_item.flags() & self.NODE_FLAG['only_drop'])
            self.add_steps(else_item, else_commands)  # 递归处理 else 子指令，添加子步骤
            print(f"(add_steps) - if 节点的子节点数量为 {item.childCount()}") if _DEBUG else None

        elif action == "loop":
            # TODO:设置 loop 根节点不可拖入，但是可以拖拽
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)
            # 添加 Loop 分支
            loop_commands = params.get("loop_commands", [])
            loop_item = QTreeWidgetItem(item, [f"重复 {params.get('count', '')} 次"])
            # TODO: 设置 loop 子节点 "重复" 不可拖拽，但是可以接受拖入
            loop_item.setFlags(loop_item.flags() & self.NODE_FLAG['only_drop'])
            self.add_steps(loop_item, loop_commands)

        elif action == "delay":
            # TODO: 设置 delay 节点可以拖拽，但是不可接受拖入
            item.setFlags(item.flags() & self.NODE_FLAG['only_drag'])

    def add_subtask(self, parent: QTreeWidgetItem, params: dict):
        """
        添加子任务
        :param parent: 父节点
        :param params: 子任务参数
        """
        subtask_file = params.get('subtask_file', None)  # 获取子任务文件路径
        if subtask_file:
            subtask_name = os.path.basename(subtask_file)  # 获取子任务名
            subtask_item = QTreeWidgetItem(parent, [f"子任务文件: {subtask_name}"])  # 创建子任务子节点,parent为父节点
            # TODO: 设置子任务的子节点不可拖拽,不可拖入
            subtask_item.setFlags(subtask_item.flags() & self.NODE_FLAG['no_drag_drop'])
            # 存储子任务文件路径
            subtask_item.setData(0, Qt.UserRole, {"subtask_file": subtask_file})

            # 加载子任务并添加其步骤
            try:
                subtask_data = load_json_with_order(subtask_file)
                subtask_steps = subtask_data.get('steps', [])
                self.add_steps(subtask_item, subtask_steps)
            except Exception as e:
                QMessageBox.critical(self.treeWidget, "错误", f"加载子任务文件\n'{subtask_file}'\n时出错: {e}")
                print(f"加载子任务文件 {subtask_file} 时出错: {e}")

    def get_icon_path(self, step_type: str, action: str, params: dict) -> str:
        """根据指令类型和动作获取图标路径"""
        print(f"(get_icon_path) 当前的 step_type: {step_type}, action: {action}") if _DEBUG else None
        if step_type in self.icon_mapping:
            type_mapping = self.icon_mapping[step_type]  # 获取指令类型对应的所有动作图标
            if isinstance(type_mapping, dict):
                if step_type == "mouse" and action == "click":  # 鼠标点击类指令根据 button 参数获取图标
                    if params.get('button') == 'left':  # 获取左键图标
                        return type_mapping.get('clickL', ':/icons/default')
                    elif params.get('button') == 'right':  # 获取右键图标
                        return type_mapping.get('clickR', ':/icons/default')
                    elif params.get('button') == 'middle':  # 获取中键图标
                        return type_mapping.get('clickM', ':/icons/default')
                    return ':/icons/icon-not-found'
                return type_mapping.get(action, ':/icons/icon-not-found')
            return type_mapping
        return ':/icons/icon-not-found'

    # ======================================== 显示属性表格 ====================================== #

    # TODO: 显示指令属性表格相关
    def show_params_window(self, item, item_data):
        """
        将属性加载到主程序的 QTableWidget 中，并支持嵌套结构
        :param item: 当前选中的树节点
        :param item_data: 节点的属性数据
        """
        if not item_data:
            print("[show_params_window] -- 当前节点没有属性数据")
            return

        print(f"\n[show_params_window] 当前的节点：{item.text(0)}，数据为：\n{dict(item_data)}") if _DEBUG else None
        # 清空表格
        self.attr_edit_table.blockSignals(True)  # 暂停信号，防止初始化表格时触发事件
        self.attr_edit_table.clear()
        self.attr_edit_table.setRowCount(0)
        self.attr_edit_table.setColumnCount(2)
        self.attr_edit_table.setHorizontalHeaderLabels(['属性', '值'])

        # 获取所有属性（包括嵌套的）
        flat_attributes = self.flatten_attributes(item_data)
        print(f"[show_params_window] 获取到的属性值：\n{flat_attributes}") if _DEBUG else None

        # 过滤掉不需要显示的属性 type、action、icon
        exclude_attributes = load_edit_mode()
        filtered_attributes = {k: v for k, v in flat_attributes.items() if k not in exclude_attributes}
        print(f"[show_params_window] 过滤后的属性值：\n{filtered_attributes}") if _DEBUG else None

        # 填充属性表格
        for row, (key, value) in enumerate(filtered_attributes.items()):
            # 获取映射后的中文属性名
            display_key = self.ATTRIBUTE_MAPPING.get(key, key) + f"\n({key})"
            name_item = QTableWidgetItem(display_key)
            name_item.setFlags(Qt.ItemIsEnabled)  # 禁止编辑属性列
            self.attr_edit_table.insertRow(row)
            self.attr_edit_table.setItem(row, 0, name_item)

            # ------ TODO: 根据属性类型设置属性值单元格的控件 ------
            # TODO: name 属性设置为只读
            if key in ["name", "id", "status"]:
                value_item = QTableWidgetItem(str(value))
                value_item.setData(Qt.UserRole, key)  # 将原始键存储到单元格中
                value_item.setFlags(Qt.ItemIsEnabled)  # 禁止编辑指令名
                self.attr_edit_table.setItem(row, 1, value_item)
            # 布尔值使用 QCheckBox
            elif isinstance(value, bool):
                checkbox = QCheckBox()  # 创建一个 QCheckBox
                checkbox.setChecked(value)  # 设置选中状态
                checkbox.setCursor(Qt.PointingHandCursor)  # 设置鼠标样式为手势
                hLayout = QHBoxLayout()  # 创建一个水平布局
                hLayout.addWidget(checkbox)  # 将 QCheckBox 添加到水平布局中
                hLayout.setContentsMargins(0, 0, 0, 0)  # 设置布局的边距
                hLayout.setAlignment(Qt.AlignHCenter)  # 设置布局的对齐方式为水平居中
                widget = QWidget(self.attr_edit_table)  # 创建一个 QWidget
                widget.setLayout(hLayout)  # 设置 QWidget 的布局为水平布局
                self.attr_edit_table.setCellWidget(row, 1, widget)  # 将 QWidget 设置为表格的单元格
                # 绑定状态改变事件
                checkbox.stateChanged.connect(
                    lambda state, _key=key: self.update_bool_attribute(item_data, _key, state, item)
                )

            # retries、error_retries、clicks、count、scroll_units 使用 QSpinBox
            elif isinstance(value, int) and \
                    (key == "retries" or key == "error_retries" or
                     key == "clicks" or key == "count" or key == "scroll_units"):
                spinbox_int = QSpinBox()  # 创建一个 QSpinBox
                spinbox_int.setCursor(Qt.ArrowCursor)  # 设置鼠标样式为指针
                spinbox_int.setFocusPolicy(Qt.ClickFocus)  # 设置聚焦策略
                # 滚动单位可以是负的
                if key == "scroll_units":
                    spinbox_int.setSuffix(" 单位")  # 设置后缀为 "单位"
                    spinbox_int.setMinimum(-9999)  # 设置最小值
                    spinbox_int.setMaximum(9999)  # 设置最大值
                    spinbox_int.setSingleStep(1)  # 设置步长
                    spinbox_int.setValue(value)  # 设置初始值
                else:
                    if key == "count":
                        spinbox_int.setPrefix("重复 ")  # 设置前缀为 "重复"
                        spinbox_int.setSuffix(" 次")  # 设置后缀为 "次"
                    elif key == "clicks":
                        spinbox_int.setPrefix("点击 ")  # 设置前缀为 "点击 "
                        spinbox_int.setSuffix(" 次")  # 设置后缀为 "次"
                    elif key == "retries":
                        spinbox_int.setPrefix("重试 ")  # 设置前缀为 "重试 "
                        spinbox_int.setSuffix(" 次")  # 设置后缀为 "次"
                    elif key == "error_retries":
                        spinbox_int.setPrefix("错误重试 ")  # 设置前缀为 "错误重试 "
                        spinbox_int.setSuffix(" 次")  # 设置后缀为 "次"

                    spinbox_int.setMinimum(0)  # 设置最小值
                    spinbox_int.setMaximum(9999)  # 设置最大值
                    spinbox_int.setSingleStep(1)  # 设置步长
                    spinbox_int.setValue(value)  # 设置初始值

                self.attr_edit_table.setCellWidget(row, 1, spinbox_int)
                # 绑定值改变信号
                spinbox_int.valueChanged.connect(
                    lambda _value, _key=key: self.update_int_attribute(item_data, _key, _value, item)
                )

            # 时间变量 duration、delay_time、interval 使用 QDoubleSpinBox
            elif isinstance(value, float) and \
                    (key == "duration" or key == "delay_time"
                     or key == "interval" or key == "error_retries_time"):
                spinbox = QDoubleSpinBox()  # 创建一个 QDoubleSpinBox
                spinbox.setDecimals(2)  # 设置小数位数为 2
                spinbox.setMinimum(0.00)  # 设置最小值
                spinbox.setMaximum(9999.00)  # 设置最大值
                spinbox.setSingleStep(0.20)  # 设置步长
                spinbox.setSuffix(" s")  # 设置后缀为 "s"
                spinbox.setValue(value)  # 设置初始值
                self.attr_edit_table.setCellWidget(row, 1, spinbox)
                # 绑定duration值改变信号
                spinbox.valueChanged.connect(
                    lambda _value, _key=key: self.update_double_attribute(item_data, _key, _value, item)
                )

            # 坐标位置 target_pos,相对坐标 offset 使用自定义的 PositionXY
            elif isinstance(value, (tuple, list)) and \
                    (key == "target_pos" or key == "offset"):
                widget = PositionXY(value[0], value[1])
                # 绑定坐标值改变信号
                widget.valueChanged.connect(
                    lambda x, y, _key=key: self.update_pos_attribute(item_data, _key, (x, y), item))
                self.attr_edit_table.setCellWidget(row, 1, widget)

            # 鼠标按键类型 left、right、middle 使用 QComboBox
            elif isinstance(value, str) and key == "button":
                combobox = QComboBox()  # 创建一个 QComboBox
                combobox.addItems(["left", "right", "middle"])  # 添加选项
                combobox.setCurrentText(value)  # 设置初始选中项
                self.attr_edit_table.setCellWidget(row, 1, combobox)
                # 绑定鼠标按键值改变信号
                combobox.currentTextChanged.connect(
                    lambda _value, _key=key: self.update_button_attribute(item_data, _key, _value, item))

            # 文字识别匹配模式 match_mode 使用 QComboBox
            elif isinstance(value, str) and key == "match_mode":
                combobox = QComboBox()  # 创建一个 QComboBox
                combobox.addItems(["完全匹配", "部分匹配"])  # 添加选项
                combobox.setCurrentText(value)  # 设置初始选中项
                self.attr_edit_table.setCellWidget(row, 1, combobox)
                # 绑定匹配模式值改变信号
                combobox.currentTextChanged.connect(
                    lambda _value, _key=key: self.update_match_mode_attribute(item_data, _key, _value, item))

            # loop_commands、then_commands、else_commands 显示指令步骤
            elif isinstance(value, list) and (key == "loop_commands" or
                                              key == "then_commands" or key == "else_commands"):
                display_values = [f"[{i + 1}]{cmd.get('params')['name']}" for i, cmd in enumerate(value)]
                value_item = QTableWidgetItem("\n".join(display_values))
                value_item.setData(Qt.UserRole, key)  # 将原始键存储到单元格中
                self.attr_edit_table.setItem(row, 1, value_item)

            #  键盘按键使用自定义的 KeyCaptureButton
            elif isinstance(value, str) and key == "key":
                key_button_single = KeyCaptureButton()
                key_button_single.setStyleSheet(load_key_capture_button_theme())
                if "&" in value:
                    key_button_single.setText(value.replace("&", "&&"))
                else:
                    key_button_single.setText(value)
                self.attr_edit_table.setCellWidget(row, 1, key_button_single)
                key_button_single.key_changed.connect(
                    lambda _value, _key=key: self.update_key_attribute(item_data, _key, _value, item))

            # 热键组合使用自定义的 KeyCaptureButton
            elif isinstance(value, list) and key == "keys":
                key_button_combine = KeyCaptureButton(mode="shortcut")  # 设置为快捷键模式
                key_button_combine.setStyleSheet(load_key_capture_button_theme())
                display_keys = ""
                for i, _key in enumerate(value):
                    if i > 0:
                        display_keys += "+"
                    display_keys += _key.replace("&", "&&") if _key == "&" else _key
                key_button_combine.setText(display_keys)
                self.attr_edit_table.setCellWidget(row, 1, key_button_combine)
                key_button_combine.key_changed.connect(
                    lambda _value, _key=key: self.update_hotkey_attribute(item_data, _key, _value, item))

            # template_img 使用自定义的 QLabel
            elif isinstance(value, str) and key == "template_img":
                image_widget = ImageWidget(value, self.treeWidget)  # 初始化时就设置好了图片显示 label
                if os.path.exists(value):
                    self.attr_edit_table.setCellWidget(row, 1, image_widget)
                else:
                    value_item = QTableWidgetItem("文件不存在")
                    value_item.setFlags(Qt.ItemIsEnabled)  # 设置单元格不可编辑
                    self.attr_edit_table.setItem(row, 1, value_item)

            else:  # 其他类型使用普通单元格
                value_item = QTableWidgetItem(str(value))
                value_item.setData(Qt.UserRole, key)  # 将原始键存储到单元格中
                self.attr_edit_table.setItem(row, 1, value_item)

        # 设置表格样式
        self.attr_edit_table.resizeRowsToContents()  # 自适应行高
        self.attr_edit_table.blockSignals(False)  # 恢复信号

    def flatten_attributes(self, attributes: dict, parent_key='') -> dict:
        """
        将嵌套的属性字典展平为扁平结构。
        :param attributes: 原始属性字典
        :param parent_key: 父级键名，用于构建嵌套键名
        :return: 展平的属性字典
        """
        items = {}
        for key, value in attributes.items():
            # TODO: 考虑是否需要处理嵌套列表的情况
            # new_key = f"{parent_key}.{key}" if parent_key else key
            new_key = key
            if isinstance(value, dict):
                # 递归展平嵌套字典
                items.update(self.flatten_attributes(value, new_key))
            else:
                items[new_key] = value
        return items

    # ====================================== 更新指令属性 ===================================== #

    def update_bool_attribute(self, item_data, key, state, item):
        """
        更新布尔值属性的值，当 QCheckBox 状态改变时触发。
        """
        params = item_data.get('params', {})  # 获取参数字典
        is_checked = bool(state == Qt.Checked)
        params[key] = is_checked
        self.node_changed_signal.emit()
        print(f"(update_bool_attribute) - 更新布尔值属性 {key} 为 {is_checked}")

        self.current_item_data['params'] = params  # 更新参数字典
        item.setData(0, Qt.UserRole, self.current_item_data)  # 更新树节点数据
        if not is_checked and key == "is_active":
            item.setDisabled(True)  # 设置禁用
        elif is_checked and key == "is_active":
            item.setDisabled(False)  # 取消禁用

    def update_int_attribute(self, item_data, key, value, item):
        """
        更新整数属性的值，当 QSpinBox 值改变时触发
        """
        params = item_data.get('params', {})  # 获取参数字典
        params[key] = value
        self.node_changed_signal.emit()
        print(f"(update_int_attribute) - 更新整数属性 {key} 为 {params[key]}")

        self.current_item_data['params'] = params  # 更新参数字典

        # 判断 key 是否为 count
        if key == "count":
            # 更新树节点文本
            if item.childCount() > 0 and item.child(0).text(0).startswith("重复"):
                item.child(0).setText(0, f"重复 {value} 次")
        # 判断 key 是否为 scroll_units
        elif key == "scroll_units":
            # 更新树节点文本
            old_text = item.text(0)
            if "(" in old_text and ")" in old_text:
                new_name = f"{old_text.split('(')[0]}({value})"
                item.setText(0, new_name)
                self.current_item_data['params']['name'] = new_name
            else:
                new_name = f"{old_text}({value})"
                item.setText(0, new_name)
                self.current_item_data['params']['name'] = new_name
        item.setData(0, Qt.UserRole, self.current_item_data)

    def update_double_attribute(self, item_data, key, value, item):
        """
        更新浮点数属性的值，当 QDoubleSpinBox 值改变时触发
        """
        params = item_data.get('params', {})  # 获取参数字典
        params[key] = value
        self.node_changed_signal.emit()
        print(f"(update_double_attribute) - 更新浮点数属性 {key} 为 {value}")

        self.current_item_data['params'] = params  # 更新参数字典
        # 判断 key 是否为 delay_time, 更新树节点文本
        if key == "delay_time":
            if item.text(0).startswith("等待"):
                name = f"等待 {value:.2f} 秒"
                item.setText(0, name)
                self.current_item_data['params']['name'] = name  # 同步更新树节点参数 “name” 的值
                item.setData(0, Qt.UserRole, self.current_item_data)

    def update_pos_attribute(self, item_data, key, value, item):
        """
        更新坐标位置属性的值，当 PositionXY 值改变时触发。
        """
        params = item_data.get('params', {})  # 获取参数字典
        params[key] = value
        self.node_changed_signal.emit()
        print(f"(update_pos_attribute) - 更新坐标位置属性 {key} 为 {params[key]}")

        self.current_item_data['params'] = params  # 更新参数字典
        # 更新树节点文本
        old_text = item.text(0)
        if "(" in old_text and ")" in old_text:
            new_name = f"{old_text.split('(')[0]}({value[0]},{value[1]})"
            item.setText(0, new_name)
            self.current_item_data['params']['name'] = new_name
        else:
            new_name = f"{old_text}({value[0]},{value[1]})"
            item.setText(0, new_name)
            self.current_item_data['params']['name'] = new_name
        item.setData(0, Qt.UserRole, self.current_item_data)

    def update_button_attribute(self, item_data, key, value, item):
        """
        更新按钮 button 的属性值，当 QComboBox 值改变时触发
        """
        params = item_data.get('params', {})  # 获取参数字典
        params[key] = value
        self.node_changed_signal.emit()
        print(f"(update_button_attribute) - 更新按钮属性 {key} 为 {params[key]}")

        self.current_item_data['params'] = params  # 更新参数字典
        # 更新树节点文本
        button_map = {
            "left": "左键",
            "right": "右键",
            "middle": "中键"
        }
        old_text = item.text(0)
        text = old_text
        if "左键" in old_text:
            text = old_text.replace("左键", button_map.get(value))
        elif "右键" in old_text:
            text = old_text.replace("右键", button_map.get(value))
        elif "中键" in old_text:
            text = old_text.replace("中键", button_map.get(value))

        item.setText(0, text)
        item.setData(0, Qt.UserRole, self.current_item_data)

    def update_match_mode_attribute(self, item_data, key, value, item):
        """
        更新文字识别匹配模式 match_mode 的属性值，当 QComboBox 值改变时触发
        """
        params = item_data.get('params', {})  # 获取参数字典
        params[key] = value
        self.node_changed_signal.emit()
        print(f"(update_match_mode_attribute) - 更新匹配模式属性 {key} 为 {value}")

        self.current_item_data['params'] = params  # 更新参数字典

    def update_key_attribute(self, item_data, key, value, item):
        """
        更新键盘按键属性值
        """
        params = item_data.get('params', {})  # 获取参数字典
        params[key] = value
        self.node_changed_signal.emit()
        print(f"(update_key_attribute) - 更新属性 {key} 为 {params[key]}")

        self.current_item_data['params'] = params  # 更新参数字典
        # 更新树节点文本
        old_text = item.text(0)
        if "-" in old_text:
            new_name = old_text.split("-")[0] + "-" + value
            item.setText(0, new_name)
            self.current_item_data['params']['name'] = new_name
        else:
            new_name = old_text + "-" + value
            item.setText(0, new_name)
            self.current_item_data['params']['name'] = new_name
        item.setData(0, Qt.UserRole, self.current_item_data)

    def update_hotkey_attribute(self, item_data, key, value, item):
        """
        更新热键属性值
        """
        params = item_data.get('params', {})  # 获取参数字典
        params[key] = value.replace(" ", "").split("+") if value else []
        self.node_changed_signal.emit()
        print(f"(update_hotkey_attribute) - 更新属性 {key} 为 {params[key]}")

        self.current_item_data['params'] = params  # 更新参数字典
        # 更新树节点文本
        old_text = item.text(0)
        if "(" in old_text and ")" in old_text:
            new_name = old_text.split("(")[0] + f"({value})"
            item.setText(0, new_name)
            self.current_item_data['params']['name'] = new_name
        else:
            new_name = old_text + f"({value})"
            item.setText(0, new_name)
            self.current_item_data['params']['name'] = new_name
        item.setData(0, Qt.UserRole, self.current_item_data)

    # ==================================== 导出任务到当前 JSON ==================================== #

    def save_to_json(self, json_path: str = None):
        """
        遍历指令编辑器并保存到 JSON 文件
        :param json_path: 保存的目标 JSON 文件路径，如果未指定则使用当前路径。
        """
        if not json_path:
            json_path = self.current_json_path

        print(f"(save_to_json) - 开始保存到文件：{json_path}")

        # 获取文件名（不含扩展名）作为 task_name
        task_name = os.path.splitext(os.path.basename(json_path))[0]

        # 构建 JSON 数据
        task_data = {
            "task_name": task_name,
            "steps": self._extract_steps_from_tree()
        }

        # 保存到文件
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(task_data, f, ensure_ascii=False, indent=4)
                json_name = os.path.basename(json_path)
            QMessageBox.information(self.treeWidget, "成功", f"当前任务已保存到文件：'{json_name}' 中", QMessageBox.Ok)
            self.is_save = True
        except Exception as e:
            self.is_save = False
            QMessageBox.critical(self.treeWidget, "错误", f"保存失败：\n{e}")

    def _extract_steps_from_tree(self) -> list:
        """
        从树形控件中提取指令步骤列表
        :return: steps[] - 包含所有步骤的列表
        """
        steps = []
        for i in range(self.treeWidget.topLevelItemCount()):
            top_item = self.treeWidget.topLevelItem(i)
            step_data = self._extract_node_data(top_item)
            steps.append(step_data)
        return steps

    def _extract_node_data(self, item: QTreeWidgetItem) -> dict:
        """
        递归提取节点数据，包括子节点
        :param item: 当前指令树节点
        :return: 当前节点及子节点的数据
        """
        # 获取指令节点数据
        node_data = item.data(0, Qt.UserRole)
        if not node_data:
            return {}

        # 提取基础数据
        result = {
            "type": node_data.get("type"),
            "action": node_data.get("action"),
            "icon": node_data.get("icon"),
            "params": node_data.get("params", {})
        }

        # 如果是流程控制类型，递归提取子指令
        if result["type"] == "flow":
            if result["action"] == "if":
                # 提取 then_commands 和 else_commands
                then_item = item.child(0) if item.childCount() > 0 and item.child(0).text(0) == "成立" else None
                else_item = item.child(1) if item.childCount() > 1 and item.child(1).text(0) == "不成立" else None

                result["params"]["then_commands"] = [
                    self._extract_node_data(then_item.child(i))
                    for i in range(then_item.childCount())
                ] if then_item else []

                result["params"]["else_commands"] = [
                    self._extract_node_data(else_item.child(i))
                    for i in range(else_item.childCount())
                ] if else_item else []

            elif result["action"] == "loop":
                # 提取 loop_commands
                loop_item = item.child(0) if item.childCount() > 0 else None
                result["params"]["loop_commands"] = [
                    self._extract_node_data(loop_item.child(i))
                    for i in range(loop_item.childCount())
                ] if loop_item else []

        # 如果是子任务，直接记录子任务文件路径
        elif result["type"] == "subtask":
            result["params"]["subtask_file"] = node_data["params"].get("subtask_file")

        return result
