"""
指令执行结果管理器模块

该模块提供了一个专门用于管理自动化指令执行结果的类，
支持添加、查询、更新和删除指令执行结果等功能。
"""

import json
from collections import OrderedDict
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional


@dataclass
class CommandResult:
    """
    单个指令执行结果类
    
    用于封装单个指令的执行结果信息，包括指令ID、名称和执行数据等。

    Attributes:
        command_id (str): 指令ID
        command_name (str): 指令名称
        result_data (Dict[str, Any]): 指令执行结果数据
        timestamp (str, optional): 指令执行时间戳
    """
    command_id: str
    command_name: str
    result_data: Dict[str, Any]
    timestamp: str = ""

    def __post_init__(self):
        """初始化后处理，设置 timestamp"""
        if not self.timestamp:
            self.timestamp = self.result_data.get("timestamp", "")

    def get_field(self, field_name: str) -> Any:
        """
        获取结果中的特定字段值
        
        Args:
            field_name (str): 字段名
            
        Returns:
            Any: 字段值，如果字段不存在则返回None
        """
        return self.result_data.get(field_name)

    def to_dict(self) -> Dict[str, Any]:
        """
        将指令执行结果转换为字典格式
        
        Returns:
            Dict[str, Any]: 包含指令执行结果信息的字典
        """
        return asdict(self)

    def __repr__(self):
        return f"CommandResult(id={self.command_id}, name={self.command_name})"


class CommandResultManager:
    """
    指令执行结果管理器
    
    用于管理所有指令的执行结果，支持添加、查询、更新和删除操作，
    并提供结果历史记录功能以支持重复ID的指令跟踪。
    """

    def __init__(self):
        """初始化指令执行结果管理器"""
        # 使用 OrderedDict 保持插入顺序，同时支持通过 ID 快速访问
        self._results: OrderedDict[str, CommandResult] = OrderedDict()
        # 用于存储每个命令ID的执行历史（支持重复ID的命令）
        self._result_history: Dict[str, List[CommandResult]] = {}

    def add_result(self, command_id: str, command_name: str, result_data: Dict[str, Any]) -> None:
        """
        添加指令执行结果
        
        Args:
            command_id (str): 指令ID
            command_name (str): 指令名称
            result_data (Dict[str, Any]): 指令执行结果数据
        """
        result = CommandResult(command_id, command_name, result_data)
        
        # 添加到有序字典中（保留最新结果）
        self._results[command_id] = result
        
        # 添加到历史记录中
        if command_id not in self._result_history:
            self._result_history[command_id] = []
        self._result_history[command_id].append(result)

    def get_result(self, command_id: str) -> Optional[CommandResult]:
        """
        根据指令 ID 获取最新的执行结果
        
        Args:
            command_id (str): 指令 ID
            
        Returns:
            Optional[CommandResult]: 指令执行结果，如果不存在则返回 None
        """
        return self._results.get(command_id)

    def get_result_by_index(self, command_id: str, index: int = -1) -> Optional[CommandResult]:
        """
        根据指令 ID 和索引获取执行结果
        
        Args:
            command_id (str): 指令ID
            index (int): 索引，默认-1表示最新的结果
            
        Returns:
            Optional[CommandResult]: 指令执行结果，如果不存在则返回 None
        """
        if command_id in self._result_history:
            history = self._result_history[command_id]
            if history:
                try:
                    return history[index]
                except IndexError:
                    pass
        return None

    def get_all_results(self) -> List[CommandResult]:
        """
        获取所有指令执行结果
        
        Returns:
            List[CommandResult]: 所有指令执行结果列表
        """
        return list(self._results.values())

    def get_results_as_dicts(self) -> List[Dict[str, Any]]:
        """
        获取所有指令执行结果的字典形式（与原来的 results_list 兼容）
        
        Returns:
            List[Dict[str, Any]]: 指令执行结果字典列表
        """
        return [result.result_data for result in self._results.values()]

    def get_results_by_name(self, command_name: str) -> List[CommandResult]:
        """
        根据指令名称获取执行结果列表
        
        Args:
            command_name (str): 指令名称
            
        Returns:
            List[CommandResult]: 匹配名称的指令执行结果列表
        """
        return [result for result in self._results.values() if result.command_name == command_name]

    def clear(self) -> None:
        """清空所有结果"""
        self._results.clear()
        self._result_history.clear()

    def remove_result(self, command_id: str) -> bool:
        """
        移除指定指令ID的结果
        
        Args:
            command_id (str): 指令ID
            
        Returns:
            bool: 是否成功移除
        """
        if command_id in self._results:
            del self._results[command_id]
            if command_id in self._result_history:
                del self._result_history[command_id]
            return True
        return False

    def get_result_count(self) -> int:
        """
        获取结果总数
        
        Returns:
            int: 结果总数
        """
        return len(self._results)

    def has_result(self, command_id: str) -> bool:
        """
        检查是否存在指定 ID 的指令结果
        
        Args:
            command_id (str): 指令 ID
            
        Returns:
            bool: 如果存在返回 True，否则返回 False
        """
        return command_id in self._results

    def get_history_count(self, command_id: str) -> int:
        """
        获取指定指令 ID 的历史记录数量
        
        Args:
            command_id (str): 指令 ID
            
        Returns:
            int: 历史记录数量，如果指令 ID 不存在则返回 0
        """
        if command_id in self._result_history:
            return len(self._result_history[command_id])
        return 0

    def to_json(self) -> str:
        """
        将所有结果转换为 JSON 字符串
        
        Returns:
            str: JSON 格式的结果数据
        """
        results_data = [result.to_dict() for result in self._results.values()]
        return json.dumps(results_data, ensure_ascii=False, indent=4)

    def __len__(self) -> int:
        return len(self._results)

    def __contains__(self, command_id: str) -> bool:
        return command_id in self._results

    def __iter__(self):
        return iter(self._results.values())