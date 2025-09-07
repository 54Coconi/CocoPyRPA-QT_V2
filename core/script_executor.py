"""
script_executor.py

指令执行引擎（基于脚本文件）
"""

import json
import operator
import os
import time
from pathlib import Path
from typing import List, Dict, Optional

import keyboard
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from core.commands.base_command import BaseCommand
from core.commands.flow_commands import IfCommand, LoopCommand
from core.commands.image_commands import ImageOcrCmd, ImageOcrClickCmd, ImageMatchCmd, ImageClickCmd
from core.commands.subtask_command import SubtaskCommand
from .command_map import COMMAND_MAP
from .command_result_manager import CommandResultManager

_DEBUG = False


class ScriptExecutor(QThread):
    """ 自动化脚本执行器 """
    execution_started = pyqtSignal(str)  # 执行器启动信号，传入脚本路径
    execution_finished = pyqtSignal(str, bool)  # 执行器结束信号，传入(脚本路径, 是否成功)
    progress_updated = pyqtSignal(str, int, int)  # 进度更新信号，传入(脚本路径, 当前步骤, 总步骤)
    log_message = pyqtSignal(str)  # 日志消息

    def __init__(self, ocr=None, parent=None):
        super().__init__(parent)
        self.current_script = None  # 当前执行的脚本文件路径
        self.ocr = ocr
        self.active_scripts: Dict[str, ScriptWorker] = {}  # 存储脚本运行状态：{script_path: worker}
        self.stop_flags: Dict[str, bool] = {}  # 存储停止标志：{script_path: stop_flag}
        self.thread = None
        keyboard.add_hotkey('q+esc', self.stop_script)

    def execute_script(self, script_path: str):
        """ 执行指定脚本 """
        self.current_script = script_path
        if script_path in self.active_scripts:
            self.log_message.emit(f"⚠ 脚本已在执行中: {script_path}")
            return
        # 存储停止标志为 False（表示不停止）
        self.stop_flags[script_path] = False
        print(f"🔴 当前 stop_flags 为：{self.stop_flags}") if _DEBUG else None

        # 创建脚本执行工作流
        worker = ScriptWorker(script_path, self.ocr)

        # 信号连接
        worker.progress.connect(self._handle_progress)
        worker.log.connect(self.log_message.emit)

        # 存储运行状态
        self.active_scripts[script_path] = worker
        print(f"🔴 当前 active_scripts 为：{self.active_scripts}") if _DEBUG else None

        # 执行工作流
        worker.execute()
        self.execution_started.emit(script_path)

    def stop_script(self):
        """ 停止执行指定脚本 """
        print("(stop_script) -  当前 stop_flags 为：", self.stop_flags) if _DEBUG else None
        if self.current_script in self.stop_flags:
            self.log_message.emit(f"🟥 正在停止脚本: {self.current_script}")
            self.stop_flags[self.current_script] = True

    def _handle_progress(self, script_path: str, current: int, total: int):
        """ 处理进度更新 """
        self.progress_updated.emit(script_path, current, total)
        if current == total:
            self.log_message.emit(f"🎉 脚本所有的 {total} 个顶层指令执行完成")
            self.execution_finished.emit(script_path, True)
            self._cleanup(script_path)
        elif current == -1:
            self.log_message.emit(f"⛔ 脚本停止执行")
            self.execution_finished.emit(script_path, False)
            self._cleanup(script_path)

    def _cleanup(self, script_path: str):
        """ 清理资源 """
        if script_path in self.active_scripts:
            del self.active_scripts[script_path]
        if script_path in self.stop_flags:
            del self.stop_flags[script_path]

    def run(self):
        """ 线程入口 """
        try:
            self.execute_script(self.current_script)
        except Exception as e:
            print(f"❌ 脚本执行出错：{e}")


