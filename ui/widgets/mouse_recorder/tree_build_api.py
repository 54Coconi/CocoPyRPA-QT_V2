"""
@Author: 54Coconi
@version: 1.0.0
@description:
    用于根据鼠标录制器的记录创建树节点的API
"""


from collections import OrderedDict

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QTreeWidgetItem, QTreeWidget

from core.register import registry


def create_tree_item(widget: QTreeWidget, record: dict):
    """创建树节点
    :param widget: QTreeWidget 树控件
    :param record: 操作记录字典
    """
    action_zh = record.get('action_zh')
    # 处理鼠标移动操作
    if action_zh == "定点移动":
        target_pos = record.get('target_pos')
        item = create_moveTo_command(target_pos)
        widget.addTopLevelItem(item)
        registry.register_command(item)
    # 处理鼠标点击操作
    elif action_zh in ["左键单击", "左键双击"]:
        item = create_click_left_command(record)
        widget.addTopLevelItem(item)
        registry.register_command(item)
    elif action_zh == "中键点击":
        item = create_click_middle_command(record)
        widget.addTopLevelItem(item)
        registry.register_command(item)
    elif action_zh == "右键单击":
        item = create_click_right_command(record)
        widget.addTopLevelItem(item)
        registry.register_command(item)
    # 处理鼠标滚轮操作，'scroll' 是一个元组(0,1)或(0,-1)，第一个元素是横向滚动，第二个元素是纵向滚动,正负表示方向
    elif action_zh == "竖直滚动":
        target_pos = record.get('target_pos')
        item1 = create_moveTo_command(target_pos)
        item2 = create_scrollV_command(record)
        widget.addTopLevelItem(item1)
        widget.addTopLevelItem(item2)
        registry.register_command(item1)
        registry.register_command(item2)
    # 处理鼠标拖动操作(鼠标从起点拖动到终点，所以鼠标应该先定点移动到起点，再拖动到终点)
    elif action_zh == "左键拖动":
        start_pos = record.get('start_pos')
        item1 = create_moveTo_command(start_pos)
        item2 = create_dragTo_command(record)
        widget.addTopLevelItem(item1)
        widget.addTopLevelItem(item2)
        registry.register_command(item1)
        registry.register_command(item2)
    else:  # 其他操作
        pass


def create_moveTo_command(target_pos: tuple[int, int]) -> QTreeWidgetItem:
    """
    创建 <鼠标定点移动> 指令
    :param target_pos: 目标坐标
    """
    item_name = "鼠标定点移动" + f"{str(target_pos)}"
    item_data = {
        "type": "mouse",
        "action": "moveTo",
        "icon": ":/icons/mouse-move",
        "params": {
            "name": item_name,
            "target_pos": target_pos,
            "duration": 1.0,
            "retries": 0,
            "is_active": True,
            "use_pynput": True,
            "status": 0
        }
    }
    # 使用 OrderedDict 创建有序字典
    item_data = OrderedDict(item_data)
    item = QTreeWidgetItem([item_name])  # 创建节点
    item.setData(0, Qt.UserRole, item_data)  # 设置数据
    item.setIcon(0, QIcon(":/icons/mouse-move"))  # 设置图标
    item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
    return item


def create_click_left_command(record: dict) -> QTreeWidgetItem:
    """
    创建 <鼠标左键点击> 指令
    :param record:
    """
    target_pos = record.get('target_pos')
    item_name = "鼠标左键点击" + f"{str(target_pos)}"
    item_data = {
        "type": "mouse",
        "action": "click",
        "icon": ":/icons/mouse-click-left",
        "params": {
            "name": item_name,
            "target_pos": target_pos,
            "clicks": int(record.get('clicks')),
            "interval": 0.2,
            "duration": 1.0,
            "retries": 0,
            "button": "left",
            "is_active": True,
            "use_pynput": True,
            "status": 0
        }
    }
    # 使用 OrderedDict 创建有序字典
    item_data = OrderedDict(item_data)
    item = QTreeWidgetItem([item_name])  # 创建节点
    item.setData(0, Qt.UserRole, item_data)  # 设置数据
    item.setIcon(0, QIcon(":/icons/mouse-click-left"))  # 设置图标
    item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
    return item


