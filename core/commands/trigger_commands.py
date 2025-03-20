"""
@author: 54Coconi
@date: 2025-01-24
@version: 1.0.0
@path: core/commands/trigger_commands.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    - 触发器模块，包含：进程状态监控、网络连接监控、时间到达监控三种触发条件指令类
"""

import socket
import threading
import time
import psutil

from typing import Optional
from datetime import datetime, timedelta
from pydantic import PrivateAttr, field_validator, Field

from .base_command import BaseCommand, STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED


# @进程状态监控触发器
class ProcessTriggerCmd(BaseCommand):
    """
    当指定进程 启动/退出 时触发指令
    Attributes:
        name: (str): 指令名称
        process_name: (str): 要监控的进程名称（不区分大小写）
        trigger_type: (str): 触发类型 start-进程启动时 / stop-进程退出时
    """
    name: str = Field("进程状态监控", description="指令名称")
    process_name: str = Field(..., description="要监控的进程名称（不区分大小写）")
    trigger_type: str = Field(..., description="触发类型：start（进程启动时触发）或 stop（进程关闭时触发）")

    # 私有属性（不参与序列化）
    _stop_event: Optional[threading.Event] = PrivateAttr(default=None)
    _monitor_thread: Optional[threading.Thread] = PrivateAttr(default=None)

    @classmethod
    @field_validator('trigger_type')
    def validate_trigger_type(cls, v):
        """ 验证触发类型 """
        if v not in ['start', 'stop']:
            raise ValueError("trigger_type 必须是 'start' 或 'stop'")
        return v

    def execute(self, **kwargs):
        """ 在QObject线程中执行监控 """
        # 通过self.q_obj访问Qt功能
        self._stop_event = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_process,
            daemon=True
        )
        self._monitor_thread.start()
        self.set_status(STATUS_RUNNING)

    def _monitor_process(self):
        """进程状态监控循环（兼容新版psutil）"""
        target_name = self.process_name.lower()
        prev_running = self.is_program_running()  # 初始化上一次运行状态

        while not self._stop_event.is_set():
            current_running = False  # 初始化当前运行状态

            # 遍历所有进程（更高效的检查方式）
            for proc in psutil.process_iter(['name']):  # 显式指定要获取的字段
                try:
                    # 正确获取进程名称的方式
                    proc_name = proc.info['name'].lower() if hasattr(proc, 'info') else proc.name().lower()
                    if proc_name == target_name:
                        current_running = True
                        print("(ProcessTriggerCmd) - 找到匹配进程：", proc.name(), "PID:", proc.pid, "PPID:",
                              proc.ppid(), "命令行:", proc.cmdline())
                        break  # 找到匹配进程即可退出循环
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # 处理进程已终止或无权限的情况
                    continue

            # 触发判断逻辑保持不变
            if self.trigger_type == 'start' and current_running and not prev_running:
                self.set_status(STATUS_COMPLETED)
                break
            elif self.trigger_type == 'stop' and not current_running and prev_running:
                self.set_status(STATUS_COMPLETED)
                break

            prev_running = current_running
            time.sleep(1)

    def is_program_running(self):
        """检查目标程序是否正在运行"""
        for proc in psutil.process_iter(attrs=['name']):
            proc_name = proc.info['name'].lower() if hasattr(proc, 'info') else proc.name().lower()
            if proc_name == self.process_name.lower():
                return True
        return False

    def stop(self):
        """停止监控"""
        if self._stop_event:
            self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join()


# @网络连接监控触发器
class NetworkConnectionTriggerCmd(BaseCommand):
    """
    当成功建立网络连接时触发指令

    Attributes:
        name: (str): 指令名称
        host: (str): 要连接的目标主机，默认谷歌DNS
        port: (int): 要连接的目标端口，默认53
    """
    name: str = Field("网络连接监控", description="指令名称")
    host: str = Field(default="8.8.8.8", description="检测网络连接的目标主机")
    port: int = Field(default=53, description="检测网络连接的目标端口")

    # 私有属性（不参与序列化）
    _stop_event: Optional[threading.Event] = PrivateAttr(default=None)
    _monitor_thread: Optional[threading.Thread] = PrivateAttr(default=None)

    def execute(self, **kwargs):
        """启动网络监控线程"""
        self._stop_event = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_network,
            daemon=True
        )
        self._monitor_thread.start()
        self.set_status(STATUS_RUNNING)

    def _monitor_network(self):
        """网络连接监控循环"""
        prev_connected = self.is_network_connected()  # 初始化上一次连接状态

        while not self._stop_event.is_set():
            current_connected = False  # 初始化当前连接状态

            # 尝试建立TCP连接
            try:
                # 尝试建立TCP连接
                with socket.create_connection(
                        address=(self.host, self.port),
                        timeout=5
                ):
                    print("(NetworkConnectionTriggerCmd) - 成功建立连接")
                    current_connected = True

            except (socket.error, OSError):
                pass  # 连接失败时忽略

            # 触发判断逻辑保持不变
            if not prev_connected and current_connected:
                self.set_status(STATUS_COMPLETED)
                break

            prev_connected = current_connected
            time.sleep(5)  # 每5秒重试一次

    @staticmethod
    def is_network_connected():
        """检测是否能够连接到外部网络"""
        try:
            # 尝试连接 Google 的公共 DNS（或其他可达的地址）
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except (socket.error, OSError):
            return False

    def stop(self):
        """停止监控"""
        if self._stop_event:
            self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join()


# @时间到达监控触发器
class DateTimeTriggerCmd(BaseCommand):
    """
    当系统时间达到指定时间时触发指令
    Attributes:
        name: (str): 指令名称
        target_time: (str): 目标时间，格式YYYY-MM-DD HH:MM:SS
    """
    name: str = Field("时间到达监控", description="指令名称")
    target_time: str = Field(..., description="触发时间，格式为 'YYYY-MM-DD HH:MM:SS'")

    _stop_event: Optional[threading.Event] = PrivateAttr(default=None)
    _monitor_thread: Optional[threading.Thread] = PrivateAttr(default=None)

    @classmethod
    @field_validator('target_time')
    def validate_target_time(cls, v):
        """验证时间格式"""
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("target_time 格式必须为 'YYYY-MM-DD HH:MM:SS'")
        return v

    def execute(self, **kwargs):
        """启动时间监控线程"""

        self._stop_event = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_time,
            daemon=True
        )

        self._monitor_thread.start()
        self.set_status(STATUS_RUNNING)

    def _monitor_time(self):
        """时间监控循环"""
        target = datetime.strptime(self.target_time, "%Y-%m-%d %H:%M:%S")

        while not self._stop_event.is_set():
            if target <= datetime.now() < target + timedelta(seconds=1):
                self.set_status(STATUS_COMPLETED)
                break
            # 如果当前时间已经完全超过目标时间，则设置状态为PENDING，但不能立即退出循环
            elif datetime.now() >= target + timedelta(seconds=1):
                self.set_status(STATUS_PENDING)
                print(f"(DateTimeTriggerCmd) - 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                      f"已经完全超过目标时间: {target}")
            time.sleep(1)  # 每秒检查一次

    def stop(self):
        """停止监控"""
        if self._stop_event:
            self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join()
