"""
@author: 54Coconi
@date: 2025-07-05
@version: 2.0.0

鼠标录制器模块

提供鼠标录制功能的核心类和 UI 组件

主要功能：
    - 录制鼠标移动、点击、滚轮等操作
    - 实时显示鼠标位置和 RGB 颜色值
    - 生成可重放的指令序列

主要组件:
    - MouseRecorderCore: 鼠标录制器核心类
    - MouseRecorderWindow: 鼠标录制器 UI

"""


from ..mouse_recorder.core import MouseRecorderCore, DEFAULT_RECORD_KEY, DEFAULT_EXIT_KEY
from ..mouse_recorder.ui import MouseRecorderWindow


__all__ = [
    'MouseRecorderCore',
    'MouseRecorderWindow',
    'DEFAULT_RECORD_KEY',
    'DEFAULT_EXIT_KEY',
]