class ScriptWorker(QObject):
    """ 脚本执行工作线程 """
    finished = pyqtSignal()
    progress = pyqtSignal(str, int, int)  # (脚本路径, 当前步骤, 总步骤)
    log = pyqtSignal(str)

    def __init__(self, script_path: str, ocr=None):
        super().__init__()
        self.script_path = script_path
        self._ocr = ocr
        self.commands: List[BaseCommand] = []
        self.results_manager = CommandResultManager()  # 指令执行结果管理器
        self.current_top_step = 0

    def load_script(self) -> bool:
        """脚本加载（支持嵌套指令）"""
        # 初始化加载栈用于循环检测
        if not hasattr(self, '_loading_stack'):
            self._loading_stack = set()

        if self.script_path in self._loading_stack:
            self.log.emit(f"❌ 检测到循环引用: {self.script_path}")
            return False

        self._loading_stack.add(self.script_path)
        try:
            with open(self.script_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                steps = config.get("steps", [])

                self.commands = self._parse_commands(steps)
                self.log.emit(f"🟢 成功加载 {len(self.commands)} 个顶层指令（含嵌套指令）")
                return True

        except Exception as e:
            self.log.emit(f"❌ 脚本加载失败: {str(e)}")
            return False
        finally:
            self._loading_stack.discard(self.script_path)

    def execute(self):
        """ 执行入口 """
        if not self.load_script():
            self.progress.emit(self.script_path, -1, 0)
            self.finished.emit()
            return

        total = len(self.commands)
        # 初始化执行进度
        self.progress.emit(self.script_path, 0, total)

        try:
            start_time = time.time()
            for idx, cmd in enumerate(self.commands, start=1):
                if self._should_stop():
                    break

                self.current_top_step = idx
                self._execute_one_command(cmd, current_step=idx)
                # 执行最后一个指令时，这里不更新进度，防止重复更新
                if idx != total:
                    self.progress.emit(self.script_path, idx, total)
            self.log.emit(f"\n⏰ 脚本执行完成，耗时 {time.time() - start_time:.2f} 秒")
            success = not self._should_stop()
        except Exception as e:
            self.log.emit(f"❌ 执行出错: {str(e)}")
            success = False

        self.progress.emit(self.script_path, total if success else -1, total)
        self.finished.emit()

    def _parse_commands(self, steps: List[dict]) -> List[BaseCommand]:
        """递归解析指令列表"""
        commands = []
        for idx, step in enumerate(steps, start=1):
            cmd_type = step.get("type", "unknown_command")
            action = step.get("action")
            params = step.get("params", {})

            # 跳过触发器指令
            if cmd_type == "trigger":
                continue
            elif cmd_type == "subtask":
                subtask_file = params.get('subtask_file', '')
                print(f"🟡 解析子任务：{subtask_file}")

                if subtask_file in self._loading_stack:
                    self.log.emit(f"❌ 检测到循环引用: {subtask_file}")
                    continue
                else:
                    self._loading_stack.add(subtask_file)
                    cmd = self._create_command(cmd_type, action, params)
                    if cmd:
                        commands.append(cmd)
                    self._loading_stack.discard(subtask_file)
            else:
                cmd = self._create_command(cmd_type, action, params)
                if cmd:
                    commands.append(cmd)
        print(f"😀子任务 loading stack: {self._loading_stack}") if _DEBUG else None
        return commands

    def _create_command(self, cmd_type: str, action: str, params: dict) -> Optional[BaseCommand]:
        """创建单个指令对象（支持嵌套）"""

        try:
            # 获取指令类
            cmd_class = COMMAND_MAP.get(cmd_type, {}).get(action)
            if not cmd_class:
                raise ValueError(f"未知指令类型: type={cmd_type}, action={action}")

            # 处理文字识别指令
            if cmd_class == ImageOcrCmd:
                # 如果是文字识别指令，需要提前加载模型
                command = ImageOcrCmd(self._ocr, **params)
            elif cmd_class == ImageOcrClickCmd:
                # 如果是文字点击指令，需要提前加载模型
                command = ImageOcrClickCmd(self._ocr, **params)
            else:
                # 其他指令
                command = cmd_class(**params)  # **params 将字典转换为关键字参数

            self.log.emit(f"🟢 成功创建指令: {command.name}")

            # 处理 If 判断 指令
            if isinstance(command, IfCommand):
                then_commands = self._parse_commands(params.get("then_commands", []))
                else_commands = self._parse_commands(params.get("else_commands", []))
                command.then_commands = then_commands
                command.else_commands = else_commands
            # 处理 Loop 循环 指令
            elif isinstance(command, LoopCommand):
                loop_commands = self._parse_commands(params.get("loop_commands", []))
                command.loop_commands = loop_commands
            # 处理子任务指令（支持循环检测）
            elif isinstance(command, SubtaskCommand):
                subtask_path = Path(params.get("subtask_file", ""))
                if not subtask_path.exists():
                    raise FileNotFoundError(f"子任务文件不存在: {subtask_path}")

                with open(subtask_path, 'r', encoding='utf-8') as f:
                    subtask_config = json.load(f)
                    subtask_steps = self._parse_commands(subtask_config.get("steps", []))
                    command.subtask_steps = subtask_steps

            return command
        except Exception as e:
            self.log.emit(f"❌指令创建失败: {str(e)}")
            return None

    def _execute_one_command(self, command: BaseCommand, is_top_level=True, current_step=0):
        """ 执行单个指令
        is_top_level: 是否是顶层指令
        current_step: 当前步骤
        """
        try:
            # 检查指令是否激活
            if command.is_active is False:
                self.log.emit(f"⚠ 指令: {command.name} 未激活, 跳过执行")
                return

            # 检查图片匹配指令
            if isinstance(command, ImageMatchCmd) or isinstance(command, ImageClickCmd):
                if not os.path.exists(command.template_img):
                    raise FileNotFoundError(f"模板图片 ‘{command.template_img}’ 不存在")

            # 判断是否顶层指令
            if is_top_level:
                self.log.emit(f"\n🔶 执行步骤 {current_step}：{command.name}")
            else:
                self.log.emit(f"🔸 执行步骤 {current_step}：{command.name}")

            # 执行指令
            if isinstance(command, IfCommand):
                self._execute_if_command(command)
            elif isinstance(command, LoopCommand):
                self._execute_loop_command(command)
            elif isinstance(command, SubtaskCommand):
                self._execute_subtask_command(command)
            else:
                command.execute()

            # self.results_list.append(command.model_dump())
            self.results_manager.add_result(
                command.id, 
                command.name, 
                command.model_dump()
            )
            # print(f"[INFO] - 当前指令 <{command.name}> 执行结果: {self.results_list[-1]}") if _DEBUG else None
            print(f"[INFO] - 当前指令 <{command.name}> 执行结果已添加到结果管理器") if _DEBUG else None

        except FileNotFoundError as e:
            self.log.emit(f"❌ 步骤 {self.current_top_step + 1} 执行失败: {str(e)}")  # 不向上抛出异常
        except Exception as e:
            raise e  # 向上抛出异常以中断执行

    def _execute_if_command(self, command: IfCommand):
        """ 执行 If 命令 """
        if command.is_active is False:
            self.log.emit(f"⚠ 指令: {command.name} 未激活, 跳过执行")
            return
        # 使用更安全的方式解析条件表达式，避免使用 eval
        condition_result = self.evaluate_condition(command.condition)

        # 根据条件的结果选择执行的代码块
        block = command.then_commands if condition_result else command.else_commands

        # 打印日志，表明条件是否成立
        self.log.emit(f"\n{'✅ 条件成立' if condition_result else '❎ 条件不成立'}，开始执行对应代码块")

        # 遍历并执行选中的代码块中的子命令
        for idx, subcommand in enumerate(block, start=1):
            self._execute_one_command(subcommand, is_top_level=False, current_step=idx)

    def _execute_loop_command(self, command: LoopCommand):
        """ 执行 Loop 命令 """
        if command.is_active is False:
            self.log.emit(f"⚠ 指令: {command.name} 未激活, 跳过执行")
            return
        for i in range(command.count):
            self.log.emit(f"\n🔁 开始执行循环体（第 {i + 1} 次）")
            for idx, subcommand in enumerate(command.loop_commands, start=1):
                self._execute_one_command(subcommand, is_top_level=False, current_step=idx)

    def _execute_subtask_command(self, command: SubtaskCommand):
        """ 执行子任务命令 """
        if command.is_active is False:
            self.log.emit(f"⚠ 指令: {command.name} 未激活, 跳过执行")
            return
        self.log.emit(f"\n🔗 开始执行子任务：{Path(command.subtask_file).name}")
        for idx, subcommand in enumerate(command.subtask_steps, start=1):
            self._execute_one_command(subcommand, is_top_level=False, current_step=idx)

    def _should_stop(self):
        """ 检查停止标志 """
        return executor.stop_flags.get(self.script_path, False)

    def evaluate_condition(self, condition: str) -> bool:
        """
        根据给定的条件字符串生成一个可执行的判断逻辑，使用指令的 `id` 来确定对应的指令

        condition 条件格式为: results_list['<id>']['<field>'] <operator> <value>
        eg: "results_list['12345678']['status'] == 2"
        """

        def get_command_by_id(_cmd_id):
            """通过指令 id 获取对应的指令执行结果"""
            result = self.results_manager.get_result(_cmd_id)
            return result.result_data if result else None

        def safe_get_field(_cmd_result, _field_name):
            """安全地获取指令结果中的字段值"""
            if not _cmd_result:
                return None
            return _cmd_result.get(_field_name)

        try:
            # 从条件字符串解析出指令 id 和字段
            parts = condition.split(" ")
            if len(parts) != 3:
                self.log.emit(f"❌ 条件表达式格式错误")
                return False

            # 提取 id、字段、操作符和值
            left_expr, operator_symbol, right_value = parts
            cmd_id = left_expr.split("[")[1].strip("'").strip("']")
            field_name = left_expr.split("]")[1].strip("['").strip("']")

            # 根据 id 获取指令结果
            cmd_result = get_command_by_id(cmd_id)
            field_value = safe_get_field(cmd_result, field_name)

            # 将右值转换为合适的类型
            if right_value in {"True", "False"}:  # 布尔值
                right_value = right_value == "True"
            elif right_value.isdigit():  # 整数
                right_value = int(right_value)
            elif "." in right_value:  # 浮点数
                try:
                    right_value = float(right_value)
                except ValueError:
                    pass  # 保留为字符串
            else:  # 字符串
                right_value = right_value.strip("'").strip('"')

            # 操作符映射
            operators = {
                "==": operator.eq,
                "!=": operator.ne,
                ">": operator.gt,
                ">=": operator.ge,
                "<": operator.lt,
                "<=": operator.le,
            }
            operation = operators.get(operator_symbol)

            if operation is None:
                self.log.emit(f"❌ 不支持操作符 '{operator_symbol}' ")
                return False

            # 执行判断
            return operation(field_value, right_value)
        except Exception as e:
            self.log.emit(f"❌ 条件解析失败: {str(e)}")
            return False


# 全局执行器实例
executor = ScriptExecutor()
