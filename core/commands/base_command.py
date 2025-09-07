"""
@author: 54Coconi
@date: 2024-11-10
@version: 1.0.1
@path: /core/commands/base_command.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    指令基类，包含所有指令的抽象基类，定义通用的指令属性和执行流程
"""

import time
import traceback
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QTreeWidgetItem
from pydantic import BaseModel, Field, field_validator

from config.app_config import info, error, warning

_DEBUG = False

# 指令状态常量
STATUS_PENDING = 0  # 未执行
STATUS_RUNNING = 1  # 执行中
STATUS_COMPLETED = 2  # 已完成
STATUS_FAILED = 3  # 失败


def _generate_short_id():
    """  生成一个唯一的短ID，通过将UUID转换为Base64字符串，然后截取前八位作为短ID """
    # 使用 UUID 的整数值并转换为 Base64 字符串，然后截取前八位作为短 ID，eg: '4d92f23b'
    return format(uuid.uuid4().int, 'x')[:8]


class CommandRunningException(Exception):
    """
    自定义异常类，用于在指令运行时捕获异常信息。
    当抛出该异常时，会自动包含异常发生的文件路径、行号。
    """

    def __init__(self, message="指令运行时发生异常"):
        super().__init__(message)
        # 获取当前异常发生的栈帧信息
        tb = traceback.extract_stack(limit=2)[-2]
        # 提取文件路径、行号和列号
        self.file_path = tb.filename
        self.line_number = tb.lineno
        # self.column_offset = tb.colno if tb.colno is not None else "未知"

    def __str__(self):
        """
        返回包含文件路径、行号和列号的详细异常信息。
        """
        if _DEBUG:
            return (f"{super().__str__()} \n"
                    f"错误发生在: {self.file_path}, 行: {self.line_number}")
        # _publish_command_status(super().__str__())
        return super().__str__()

    def __repr__(self):
        """
        为调试提供详细信息。
        """
        return self.__str__()


class CommandQObject(QObject):
    """ 指令的Qt对象容器 """
    status_changed = pyqtSignal(int)  # 状态变化信号
    error_message = pyqtSignal(str)  # 错误消息信号
    info_message = pyqtSignal(str)  # 信息消息信号


class BaseCommand(BaseModel, ABC):
    """
    :class:`BaseCommand` 是所有指令的抽象基类，定义通用的指令属性和执行流程，
    包含Qt对象的组合式实现
    Attributes:
        q_obj: (:class:`CommandQObject`): 指令的Qt对象
        id:(str): 指令id
        name:(str): 指令名称
        status:(int): 指令执行状态
        is_active:(bool): 指令是否启用
        tree_item: (:class:`QTreeWidgetItem`): 指令对应的树节点
    """
    # 指令的 Qt 对象，排除序列化
    q_obj: CommandQObject = Field(default_factory=CommandQObject, exclude=True)
    id: str = Field(default_factory=_generate_short_id, description="指令唯一ID")
    name: str = Field(..., description="指令名称")
    status: int = Field(STATUS_PENDING, description="指令执行状态")
    is_active: bool = Field(True, description="指令是否启用")
    # 指令对应的树节点
    tree_item: Optional[QTreeWidgetItem] = Field(None, description="指令对应的树节点")

    class Config:
        """ 配置pydantic，允许任意类型的属性 """
        arbitrary_types_allowed = True

    @classmethod
    @field_validator('status')
    def validate_status(cls, v):
        """ 验证指令状态 """
        if v not in {STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED}:
            raise ValueError("指令状态必须为0 (未执行)、1 (执行中)、2 (已完成)、3 (失败) 之一")
        return v

    @abstractmethod
    def execute(self, **kwargs):
        """
        执行指令的抽象方法，每个具体指令必须实现。
        """
        raise NotImplementedError("每个指令类必须实现 'execute' 方法")

    def set_status(self, new_status: int):
        """ 设置指令状态 """
        self.status = new_status
        self.q_obj.status_changed.emit(new_status)

    def __str__(self):
        """ 返回包含所有属性的字典格式字符串表示 """
        # 将属性字典格式化为多行字符串
        attributes_str = ",\n    ".join([f"{key}: {value!r}" for key, value in self.model_dump().items()])
        return f"{self.__class__.__name__}(\n{{\n    {attributes_str}\n}})"

    def __repr__(self):
        """ 为调试提供详细信息 """
        return self.__str__()


