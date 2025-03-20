"""
@author: 54Coconi
@date: 2024-11-16
@version: 1.0.0
@path: core/commands/flow_commands.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    流程控制类指令模块
"""
import time

from pydantic import Field

from core.commands.base_command import BaseCommand, STATUS_RUNNING, STATUS_COMPLETED


# @ <延时> 指令
class DelayCmd(BaseCommand):
    """
    <延时> 指令
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否启用

        delay_time:(float | int): 延时时间，默认为 0.0 秒
    """
    name: str = Field("延时", description="指令名称")
    is_active: bool = Field(True, description="指令是否启用")

    delay_time: float | int = Field(0.0, description="延时时间")

    def execute(self, **kwargs):
        print(f"[INFO] - (DelayCmd) 正在执行指令 🚀{self.name}🚀 ")
        print(f"[INFO] - (DelayCmd) 延时时间为 {self.delay_time}s ")
        self.set_status(STATUS_RUNNING)
        time.sleep(self.delay_time)
        self.set_status(STATUS_COMPLETED)
        print(f"[INFO] - 指令 {self.name} 🎉执行成功🎉")
        print("-" * 100 + "")


# @ <If 判断> 指令
class IfCommand(BaseCommand):
    """
    <If 判断> 指令
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否启用

        condition:(str): 判断条件
        then_commands: (List[:class:`BaseCommand`]): 满足条件时执行的指令对象列表
        else_commands: (List[:class:`BaseCommand`]): 不满足条件时执行的指令对象列表
    """
    name: str = Field("If 判断", description="指令名称")
    is_active: bool = Field(True, description="指令是否启用")

    condition: str = Field(..., description="判断条件")
    then_commands: list = Field([], description="满足条件时执行的指令对象列表")
    else_commands: list = Field([], description="不满足条件时执行的指令对象列表")

    def execute(self, **kwargs):
        self.set_status(STATUS_COMPLETED)  # 设置指令状态为已完成
        pass


# @ <While 循环> 指令
class LoopCommand(BaseCommand):
    """
    <Loop 循环> 指令
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否启用

        count:(int): 循环次数
        loop_commands: (List[:class:`BaseCommand`]): 需要重复执行的指令对象列表
    """
    name: str = Field("Loop 循环", description="指令名称")
    is_active: bool = Field(True, description="指令是否启用")

    count: int = Field(0, description="循环次数")
    loop_commands: list = Field([], description="需要重复执行的指令对象列表")

    def execute(self, **kwargs):
        self.set_status(STATUS_COMPLETED)  # 设置指令状态为已完成
        pass
