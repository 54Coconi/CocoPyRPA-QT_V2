"""
@author: 54Coconi
@date: 2025-07-29
@version: 2.0.0

键盘录制器模块

主要功能:
    - 提供键盘记录和回放功能
    - 支持记录和解析键盘操作
    - 提供图形界面组件

主要组件:
    - Controller: 控制器
    - RecorderWidget: 键盘记录器主界面组件
    - KeyboardListener: 键盘事件监听器
    - operation_parser: 操作解析器
    - tree_build_api: 树形结构构建API
"""

from .core import Controller, KeyboardListener
from .operation_parser import parse_operation_history, operation_history_to_text
from .tree_build_api import create_tree_item
from .ui import RecorderWidget

__all__ = [
    'Controller',
    'RecorderWidget',
    'KeyboardListener',
    'parse_operation_history',
    'operation_history_to_text',
    'create_tree_item'
]