def create_click_right_command(record: dict) -> QTreeWidgetItem:
    """
    创建 <鼠标右键点击> 指令
    :param record:
    """
    target_pos = record.get('target_pos')
    item_name = "鼠标右键点击" + f"{str(target_pos)}"
    item_data = {
        "type": "mouse",
        "action": "click",
        "icon": ":/icons/mouse-click-right",
        "params": {
            "name": item_name,
            "target_pos": target_pos,
            "clicks": int(record.get('clicks')),
            "interval": 0.2,
            "duration": 1.0,
            "retries": 0,
            "button": "right",
            "is_active": True,
            "use_pynput": True,
            "status": 0
        }
    }
    # 使用 OrderedDict 创建有序字典
    item_data = OrderedDict(item_data)
    item = QTreeWidgetItem([item_name])  # 创建节点
    item.setData(0, Qt.UserRole, item_data)  # 设置数据
    item.setIcon(0, QIcon(":/icons/mouse-click-right"))  # 设置图标
    item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
    return item


def create_click_middle_command(record: dict) -> QTreeWidgetItem:
    """
    创建 <鼠标中键点击> 指令
    :param record:
    """
    target_pos = record.get('target_pos')
    item_name = "鼠标中键点击" + f"{str(target_pos)}"
    item_data = {
        "type": "mouse",
        "action": "click",
        "icon": ":/icons/mouse-click-middle",
        "params": {
            "name": item_name,
            "target_pos": target_pos,
            "clicks": int(record.get('clicks')),
            "interval": 0.2,
            "duration": 1.0,
            "retries": 0,
            "button": "middle",
            "is_active": True,
            "use_pynput": True,
            "status": 0
        }
    }
    # 使用 OrderedDict 创建有序字典
    item_data = OrderedDict(item_data)
    item = QTreeWidgetItem([item_name])  # 创建节点
    item.setData(0, Qt.UserRole, item_data)  # 设置数据
    item.setIcon(0, QIcon(":/icons/mouse-click-middle"))  # 设置图标
    item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
    return item


def create_scrollV_command(record: dict) -> QTreeWidgetItem:
    """
    创建 <鼠标竖直滚动> 指令
    :param record:
    """
    target_pos = record.get('target_pos')
    scroll_units = record.get('scroll')[1]  # 有正负
    item_name = "鼠标竖直滚动" + f"{str()}"
    item_data = {
        "type": "mouse",
        "action": "scrollV",
        "icon": ":/icons/wheel-v",
        "params": {
            "name": item_name,
            "scroll_units": scroll_units,
            "retries": 0,
            "is_active": True,
            "use_pynput": True,
            "status": 0
        }
    }
    # 使用 OrderedDict 创建有序字典
    item_data = OrderedDict(item_data)
    item = QTreeWidgetItem([item_name])  # 创建节点
    item.setData(0, Qt.UserRole, item_data)  # 设置数据
    item.setIcon(0, QIcon(":/icons/wheel-v"))  # 设置图标
    item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
    return item


def create_dragTo_command(record: dict) -> QTreeWidgetItem:
    """
    创建 <鼠标定点拖动> 指令
    :param record:
    """
    target_pos = record.get('target_pos')
    item_name = "鼠标定点拖动" + f"{str(target_pos)}"
    item_data = {
        "type": "mouse",
        "action": "dragTo",
        "icon": ":/icons/mouse-drag",
        "params": {
            "name": item_name,
            "target_pos": target_pos,
            "duration": record.get('duration'),
            "retries": 0,
            "button": "left",
            "is_active": True,
            "use_pynput": True,
            "status": 0
        }
    }
    # 使用 OrderedDict 创建有序字典
    item_data = OrderedDict(item_data)
    item = QTreeWidgetItem([item_name])  # 创建节点
    item.setData(0, Qt.UserRole, item_data)  # 设置数据
    item.setIcon(0, QIcon(":/icons/mouse-drag"))  # 设置图标
    item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled | Qt.ItemIsDragEnabled)  # 设置标志
    return item
