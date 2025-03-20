"""
@author: 54Coconi
@date: 2024-11-13
@version: 1.0.0
@path: /core/commands/system_commands.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    系统控制指令模块
"""
import time

from pydantic import Field

from utils.debug import print_func_time
from .base_command import BaseCommand, CommandRunningException

_DEBUG = True



