""" 调试工具模块 """

import inspect  # 用于获取当前堆栈帧
import os
import threading
import time
from functools import wraps  # 用于装饰器
from typing import Any, Callable, Dict

_DEBUG = True


# 打印指令对象属性(不包括私有属性)
def print_command(obj: Any):
    """
    自动获取对象的变量名，并以指定格式打印对象的属性信息。
    :param  obj: (BaseCommand): 需要打印的指令对象
    """
    # 获取当前堆栈帧的信息
    frame = inspect.currentframe()
    try:
        # 获取上层调用环境中的局部变量
        local_vars = frame.f_back.f_locals
        # 通过值找到变量名（获取第一个匹配的变量名）
        obj_name = next(name for name, val in local_vars.items() if val is obj)
    except StopIteration:
        obj_name = "unknown_object"  # 如果找不到变量名则使用默认名称
    finally:
        del frame  # 避免循环引用

    # 获取对象的属性字典格式
    attributes_str = ",\n    ".join([f"{key}: {value!r}" for key, value in obj.model_dump().items()])
    # 按指定格式打印对象信息
    print(f"object: {obj_name} -> class: {obj.__class__.__name__}(\n{{\n    {attributes_str}\n}})")


# 打印函数运行时间
def print_func_time(debug=_DEBUG):
    """
    打印函数运行时间的装饰器。
    :param debug: 是否启用运行时间计算和打印，默认为 True
    :return: 装饰器函数
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if debug:
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                print("\n" + "=" * 100)
                # 打印函数所在的文件名、类名、函数名
                file_name = os.path.basename(func.__code__.co_filename)
                class_name = func.__qualname__
                function_name = func.__name__
                print(" " * 5, f"函数 [{file_name}->{class_name}()]"
                               f"运行时间为 {(end_time - start_time):.5f} s")
                print("=" * 100 + "\n")
            else:
                result = func(*args, **kwargs)
            return result

        return wrapper

    # 如果装饰器直接应用而没有参数
    if callable(debug):
        return decorator(debug)
    # 如果装饰器有参数，则返回装饰器函数
    return decorator


# 全局计数器（线程安全）
_call_counts: Dict[str, int] = {}
_lock = threading.Lock()


def _get_func_identity(func: Callable) -> str:
    """安全获取函数唯一标识（含模块、类、文件、行号）"""
    func_module = getattr(func, "__module__", "<unknown_module>")
    func_qualname = getattr(func, "__qualname__", getattr(func, "__name__", "<unknown_func>"))

    try:
        source_file = inspect.getsourcefile(func) or "<unknown_file>"
        _, start_line = inspect.getsourcelines(func)
    except (OSError, TypeError):
        source_file, start_line = "<unknown_file>", -1

    return f"{func_module}.{func_qualname} ({source_file}:{start_line})"


def timeit(func: Callable) -> Callable:
    """计算函数执行耗时的装饰器"""
    func_key = _get_func_identity(func)

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = (time.perf_counter() - start) * 1000
        print(f"[timeit] {func_key} 执行耗时: {duration:.3f} ms")
        return result

    return wrapper


def count_calls(func: Callable) -> Callable:
    """统计函数调用次数的装饰器"""
    func_key = _get_func_identity(func)

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        with _lock:
            _call_counts[func_key] = _call_counts.get(func_key, 0) + 1
            count = _call_counts[func_key]
        print(f"[count_calls] {func_key} 已被调用 {count} 次")
        return func(*args, **kwargs)

    return wrapper


def log_args(func: Callable) -> Callable:
    """记录函数参数和返回值的装饰器"""
    func_key = _get_func_identity(func)

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        print(f"[log_args] {func_key} 参数: args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"[log_args] {func_key} 返回: {result}")
        return result

    return wrapper


def debug(log_time: bool = True, log_count: bool = True, log_io: bool = True) -> Callable:
    """组合调试装饰器"""

    def decorator(func: Callable) -> Callable:
        if log_io:
            func_wrapped = log_args(func)
        else:
            func_wrapped = func
        if log_count:
            func_wrapped = count_calls(func_wrapped)
        if log_time:
            func_wrapped = timeit(func_wrapped)
        return func_wrapped

    return decorator


if __name__ == '__main__':
    @timeit
    def foo(x, y):
        return x + y

    @debug(log_time=True, log_count=True, log_io=True)
    def bar(n):
        return sum(range(n))

    print(foo(3, 4))
    print(bar(10))
    print(bar(20))
