"""
@author: 54Coconi
@date: 2024-12-2
@version: 1.0.0
@path:
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    - CocoPyRPA_v2.0.0 - 指令注册模块
"""

import uuid
import json
import time
import os.path
from typing import Dict, Optional
from dataclasses import dataclass
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidgetItem


MAX_RECORDS = 1000  # 最大记录数


# 指令记录数据类
@dataclass
class CommandRecord:
    """
    指令记录数据类
    """
    cmd_id: str  # 指令唯一标识
    cmd_type: str  # 指令类型
    cmd_action: str  # 指令动作
    cmd_name: str  # 指令名称
    created_time: float  # 创建时间
    parent_id: Optional[str] = None  # 父节点ID
    attributes: Dict = None  # 指令属性


# 指令ID生成器
class CommandIDGenerator:
    """
    指令ID生成器
    """
    @staticmethod
    def generate_id() -> str:
        """
        生成一个唯一的指令ID
        :return: 指令ID
        """
        # 生成一个唯一的短ID，通过将UUID转换为Base64字符串，然后截取前八位作为短ID
        return format(uuid.uuid4().int, 'x')[:8]

    @staticmethod
    def generate_timestamp() -> float:
        """
        生成一个唯一的时间戳
        :return: 时间戳
        """
        # 生成当前时间戳
        return time.time()


# 指令持久化管理
class CommandPersistence:
    """
    指令持久化管理
    """
    def __init__(self, storage_path: str):
        self.storage_path = storage_path  # 存储路径

    def save_records(self, records: Dict[str, CommandRecord]):
        """
        保存指令记录到文件
        :param records: 指令记录
        """
        data = {}
        for cmd_id, record in records.items():
            formatted_time = self.format_time(record.created_time)  # 格式化时间
            data[cmd_id] = {
                "cmd_type": record.cmd_type,
                "cmd_action": record.cmd_action,
                "cmd_name": record.cmd_name,
                "created_time": formatted_time,  # 保存格式化后的时间
                "parent_id": record.parent_id,
                "attributes": record.attributes
            }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)  # 保存为JSON文件

    def load_records(self) -> Dict[str, CommandRecord]:
        """
        加载指令记录
        :return:
        """
        # 从文件加载指令记录
        if not os.path.exists(self.storage_path):
            return {}
        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = {}
        for cmd_id, info in data.items():
            created_time = self.parse_time(info["created_time"])  # 解析时间
            if created_time is not None:
                records[cmd_id] = CommandRecord(
                    cmd_id=cmd_id,
                    cmd_type=info["cmd_type"],
                    cmd_action=info["cmd_action"],
                    cmd_name=info["cmd_name"],
                    created_time=created_time,
                    parent_id=info["parent_id"],
                    attributes=info["attributes"]
                )
        return records

    @staticmethod
    def format_time(timestamp):
        """
        格式化时间戳为字符串
        :param timestamp: 时间戳
        :return: 格式化后的时间字符串
        """
        # 将时间戳格式化为xxxx-xx-xx-xx:xx:xx:xxx:xxx字符串，精确到微秒
        dt = datetime.datetime.fromtimestamp(timestamp)
        microsecond = dt.microsecond
        return dt.strftime("%Y-%m-%d-%H:%M:%S") + f":{microsecond:06d}"

    @staticmethod
    def parse_time(time_str):
        """
        解析时间字符串为时间戳
        :param time_str: 时间字符串
        :return: 时间戳
        """
        # 将xxxx-xx-xx-xx:xx:xx:xxx:xxx字符串解析为浮点数时间戳
        try:
            parts = time_str.split(":")
            if len(parts) != 6:
                return None
            date_parts = parts[:4]
            seconds = parts[4]
            microseconds = parts[5]
            dt_str = "-".join(date_parts) + ":" + seconds
            dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d-%H:%M:%S")
            timestamp = dt.timestamp() + int(microseconds) / 1e6
            return timestamp
        except ValueError:
            return None


# 指令节点装饰器
class CommandDecorator:
    """
    指令节点装饰器
    """
    def __init__(self, tree_item: QTreeWidgetItem, cmd_record: CommandRecord):
        self.tree_item = tree_item
        self.cmd_record = cmd_record

    def decorate(self):
        """
        装饰树节点
        """
        # 装饰树节点，添加指令信息
        user_data = self.tree_item.data(0, Qt.UserRole) or {}
        user_data["cmd_id"] = self.cmd_record.cmd_id
        self.tree_item.setData(0, Qt.UserRole, user_data)


# 指令注册管理器
class CommandRegistry:
    """
    指令注册管理器
    """
    def __init__(self, storage_path: str):
        self.id_generator = CommandIDGenerator()  # ID生成器
        self.persistence = CommandPersistence(storage_path)  # 持久化
        self.records = self.persistence.load_records()  # 指令记录

    def register_command(self, tree_item: QTreeWidgetItem) -> str:
        """
        注册指令
        :param tree_item: 指令节点
        :return: 指令ID
        """
        # 如果记录数量超过1000，删除最早的指令
        if len(self.records) >= MAX_RECORDS:
            min_time = float('inf')   # 最小时间戳
            oldest_cmd_id = None
            for cmd_id, record in self.records.items():
                if record.created_time < min_time:
                    min_time = record.created_time
                    oldest_cmd_id = cmd_id
            if oldest_cmd_id:
                del self.records[oldest_cmd_id]

        cmd_id = self.id_generator.generate_id()  # 生成新的指令ID
        item_data = tree_item.data(0, Qt.UserRole) or {}   # 获取节点数据
        params = item_data.get("params", {})   # 获取参数
        params["id"] = cmd_id   # 添加指令ID
        item_data["params"] = params   # 更新参数
        tree_item.setData(0, Qt.UserRole, item_data)   # 更新节点数据

        record = CommandRecord(
            cmd_id=cmd_id,
            cmd_type=item_data.get("type", "unknown"),
            cmd_action=item_data.get("action", "unknown"),
            cmd_name=tree_item.text(0),
            created_time=self.id_generator.generate_timestamp(),
            parent_id=None,
            attributes=params
        )

        self.records[cmd_id] = record
        self.persistence.save_records(self.records)

        return cmd_id

    def unregister_command(self, tree_item: QTreeWidgetItem):
        """
        注销指令
        :param tree_item:
        """
        item_data = tree_item.data(0, Qt.UserRole) or {}
        params = item_data.get('params', {})
        cmd_id = params.get('id')
        # 注销指令
        if cmd_id in self.records:
            del self.records[cmd_id]
            self.persistence.save_records(self.records)

    def get_command(self, cmd_id: str) -> Optional[CommandRecord]:
        """
        获取指令记录
        :param cmd_id:
        :return: 指令记录
        """
        return self.records.get(cmd_id)

    def update_command(self, cmd_id: str, **kwargs):
        """
        更新指令记录
        :param cmd_id: 指令ID
        :param kwargs: 更新的属性
        """
        if cmd_id in self.records:
            record = self.records[cmd_id]
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            self.persistence.save_records(self.records)


registry = CommandRegistry("register.json")  # 全局指令注册管理器
