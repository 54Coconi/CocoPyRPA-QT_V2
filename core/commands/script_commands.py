"""
@author: 54Coconi
@date: 2024-12-09
@version: 1.0.0
@path: /core/commands/script_commands.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    执行脚本命令模块
    包括 <执行 DOS 命令>、<执行 Python 代码>
"""

import subprocess

from pydantic import Field
from typing import Optional, Any, Dict

from utils.debug import print_func_time, print_command
from utils.opencv_funcs import drawRectangle

from .base_command import BaseCommand, CommandRunningException, STATUS_COMPLETED, STATUS_FAILED
from .mouse_commands import *
from .keyboard_commands import *
from .image_commands import *
from ..safe_globals import safe_globals_manager  # 导入全局单例


_DEBUG = True


class ExecuteDosCmd(BaseCommand):
    """
    <执行 DOS 命令> 指令
    用于执行指定的命令，支持跨平台（Windows 和 Unix 系统）并捕获执行后的输出

    Attributes:
        name: (str) 指令名称
        is_active: (bool) 指令是否生效, 默认为 True

        dos_cmd: (str) 需要执行的具体命令
        working_dir: (Optional[str]) 指定的工作目录, 默认为 None
        timeout: (Optional[float]) 命令执行超时时间(秒), 默认为 None

    Notes:
        - 对于 start 命令，程序内置超时检测(默认 5 秒)，即如果超过 5 秒应用未响应则认为失败.当然可以设置超时 timeout 来控制,在 timeout>5 时生效
        - 通常 start 命令执行超时是因为该应用系统找不到或不存在，请先在 DOS 窗口中检查该应用是否存在，再执行 start 命令.建议使用绝对路径执行 start 命令
    """
    name: str = Field("执行DOS命令", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")

    dos_cmd: str = Field(..., description="需要执行的dos命令")
    working_dir: Optional[str] = Field(None, description="指定的工作目录")
    timeout: Optional[float | int] = Field(None, description="命令执行超时时间 (秒)")

    @print_func_time(debug=_DEBUG)
    def execute(self, **kwargs):
        """
        执行命令并捕获输出，支持跨平台和异常处理
        Raises:
            CommandRunningException: 执行过程中发生错误或超时
        """
        print(f"[INFO] - (ExecuteDosCmd) 正在执行指令: 🚀{self.name}🚀")
        _msg = f"[INFO] - (ExecuteDosCmd) 执行命令: '{self.dos_cmd}' "
        if self.dos_cmd == "":
            raise CommandRunningException("指令内容为空，无法执行")
        try:
            # 检测当前操作系统
            shell_flag = True if os.name == "nt" else False  # Windows 使用 shell=True,Unix 使用 shell=False

            # 判断是否为 start 命令,使用 Popen 执行 start 命令
            if os.name == "nt" and self.dos_cmd.lower().startswith("start "):
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

                process = subprocess.Popen(
                    self.dos_cmd,
                    shell=shell_flag,
                    cwd=self.working_dir,
                    startupinfo=si,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE
                )

                def check_process():
                    """ 检查进程是否已经结束 """
                    try:
                        process.wait(timeout=0.1)  # 短时间等待
                        return True
                    except subprocess.TimeoutExpired:
                        return False

                # 设置总等待时间
                start_time = time.time()
                while time.time() - start_time < (self.timeout or 5):  # 默认5秒超时
                    if check_process():
                        if process.returncode != 0:
                            stderr = process.stderr.read().decode('utf-8', errors='ignore')
                            raise CommandRunningException(f"命令执行失败: {stderr}")
                        print(f"[INFO] - (ExecuteDosCmd) 指令 {self.name} 🎉执行成功🎉")
                        return
                    time.sleep(0.1)

                # 超时处理
                process.kill()
                raise CommandRunningException(f"命令执行超时 (超时时间: {self.timeout or 5} 秒),"
                                              f"请检查命令是否正确,可以在CMD窗口内先执行一遍 start 命令,然后再执行该命令")

            # 执行其它命令
            result = subprocess.run(
                self.dos_cmd,
                shell=shell_flag,
                cwd=self.working_dir,
                timeout=self.timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 捕获标准输出和错误输出
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode != 0:
                # 如果命令执行失败，抛出异常并附带错误信息
                error_message = f"错误信息: {stderr or '未知错误'}"
                raise CommandRunningException(error_message)

            self.set_status(STATUS_COMPLETED)  # 设置指令状态为已完成
            # 打印成功信息并返回标准输出
            print(f"{_msg} 成功，输出: {stdout} ")
            print(f"[INFO] - (ExecuteDosCmd) 指令 {self.name} 🎉执行成功🎉")
            print("-" * 100)
            return stdout

        except CommandRunningException as e:
            # 捕获 CommandRunningException 异常
            self.set_status(STATUS_FAILED)  # 设置指令状态为失败
            print(f"[ERROR] - (ExecuteDosCmd) 指令执行失败: {str(e)}")
            raise CommandRunningException(str(e))
        except subprocess.TimeoutExpired as e:
            # 处理超时异常
            self.set_status(STATUS_FAILED)  # 设置指令状态为失败
            error_message = f"命令执行超时 (超时时间: {self.timeout} 秒): {str(e)}"
            print(f"[ERROR] - (ExecuteDosCmd) {error_message}")
            raise CommandRunningException(error_message)
        except Exception as e:
            # 捕获其他异常
            self.set_status(STATUS_FAILED)  # 设置指令状态为失败
            print(f"[ERROR] - (ExecuteDosCmd) 发生未知错误: {str(e)}")
            raise Exception(f"发生未知错误: {str(e)}")


class ExecutePyCmd(BaseCommand):
    """
    <执行 Python 代码> 指令
    支持执行复杂的 Python 代码块，返回执行结果和局部变量，并限制危险操作
    Attributes:
        name: (str) 指令名称
        is_active: (bool) 指令是否生效, 默认为 True

        code: (str) 需要执行的 Python 代码字符串
    """
    name: str = Field("执行 Python 脚本", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")

    code: str = Field(..., description="需要执行的 Python 代码字符串")

    def __init__(self, **data):
        super().__init__(**data)
        # 注册自动化指令类
        self._register_command_classes()
        # 注册自定义类
        self._register_custom_classes()
        # 注册函数
        self._register_functions()

    @staticmethod
    def _register_command_classes():
        """ 注册所有可用的自动化指令类 """
        command_classes = {
            # 鼠标操作
            "MouseClickCmd": MouseClickCmd,
            "MouseMoveToCmd": MouseMoveToCmd,
            "MouseMoveRelCmd": MouseMoveRelCmd,
            "MouseDragToCmd": MouseDragToCmd,
            "MouseDragRelCmd": MouseDragRelCmd,
            "MouseScrollCmd": MouseScrollCmd,
            "MouseScrollHCmd": MouseScrollHCmd,
            # 键盘操作
            "KeyPressCmd": KeyPressCmd,
            "KeyReleaseCmd": KeyReleaseCmd,
            "KeyTapCmd": KeyTapCmd,
            "HotKeyCmd": HotKeyCmd,
            "KeyTypeTextCmd": KeyTypeTextCmd,
            # 图像操作
            "ImageMatchCmd": ImageMatchCmd,
            "ImageClickCmd": ImageClickCmd,
            "ImageOcrCmd": ImageOcrCmd,
            "ImageOcrClickCmd": ImageOcrClickCmd,
            # 执行Dos命令
            "ExecuteDosCmd": ExecuteDosCmd,
        }
        for name, cmd_class in command_classes.items():
            safe_globals_manager.register_command(name, cmd_class)

    @staticmethod
    def _register_custom_classes():
        """ 注册自定义类 """
        custom_classes = {
            # 图片识别工具类
            "OCRTool": OCRTool
        }
        for name, custom_class in custom_classes.items():
            safe_globals_manager.register_custom_class(name, custom_class)

    @staticmethod
    def _register_functions():
        """ 注册函数 """
        custom_functions = {
            # debug 函数
            "print_func_time": print_func_time,
            "print_command": print_command,
            "drawRectangle": drawRectangle
        }
        for name, func in custom_functions.items():
            safe_globals_manager.register_custom_function(name, func)

    @print_func_time(debug=_DEBUG)
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行用户输入的 Python 代码,捕获结果或异常,支持限制危险操作和指令类调用
        Returns:
            dict: 包含执行结果和局部变量的字典
        Raises:
            CommandRunningException: 执行过程中发生错误
        """
        print(f"[INFO] - (ExecutePyCmd) 正在执行指令 🚀{self.name}🚀")
        _msg = f"[INFO] - (ExecutePyCmd) 执行Python代码:\n{self.code}\n"
        try:
            # 获取执行环境
            additional_globals = kwargs.get("additional_globals", {})
            safe_globals = safe_globals_manager.create_restricted_exec_env(additional_globals)
            local_vars = {}  # 用于存储局部变量

            # 执行代码
            exec(self.code, safe_globals, local_vars)

            # 返回局部变量和结果
            result = local_vars.get("result", "代码执行成功，但没有定义 'result' 变量返回值")
            print(f"{_msg} 成功, 结果为: {result}")
            print(f"[INFO] - (ExecutePyCmd) 指令 {self.name} 🎉执行成功🎉")
            print("-" * 100)
            self.set_status(STATUS_COMPLETED)
            return {"result": result, "locals": local_vars}

        except Exception as e:
            # 捕获所有异常并抛出自定义异常
            error_message = f"代码执行失败，错误信息: {str(e)}"
            print(f"[ERROR] - (ExecutePyCmd) {error_message}")
            self.set_status(STATUS_FAILED)
            raise CommandRunningException(error_message)
