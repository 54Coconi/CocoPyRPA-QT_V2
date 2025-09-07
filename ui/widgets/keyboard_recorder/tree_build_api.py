"""
@Author: 54Coconi
@version: 1.0.0
@description:
    用于根据键盘录制器的记录创建树节点的 API
"""
from collections import OrderedDict

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QTreeWidgetItem, QTreeWidget

from core.register import registry


def create_tree_item(widget: QTreeWidget, record: dict):
    """ 创建树节点
    :param widget: QTreeWidget 控件
    :param record: 单个操作记录
    :return: None
    """
    if record.get("type") == "keyboard":
        if record.get("action") == "keyPress":
            item = create_keyPress_command(record)
            widget.addTopLevelItem(item)
            registry.register_command(item)
        elif record.get("action") == "keyRelease":
            item = create_keyRelease_command(record)
            widget.addTopLevelItem(item)
            registry.register_command(item)
    elif record.get("type") == "flow":
        if record.get("action") == "delay":
            item = create_delay_command(record)
            widget.addTopLevelItem(item)
            registry.register_command(item)


# 键盘按下
def create_keyPress_command(record: dict) -> QTreeWidgetItem:
    """ 创建键盘按下指令
    :param record: 单个操作记录
    :return: QTreeWidgetItem 节点
    """
    key = record.get("key")
    item_name = f"键盘按下-{str(key)}"
    # 构建节点数据
    item_data = {
        "type": "keyboard",
        "action": "keyPress",
        "icon": ":/icons/key-press",
        "params": {
            "name": item_name,
            "key": str(key),
            "retries": 0,
            "is_active": True,
            "use_pynput": False,
            "status": 0
        }
    }
    # 使用 OrderedDict 创建有序字典
    item_data = OrderedDict(item_data)
    item = QTreeWidgetItem([item_name])  # 创建节点
    item.setData(0, Qt.UserRole, item_data)  # 设置数据
    item.setIcon(0, QIcon(":/icons/key-press"))  # 设置图标
    item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
    return item


# 键盘释放
def create_keyRelease_command(record: dict) -> QTreeWidgetItem:
    """创建键盘释放指令
    :param record: 单个操作记录
    :return: QTreeWidgetItem 节点
    """
    key = record.get("key")
    item_name = f"键盘释放-{str(key)}"
    # 构建节点数据
    item_data = {
        "type": "keyboard",
        "action": "keyRelease",
        "icon": ":/icons/key-release",
        "params": {
            "name": item_name,
            "key": str(key),
            "retries": 0,
            "is_active": True,
            "use_pynput": False,
            "status": 0
        }
    }
    # 使用 OrderedDict 创建有序字典
    item_data = OrderedDict(item_data)
    item = QTreeWidgetItem([item_name])  # 创建节点
    item.setData(0, Qt.UserRole, item_data)  # 设置数据
    item.setIcon(0, QIcon(":/icons/key-release"))  # 设置图标
    item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
    return item


# 延时
def create_delay_command(record: dict) -> QTreeWidgetItem:
    """创建延时指令
    :param record: 单个操作记录
    :return: QTreeWidgetItem 节点
    """
    delay_time = record.get("delay_time")
    item_name = f"等待 {delay_time:.2f} 秒"
    # 构建节点数据
    item_data = {
        "type": "flow",
        "action": "delay",
        "icon": ":/icons/delay",
        "params": {
            "name": item_name,
            "delay_time": float(delay_time),
            "is_active": True,
            "status": 0
        }
    }
    # 使用 OrderedDict 创建有序字典
    item_data = OrderedDict(item_data)
    item = QTreeWidgetItem([item_name])  # 创建节点
    item.setData(0, Qt.UserRole, item_data)  # 设置数据
    item.setIcon(0, QIcon(":/icons/delay"))  # 设置图标
    item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
    return item
