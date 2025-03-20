"""
@author: 54Coconi
@data: 2024-12-10
@version: 1.0.0
@path: core/safe_globals.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    - 用于管理 Python 代码执行环境中的
    安全全局变量
"""

from typing import Dict, Any, Optional
from functools import lru_cache


def analyze_code_safety(code: str) -> bool:
    """分析代码安全性"""
    import ast

    class SecurityVisitor(ast.NodeVisitor):
        """ 代码安全性检查访问者 """

        def __init__(self):
            self.has_dangerous_ops = False

        def visit_Call(self, node):
            """ 访问 Call 节点 """
            if isinstance(node.func, ast.Attribute):
                if node.func.attr.startswith('_'):
                    self.has_dangerous_ops = True
            self.generic_visit(node)

    try:
        tree = ast.parse(code)
        visitor = SecurityVisitor()
        visitor.visit(tree)
        return not visitor.has_dangerous_ops
    except SyntaxError:
        return False


def execute_with_timeout(code: str, globals_dict: dict, locals_dict: dict, timeout: float = 5.0):
    """带超时控制的代码执行

    该函数用于在指定的全局和局部变量环境下执行一段代码，并设置执行的超时时间
    如果代码在指定时间内未执行完毕，将抛出TimeoutError异常

    :param code: 待执行的代码字符串
    :param globals_dict: 全局变量字典
    :param locals_dict: 局部变量字典
    :param timeout: 代码执行的超时时间，默认为5秒
    """
    import signal

    def handler(signum, frame):
        """
        超时处理函数
        当代码执行超过指定时间后，该函数将被调用，抛出TimeoutError异常

        :param signum: 信号编号
        :param frame: 当前的帧对象
        """
        raise TimeoutError("代码执行超时")

    # 设置信号处理器，当指定时间后未执行完毕，发送SIGALRM信号
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(int(timeout))

    try:
        exec(code, globals_dict, locals_dict)
    finally:
        # 无论代码执行是否完成，都取消闹钟，防止遗留的信号影响其他操作
        signal.alarm(0)


def limit_memory(max_bytes):
    """
    限制进程的内存使用。

    本函数通过设置进程的最大地址空间限制来达到限制内存使用的目的
    这对于防止由于内存泄漏或无意中使用过多内存而导致的程序崩溃非常有用

    参数:
    max_bytes (int): 内存的最大字节数限制。这将同时作为软限制和硬限制

    返回:
    无返回值
    """
    # 导入resource模块，它提供了与系统资源相关的功能，如设置和获取系统资源限制
    import resource

    # 设置进程的最大地址空间限制，以限制内存使用
    # 参数resource.RLIMIT_AS表示地址空间的限制
    # (max_bytes, max_bytes)表示软限制和硬限制都设置为max_bytes
    resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))


class SafeGlobalsManager:
    """管理安全的全局变量环境"""

    # 基础内置函数白名单
    SAFE_BUILTINS = {
        "__import__": __import__,
        "abs": abs,
        "min": min,
        "max": max,
        "len": len,
        "range": range,
        "print": print,
        "str": str,
        "int": int,
        "float": float,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "sum": sum,
        "all": all,
        "any": any,
        "zip": zip,
        "enumerate": enumerate,
        "round": round,
        "sorted": sorted,
        "filter": filter,
        "map": map,
        "bool": bool,
        "isinstance": isinstance,
        "type": type,
    }

    # 安全模块白名单
    SAFE_MODULES = {
        "time": ["sleep", "time", "strftime", "strptime"],
        "math": None,  # None 表示导入所有
        "random": ["random", "randint", "choice", "shuffle"],
        "datetime": ["datetime", "date", "time", "timedelta"],
        "json": ["loads", "dumps"],
        "copy": ["copy", "deepcopy"],
        "re": ["search", "findall", "sub", "split", "match", "fullmatch", "finditer"],
        "numpy": None,
        "cv2": None,
        "pyautogui": None,
    }

    # 禁止使用的模块黑名单
    BLOCKED_MODULES = {
        "os": None,
        "sys": None,
        "subprocess": None,
        "socket": None,
        "requests": None,
        "urllib": None,
    }

    def __init__(self):
        self._command_classes = {}  # 自动化指令类
        self._custom_classes = {}  # 自定义类
        self._custom_functions = {}  # 自定义函数

    def register_command(self, name: str, command_class: Any) -> None:
        """注册自动化指令类"""
        self._command_classes[name] = command_class

    def register_custom_class(self, name: str, custom_class: Any) -> None:
        """注册自定义类"""
        self._custom_classes[name] = custom_class

    def register_custom_function(self, name: str, func: callable) -> None:
        """注册自定义函数"""
        self._custom_functions[name] = func

    @lru_cache(maxsize=1)
    def get_safe_globals(self) -> Dict[str, Any]:
        """
        获取安全的全局变量环境
        使用 lru_cache 避免重复创建
        """
        safe_globals = {
            "__builtins__": self.SAFE_BUILTINS.copy()
        }

        # 导入安全模块，根据允许的属性列表进行筛选
        for module_name, allowed_attrs in self.SAFE_MODULES.items():
            try:
                module = __import__(module_name)
                if allowed_attrs is None:
                    safe_globals[module_name] = module
                else:
                    safe_module = {}
                    for attr in allowed_attrs:
                        if hasattr(module, attr):
                            safe_module[attr] = getattr(module, attr)
                    # 创建一个带有安全属性的模块类
                    safe_globals[module_name] = type(module_name, (), safe_module)
            except ImportError:
                continue

        # 添加禁止模块
        safe_globals.update({name: None for name in self.BLOCKED_MODULES})

        # 添加已注册的指令类 BaseCommand
        safe_globals.update(self._command_classes)

        # 添加自定义类
        safe_globals.update(self._custom_classes)

        # 添加自定义函数
        safe_globals.update(self._custom_functions)

        return safe_globals

    def create_restricted_exec_env(self, additional_globals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建受限制的执行环境，可以添加额外的全局变量
        """
        globals_dict = self.get_safe_globals()
        if additional_globals:
            globals_dict.update(additional_globals)
        return globals_dict


# 创建全局单例实例
safe_globals_manager = SafeGlobalsManager()
