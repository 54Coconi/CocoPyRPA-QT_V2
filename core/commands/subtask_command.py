"""
@author: 54Coconi
@date: 2024-11-22
@version: 1.0.0
@path: core/commands/subtask_command.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    用于执行子任务的指令模块
"""
from pathlib import Path
from typing import List
from pydantic import Field


from .base_command import BaseCommand


class SubtaskCommand(BaseCommand):
    """  子任务指令类
    通过子任务文件路径加载子任务
    """
    name: str = Field("<子任务>", description="指令名称")
    is_active: bool = Field(True, description="指令是否启用")

    subtask_file: Path = Field(..., description="子任务文件路径")

    _subtask_steps: List[BaseCommand] = []  # 子任务步骤对象,私有属性

    def execute(self, **kwargs):
        pass

    # 获取私有属性子任务步骤
    @property
    def subtask_steps(self):
        """子任务步骤"""
        return self._subtask_steps

    # 设置私有属性子任务步骤
    @subtask_steps.setter
    def subtask_steps(self, value):
        self._subtask_steps = value
