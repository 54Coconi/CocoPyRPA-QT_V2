"""
指令执行引擎模块（基于GUI界面）
"""
import operator
import os
from enum import Enum
from typing import List, Optional

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator

from ui.widgets.CocoSettingWidget import config_manager
from utils.image_process.ocr_tools import OCRTool
from .command_map import COMMAND_MAP
from .command_result_manager import CommandResultManager
from .commands.base_command import BaseCommand
from .commands.flow_commands import LoopCommand, IfCommand
from .commands.image_commands import ImageMatchCmd, ImageOcrCmd, ImageOcrClickCmd
from .commands.keyboard_commands import *
from .commands.subtask_command import SubtaskCommand

_DEBUG = True

LOG_COLORS = {
    "默认": {
        "INFO": "#C4E791",
        "WARN": "#ffb700",
        "ERROR": "#be0007"
    },
    "深色": {
        "INFO": "#C4E791",
        "WARN": "#ffb700",
        "ERROR": "#ff0007"
    },
    "浅色": {
        "INFO": "#0a5609",
        "WARN": "#B28E17",
        "ERROR": "#c90007"
    },
    "护眼": {
        "INFO": "#C4E791",
        "WARN": "#ffb700",
        "ERROR": "#ff0007"
    }
}


def load_theme_config() -> dict:
    """ 加载主题配置 """
    theme = config_manager.config.get("General", {}).get("Theme", "默认")
    return LOG_COLORS[theme]