class RetryCmd(BaseCommand, ABC):
    """
    :class:`RetryCmd` 是可以重复执行的指令基类，继承自 :class:`BaseCommand`
    Attributes:
        retries: 指令重试次数，无论成功还是失败都会执行指定次数，默认为 0
        error_retries: 指令执行错误时的重试次数，仅在指令执行失败时重试，默认为 0
        retries_time: 指令重复执行的时间间隔，单位为秒，默认为 0.0
        error_retries_time: 指令执行错误时的重试时间间隔，单位为秒，则为 0.0
    """

    retries: int = Field(0, description="指令重复执行次数")
    error_retries: int = Field(0, description="指令执行出错时的重试次数")
    retries_time: float | int = Field(0.0, description="指令重复执行时的时间间隔")
    error_retries_time: float | int = Field(0.0, description="指令执行出错时的重试时间间隔")

    def execute(self, **kwargs):
        """
        执行指令，并根据 retries 和 error_retries 的设置进行重复执行和错误重试
        """
        for attempt in range(self.retries + 1):
            _start_msg_1 = f"正在执行指令 🚀<{self.name}>🚀"
            _start_msg_2 = f"重复执行指令第 [{attempt + 1}] 次 🚀<{self.name}>🚀\n"
            info(_start_msg_2 if self.retries > 0 else _start_msg_1)

            _successful = False
            for error_attempt in range(self.error_retries + 1):
                try:
                    self.set_status(STATUS_RUNNING)  # 设置指令状态为执行中
                    # TIP: run_command 方法需要在子类中实现, 子类对象执行时会在这里调用, self 即为当前子类对象
                    self.run_command(**kwargs)  # 执行指令
                    self.set_status(STATUS_COMPLETED)  # 设置指令状态为已完成
                    _successful = True
                    break  # 执行成功后跳出错误重试循环, 继续执行下一次指令循环
                except CommandRunningException as cre:
                    _error_msg_0 = f"执行 &lt;{self.name}&gt; 失败: {cre}"
                    _error_msg_1 = f"执行 &lt;{self.name}&gt; 失败,错误重试第 [{error_attempt}] 次: {cre}\n"
                    if self.error_retries > 0 and error_attempt != 0:
                        self.q_obj.error_message.emit("\t(RetryCmd) " + _error_msg_1)
                        error(f"执行 <{self.name}> 失败,错误重试第 [{error_attempt}] 次: {cre}\n")
                    else:
                        self.q_obj.error_message.emit("\t(RetryCmd) " + _error_msg_0)
                        error(f"执行 <{self.name}> 失败: {cre}")

                    self.set_status(STATUS_FAILED)  # 设置指令状态为失败
                except AttributeError as ae:
                    error(f"指令属性错误，退出执行：{ae}")
                    self.set_status(STATUS_FAILED)  # 设置指令状态为失败
                    return
                except KeyboardInterrupt:
                    error(f"已手动中断指令执行，退出执行")
                    self.set_status(STATUS_FAILED)  # 设置指令状态为失败
                    return
                except Exception as e:
                    error(f"未知错误，退出指令执行：{e}")
                    self.set_status(STATUS_FAILED)  # 设置指令状态为失败
                    return

                # 等待一段时间再进行下一次重试
                if error_attempt < self.error_retries:
                    msg = f"等待 {self.error_retries_time:.2f} 秒后再进行下一次错误重试"
                    self.q_obj.info_message.emit("\t(RetryCmd) " + msg)
                    info(msg)
                    time.sleep(self.error_retries_time)

                # 如果错误重试次数已用完，且指令容错次数大于 0，打印错误
                if error_attempt == self.error_retries and self.error_retries > 0:
                    error(f"指令 <{self.name}> 在错误重试 {self.error_retries} 次后仍未成功")

            if _successful:
                _end_msg_1 = f"指令 <{self.name}> 🎉执行成功🎉"
                _end_msg_2 = f"指令 <{self.name}> 第 [{attempt + 1}] 次 🎉执行成功🎉\n"
                info(_end_msg_2 if self.retries > 1 else _end_msg_1)
                info("-" * 100)
            else:
                _end_msg_1 = f"指令 <{self.name}> ❌执行失败❌\n"
                _end_msg_2 = f"指令 <{self.name}> 第 [{attempt + 1}] 次 ❌执行失败❌"
                warning(_end_msg_2 if self.retries > 1 else _end_msg_1)
                warning("x-" * 43 + '\n')

            if attempt < self.retries:  # 确保只在每两次重复指令之间等待一段时间
                info(f"等待 {self.retries_time:.2f}s 后，继续执行下一次指令")
                time.sleep(self.retries_time)

    @abstractmethod
    def run_command(self, **kwargs):
        """
        具体指令的执行方法，每个子类需要实现。
        """
        raise NotImplementedError("每个具体指令类必须实现 'run_command' 方法")