class LogLevel(Enum):
    """日志等级"""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class CommandExecutor(QThread):
    """
    指令执行器，支持遍历树节点并执行指令
    """
    task_stop = pyqtSignal()  # 任务终止信号
    task_finished = pyqtSignal()  # 任务完成信号
    task_error = pyqtSignal(str)  # 任务错误信号
    progress_update = pyqtSignal(str)  # 进度更新信号
    log_message = pyqtSignal(str)  # 日志消息信号, 用于日志显示

    select_node = pyqtSignal(QTreeWidgetItem or None)  # 选中节点信号

    def __init__(self,
                 tree_widget: QTreeWidget, run_action: str, ocr: OCRTool = None,
                 all_tasks_cmd: List[BaseCommand] = None, parent=None):
        """
        :param tree_widget: 使用主程序中的 QTreeWidget
        :param run_action: 运行动作种类（run_all、run_one、run_now）
        :param ocr: OCR工具
        :param all_tasks_cmd: 所有任务指令
        :param parent: 父类
        """
        super().__init__(parent)
        self.tree_widget = tree_widget  # 使用主程序中的 QTreeWidget
        self.run_action = run_action  # 运行动作种类（run_all、run_one、run_from_now、run_to_now）
        self._ocr = ocr
        self.all_tasks_cmd: List[BaseCommand] = all_tasks_cmd or []  # 存储指令对象列表
        self.parent = parent

        self.stop_flag = False  # 停止标志
        self.current_node = None  # 当前正在执行的节点
        self.task_name = ""  # 当前任务名称
        self.results_manager = CommandResultManager()  # 指令执行结果管理器
        self.current_index = 0  # 当前执行的指令索引
        self.bindings = {}  # 绑定关系

        # TODO: 订阅运行异常信号
        # pub.subscribe(self.on_cmd_running_error, "command_running_exception")
        # TODO: 订阅运行日志信号
        # pub.subscribe(self.on_cmd_running_progress, "command_running_progress")

        self.task_stop.connect(self._task_stop)  # 连接任务终止信号
        self.task_finished.connect(self._task_finished)  # 连接任务完成信号

        # 命令映射表
        self.command_map = COMMAND_MAP

    def _format_msg(self, level: LogLevel, message: str) -> None:
        """统一日志处理"""
        # 根据日志等级设置不同的颜色,采用 HTML 格式
        formatted_message = ""
        theme = load_theme_config()  # 加载主题
        if level.value == LogLevel.INFO.value:
            formatted_message = f"<p align='left'><font color='{theme[level.value]}' size='3'>" \
                                f"[{level.value}] - {message}" \
                                f"</font></p>"
        elif level.value == LogLevel.WARN.value:
            formatted_message = f"<p align='left'><font color='{theme[level.value]}' size='3'>" \
                                f"[{level.value}] - {message}" \
                                f"</font></p>"
        elif level.value == LogLevel.ERROR.value:
            formatted_message = f"<p align='left'><font color='{theme[level.value]}' size='3'>" \
                                f"[{level.value}] - {message}" \
                                f"</font></p>"

        self.log_message.emit(formatted_message)

    def _task_stop(self):
        self.stop_flag = True
        self._format_msg(LogLevel.WARN, "⚠ ⚠ ⚠ 已停止任务执行!!!⚠ ⚠ ⚠ ")
        self._task_finished()  # 任务终止时，取消选中

    def _task_finished(self):
        # 判断是否有节点处于选中状态，如果有则取消选中
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        # 设置迭代器的选中标志，只迭代选中的节点
        iterator.IteratorFlags = QTreeWidgetItemIterator.Selected
        while iterator.value():
            item = iterator.value()
            item.setSelected(False)
            iterator += 1

    # ========================= 连接指令Qt对象信号的槽函数 =========================
    def on_cmd_running_error(self, message):
        """指令运行出错"""
        self._format_msg(LogLevel.ERROR, message)

    def on_cmd_running_progress(self, message):
        """指令运行进度"""
        self.progress_update.emit(message)
        self._format_msg(LogLevel.INFO, message)

    # ================================= 加载指令 =================================

    def extract_commands_from_tree(self) -> list:
        """从树控件中提取指令并实例化"""
        self.all_tasks_cmd.clear()
        self.task_name = self.tree_widget.headerItem().text(0) or "未命名任务"

        def extract_node_commands(item: QTreeWidgetItem) -> Optional[BaseCommand]:
            """
            从树节点中提取命令并实例化
            :param item: 树节点
            :return: 指令对象
            """

            if item is None:
                return None

            node_data = item.data(0, Qt.UserRole)
            if node_data is None:
                return None

            step_type = node_data.get("type")  # 当前指令类型
            action = node_data.get("action")  # 当前指令动作
            params = node_data.get("params", {})  # 当前指令参数

            if step_type == "trigger":
                return None

            command_class = self.command_map.get(step_type, {}).get(action)  # 获取指令类型

            if not command_class:
                self._format_msg(LogLevel.WARN, f"(extract_node_commands) 未知的指令类型或动作: {step_type}, {action}")
                return None

            # TODO: 创建指令对象并关联树节点
            try:
                if command_class == ImageOcrCmd:
                    # 如果是文字识别指令，需要提前加载模型
                    command = ImageOcrCmd(self._ocr, **params)
                elif command_class == ImageOcrClickCmd:
                    # 如果是文字点击指令，需要提前加载模型
                    command = ImageOcrClickCmd(self._ocr, **params)
                else:
                    # 其他指令
                    command = command_class(**params)  # **params 将字典转换为关键字参数

                command.tree_item = item  # 关联树节点
                # 连接指令对象的 Qt 对象信号
                command.q_obj.error_message.connect(self.on_cmd_running_error)
                command.q_obj.info_message.connect(self.on_cmd_running_progress)
                self._format_msg(LogLevel.INFO, f"(extract_node_commands) 已加载指令: &lt;{command.name}&gt;")

                # 如果当前节点是根节点，则将其添加到 all_tasks_cmd 中
                if item.parent() is None:
                    self.all_tasks_cmd.append(command)

                # 处理 If 指令
                if isinstance(command, IfCommand):
                    # 提取 then_commands 和 else_commands 节点, 并将其子节点转换为命令对象

                    # 初始化一个空列表来存储 then_commands
                    then_commands = []
                    # 获取 <If 判断> 指令节点的第一个子节点 <成立>
                    if_true_item = item.child(0)
                    # 获取 <成立> 节点的子节点数量
                    true_cmd_count = if_true_item.childCount()
                    # 遍历第一个子节点 <成立> 的所有子节点
                    for _ in range(true_cmd_count):
                        # 从 if_true_item 节点中提取命令并实例化
                        extracted_command = extract_node_commands(if_true_item.child(_))
                        # 将提取的命令添加到 then_commands 列表中
                        then_commands.append(extracted_command)
                    command.then_commands = then_commands

                    # 初始化一个空列表来存储 else_commands
                    else_commands = []
                    # 获取 <If 判断> 指令节点的第二个子节点 “不成立”
                    if_false_item = item.child(1)
                    # 获取 <不成立> 节点的子节点数量
                    false_cmd_count = if_false_item.childCount()
                    # 遍历第二个子节点的所有子节点
                    for _ in range(false_cmd_count):
                        # 从 if_false_item 节点中提取命令并实例化
                        extracted_command = extract_node_commands(if_false_item.child(_))
                        # 将提取的命令添加到 else_commands 列表中
                        else_commands.append(extracted_command)
                    command.else_commands = else_commands
                # 处理 Loop 指令
                elif isinstance(command, LoopCommand):
                    # 提取 loop_commands 节点, 并将其子节点转换为命令对象
                    loop_commands = []
                    loop_item = item.child(0)
                    loop_cmd_count = loop_item.childCount()
                    for _ in range(loop_cmd_count):
                        extracted_command = extract_node_commands(loop_item.child(_))
                        loop_commands.append(extracted_command)
                    command.loop_commands = loop_commands
                # 处理 Subtask 指令
                elif isinstance(command, SubtaskCommand):
                    # 提取 subtask_steps 节点, 并将其子节点转换为命令对象
                    subtask_steps = []
                    subtask_item = item.child(0)
                    subtask_cmd_count = subtask_item.childCount() if subtask_item else 0
                    for _ in range(subtask_cmd_count):
                        extracted_command = extract_node_commands(subtask_item.child(_))
                        subtask_steps.append(extracted_command)
                        # print("🔴🔴 子任务的步骤:", subtask_steps)
                    command.subtask_steps = subtask_steps
                return command
            except Exception as e:
                self._format_msg(LogLevel.ERROR, f"(extract_node_commands) 加载指令失败: {e}")
                return None

        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            extract_node_commands(top_item)

        self._format_msg(LogLevel.INFO, f"所有任务加载完毕，准备开始执行")
        self.log_message.emit("\n")
        print("加载的全部指令对象：\n", self.all_tasks_cmd) if _DEBUG else None
        return self.all_tasks_cmd

    # =================================== 运行全部 ===============================

    def execute_all_commands(self) -> None:
        """运行所有指令"""
        self._format_msg(LogLevel.INFO, f"🚀 -------------- 开始执行所有指令 -------------- 🚀")
        self.current_index = 0
        self.results_manager.clear()  # 清空之前的结果
        self._execute_from_current()

    # ============================== 从当前开始运行 ===============================

    def execute_from_command(self, index: int) -> None:
        """ 运行选中的顶层节点指令 """
        if self.all_tasks_cmd is None or len(self.all_tasks_cmd) == 0:
            self._format_msg(LogLevel.ERROR, "❌(execute_from_index) 无法运行，没有加载任何指令")
            return
        if index < 0 or index >= len(self.all_tasks_cmd):
            self._format_msg(LogLevel.ERROR, f"❌(execute_from_index) all_tasks_cmd 中无效的索引: {index}")
            return
        self._format_msg(LogLevel.INFO, f"🔽 ------------- 从步骤 {index + 1} 开始执行指令 ------------- 🔽")
        self.current_index = index
        self.results_manager.clear()  # 清空之前的结果
        self._execute_from_current()

    # ================================ 运行到当前 ===============================

    def execute_to_command(self, index: int) -> None:
        """ 从开始运行到当前选中的指令 """
        if self.all_tasks_cmd is None or len(self.all_tasks_cmd) == 0:
            self._format_msg(LogLevel.ERROR, "❌(execute_to_command) 无法运行，没有加载任何指令")
            return
        if index < 0 or index >= len(self.all_tasks_cmd):
            self._format_msg(LogLevel.ERROR, f"❌(execute_to_command) all_tasks_cmd 中无效的索引: {index}")
            return
        self._format_msg(LogLevel.INFO, f"▶ ------------- 开始执行到步骤 {index + 1} ------------- ◀")
        # 截取指令列表
        self.all_tasks_cmd = self.all_tasks_cmd[:index + 1]
        self.current_index = 0
        self.results_manager.clear()  # 清空之前的结果
        self._execute_from_current()

    # ================================= 指定运行 =================================

    def execute_selected_normal_command(self, item: QTreeWidgetItem) -> None:
        """运行选中的普通节点指令"""
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            self._format_msg(LogLevel.ERROR, "(execute_selected_normal_command) 无效的节点数据")
            return
        item_type = item_data.get("type")
        item_action = item_data.get("action")
        item_params = item_data.get("params", {})

        if item_type == "subtask" or (item_type == "flow" and item_action in ["if", "loop"]):
            self._format_msg(LogLevel.WARN, "⚠ 无法指定运行子任务或If、Loop指令")
            return

        if item_type == "trigger":
            self._format_msg(LogLevel.WARN, "⚠ 无法指定运行触发器指令")
            return

        command_class = self.command_map.get(item_type, {}).get(item_action)  # 获取指令类型
        if not command_class:
            self._format_msg(LogLevel.WARN,
                             f"(execute_selected_normal_command) ⚠ 未知的指令类型或动作: {item_type}, {item_action}")
            return

        try:
            if command_class == ImageOcrCmd:
                command = ImageOcrCmd(self._ocr, **item_params)
            elif command_class == ImageOcrClickCmd:
                command = ImageOcrClickCmd(self._ocr, **item_params)
            else:
                command = command_class(**item_params)
            command.tree_item = item  # 关联树节点
            # 连接指令对象的 Qt 对象信号
            command.q_obj.info_message.connect(lambda msg: self._format_msg(LogLevel.INFO, msg))
            command.q_obj.error_message.connect(lambda msg: self._format_msg(LogLevel.WARN, msg))
            if not command.is_active:
                self._format_msg(LogLevel.WARN, f"⚠ 指令: &lt;{command.name}&gt; 未激活, 跳过执行")
                return

            if isinstance(command, ImageMatchCmd) and \
                    os.path.exists(command.template_img) is False:
                self._format_msg(LogLevel.WARN, f"⚠ 指令: &lt;{command.name}&gt; 模板图片路径错误, 退出执行")
                return

            self._format_msg(LogLevel.INFO, f"👉 --------- 指定运行指令 --------- 👈")

            self._format_msg(LogLevel.INFO, f"开始执行: &lt;{command.name}&gt;")
            start_time = time.time()

            self.execute_one_command(command, self.current_index)  # 运行指令

            # 如果模板图片中心坐标存在，则输出
            if isinstance(command, ImageMatchCmd):
                if command.template_img_center:
                    self._format_msg(LogLevel.INFO, f"🖼模板图片中心坐标为{command.template_img_center}")
                else:
                    self._format_msg(LogLevel.WARN, f"⚠模板图片中心坐标未找到")
            # 如果OCR识别结果存在，则输出
            elif type(command) is ImageOcrCmd:
                if command.matching_boxes:
                    self._format_msg(LogLevel.INFO, f"✅ 文字识别匹配区域结果: {command.matching_boxes}")
                else:
                    self._format_msg(LogLevel.WARN, f"⚠ 未找到匹配区域")
            # 如果OCR点击结果存在，则输出
            elif type(command) is ImageOcrClickCmd:
                if command.matching_boxes_center:
                    self._format_msg(LogLevel.INFO, f"✅ 文字识别匹配区域结果: {command.matching_boxes}")
                    self._format_msg(LogLevel.INFO, f"✅ 文字识别点击中心坐标: {command.matching_boxes_center}")
                    self._format_msg(LogLevel.INFO, f"共计匹配成功 {len(command.matching_boxes)} 个区域")
                else:
                    self._format_msg(LogLevel.WARN, f"⚠ 未找到匹配区域")
            self._format_msg(LogLevel.INFO, f"执行耗时🕓: {time.time() - start_time:.5f} 秒")
            self._format_msg(LogLevel.INFO, f"🎉 --------- 指令执行完成 --------- 🎉")

        except CommandRunningException as cre:
            self._format_msg(LogLevel.ERROR, f"❌(execute_selected_normal_command) 指令执行出错: {cre}")
            return
        except Exception as e:
            self._format_msg(LogLevel.ERROR, f"❌(execute_selected_normal_command) 指令执行出错: {e}")

    def _execute_from_current(self) -> None:
        """从当前索引开始依次运行指令"""
        if self.stop_flag:
            return
        try:
            start_all_time = time.time()

            while self.current_index < len(self.all_tasks_cmd):
                if self.stop_flag:
                    return
                command = self.all_tasks_cmd[self.current_index]  # 从总指令列表中获取指定索引的指令

                # 如果指令不存在（触发器指令默认为None），则跳过
                if command is None:
                    self.current_index += 1  # 更新当前索引
                    continue

                # 如果模板图片路径不存在，则跳过
                if isinstance(command, ImageMatchCmd) and \
                        os.path.exists(command.template_img) is False:
                    self._format_msg(LogLevel.WARN, f"⚠ 指令: &lt;{command.name}&gt; 模板图片路径错误, 跳过执行")
                    self.current_index += 1  # 更新当前索引
                    continue

                self._format_msg(LogLevel.INFO, f"开始执行步骤 {self.current_index + 1}: &lt;{command.name}&gt;")
                start_time = time.time()

                self.execute_one_command(command, self.current_index)  # 运行单个指令

                # 如果模板图片中心坐标存在，则输出
                if isinstance(command, ImageMatchCmd):
                    if command.template_img_center:
                        self._format_msg(LogLevel.INFO, f"🖼 模板图片中心坐标为{command.template_img_center}")
                    else:
                        self._format_msg(LogLevel.WARN, f"⚠ 模板图片中心坐标未找到！")
                # 如果OCR识别结果存在，输出
                elif type(command) is ImageOcrCmd:
                    if command.matching_boxes:
                        self._format_msg(LogLevel.INFO, f"✅ 文字识别匹配区域结果: {command.matching_boxes}")
                    else:
                        self._format_msg(LogLevel.WARN, f"⚠ 未找到文字识别匹配区域！")
                # 如果OCR点击结果存在，则输出
                elif type(command) is ImageOcrClickCmd:
                    if command.matching_boxes_center:
                        self._format_msg(LogLevel.INFO, f"✅ 文字识别匹配区域结果: {command.matching_boxes}")
                        self._format_msg(LogLevel.INFO, f"✅ 文字识别点击中心坐标: {command.matching_boxes_center}")
                        self._format_msg(LogLevel.INFO, f"共计匹配成功 {len(command.matching_boxes)} 个区域")
                    else:
                        self._format_msg(LogLevel.WARN, f"⚠ 未找到文字识别匹配区域！")

                self._format_msg(LogLevel.INFO, f"执行耗时🕓: {time.time() - start_time:.3f} 秒")
                self._format_msg(LogLevel.INFO, "-" * 60)
                self.current_index += 1  # 更新当前索引

            self._format_msg(LogLevel.INFO,
                             f"🎉所有的 {self.results_manager.get_result_count()} 个指令运行完成, "
                             f"总耗时⏰: {time.time() - start_all_time:.3f} 秒🎉") if not self.stop_flag else None

            self.task_finished.emit()  # 发送任务完成信号, 以取消当前选中的节点

        except CommandRunningException as cre:
            self._format_msg(LogLevel.ERROR, f"❌指令运行时出错: {cre}")
        except Exception as e:
            self._format_msg(LogLevel.ERROR, f"❌执行任务时出错: {e}")

    # ------------------------------------ 单个指令执行方法 ----------------------------------

    def execute_one_command(self, command: BaseCommand, current_idx: int) -> None:
        """执行单个命令"""
        # 如果任务已停止，则不执行
        if self.stop_flag:
            return
        # 如果指令不存在（触发器指令默认为None），则不执行
        if command is None:
            return
        # 如果指令未激活，则不执行
        if not command.is_active:
            self._format_msg(LogLevel.WARN, f"⚠ 指令: &lt;{command.name}&gt; 未激活, 跳过执行")
            return

        try:
            # 获取当前节点
            current_node = getattr(command, "tree_item", None)

            # ------------------- 发送选中信号 -------------------
            if current_node:
                self._format_msg(LogLevel.INFO, f"选中指令: &lt;{current_node.text(0)}&gt;")
                # 展开当前节点
                self.tree_widget.expandAll()
                # 选中当前节点
                self.select_node.emit(current_node)
            else:
                self._format_msg(LogLevel.WARN, f"⚠ 指令 &lt;{command.name}&gt; 的 tree_item 为None，无法选中当前节点")

            # -------------------- 执行指令 --------------------

            if isinstance(command, IfCommand):
                self._execute_if_command(command, current_idx)
            elif isinstance(command, LoopCommand):
                self._execute_loop_command(command, current_idx)
            elif isinstance(command, SubtaskCommand):
                self._execute_subtask_command(command, current_idx)
            else:
                command.execute()
                self.results_manager.add_result(
                    command.id,
                    command.name,
                    command.model_dump()
                )
        except CommandRunningException as cre:
            self._format_msg(LogLevel.ERROR, f"❌(运行时错误) 执行指令 &lt;{command.name}&gt; 失败: {cre}")
        except Exception as e:
            self._format_msg(LogLevel.ERROR, f"❌(未知错误) 执行指令 &lt;{command.name}&gt; 失败: {e}")

    def _execute_if_command(self, command: IfCommand, current_idx: int) -> None:
        """执行 If 命令"""
        if self.stop_flag:
            return
        if not command.is_active:
            self._format_msg(LogLevel.WARN, f"⚠ 指令: &lt;{command.name}&gt; 未激活, 跳过执行")
            return
        # 使用更安全的方式解析条件表达式，避免使用 eval
        condition_result = self.evaluate_condition(command.condition)

        # 根据条件的结果选择执行的代码块
        block = command.then_commands if condition_result else command.else_commands

        # 打印日志，表明条件是否成立
        self._format_msg(LogLevel.INFO, f"{'✔ 条件成立' if condition_result else '❌ 条件不成立'}，执行对应代码块")

        # 遍历并执行选中的代码块中的子命令
        for subcommand in block:
            self.execute_one_command(subcommand, current_idx)

    def _execute_loop_command(self, command: LoopCommand, current_idx: int) -> None:
        """执行 Loop 命令"""
        if self.stop_flag:
            return
        if not command.is_active:
            self._format_msg(LogLevel.WARN, f"⚠ 指令: &lt;{command.name}&gt; 未激活, 跳过执行")
            return
        for i in range(command.count):
            if self.stop_flag:
                return
            self._format_msg(LogLevel.INFO, f"开始执行循环步骤 (第 {i + 1} 次)")
            for subcommand in command.loop_commands:
                self.execute_one_command(subcommand, current_idx)

    def _execute_subtask_command(self, command: SubtaskCommand, current_idx: int) -> None:
        """执行子任务命令"""
        if self.stop_flag:
            return
        if not command.is_active:
            self._format_msg(LogLevel.WARN, f"⚠ 指令: &lt;{command.name}&gt; 未激活, 跳过执行")
            return
        for subcommand in command.subtask_steps:
            self.execute_one_command(subcommand, current_idx)

    def evaluate_condition(self, condition: str) -> bool:
        """
        根据给定的条件字符串生成一个可执行的判断逻辑。
        使用指令的 `id` 来确定对应的指令。
        """

        def get_command_by_id(_cmd_id):
            """通过指令 id 获取对应的指令执行结果"""
            # for result in self.results_list:
            #     if result.get("id") == _cmd_id:
            #         return result
            # return None
            result = self.results_manager.get_result(_cmd_id)
            return result.result_data if result else None

        def safe_get_field(_cmd_result, _field_name):
            """安全地获取指令结果中的字段值"""
            if not _cmd_result:
                return None
            return _cmd_result.get(_field_name)

        try:
            # 从条件字符串解析出指令 id 和字段
            # 条件格式为: results_list['<id>']['<field>'] <operator> <value>
            # eg: "results_list['12345678']['status'] == 2"
            parts = condition.split(" ")
            if len(parts) != 3:
                self._format_msg(LogLevel.ERROR, "❌ 条件表达式格式错误")
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
                self._format_msg(LogLevel.ERROR, f"❌ 不支持的操作符: {operator_symbol}")
                return False

            # 执行判断
            return operation(field_value, right_value)
        except Exception as e:
            self._format_msg(LogLevel.ERROR, f"❌ 条件解析失败: {e}")
            return False

    # ------------------------------------ 线程运行入口 ----------------------------------

    def run(self):
        """线程运行入口"""

        if self.run_action == "run_all":
            self.extract_commands_from_tree()  # TODO: 应该在每次用户放置好一个指令节点后就提取指令
            self.execute_all_commands()  # 运行所有指令
        elif self.run_action == "run_one":
            current_item = self.tree_widget.currentItem()  # 获取当前选中的节点
            self.execute_selected_normal_command(current_item)  # 运行选中的节点
        elif self.run_action == "run_from_now":
            current_item = self.tree_widget.currentItem()  # 获取当前选中的节点
            index = self.tree_widget.indexOfTopLevelItem(current_item)
            self.extract_commands_from_tree()  # 提取指令
            self.execute_from_command(index)  # 运行选中的顶层节点
        elif self.run_action == "run_to_now":
            current_item = self.tree_widget.currentItem()  # 获取当前选中的节点
            index = self.tree_widget.indexOfTopLevelItem(current_item)
            self.extract_commands_from_tree()  # 提取指令
            self.execute_to_command(index)  # 运行到选中的顶层节点
        elif self.run_action == "attr_bind":
            self.extract_commands_from_tree()  # 提取指令不执行
        else:
            self._format_msg(LogLevel.ERROR, "❌无效的运行动作!")
            return

    def stop(self):
        """停止线程运行"""
        self.task_stop.emit()  # 发送任务停止信号
