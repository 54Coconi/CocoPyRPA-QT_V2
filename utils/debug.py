# -*- coding: utf-8 -*- debug.py
""" 调试工具模块 """
import os
import time
import inspect  # 用于获取当前堆栈帧
from functools import wraps

from core.commands.base_command import BaseCommand

_DEBUG = True


# 打印指令对象属性(不包括私有属性)
def print_command(obj: BaseCommand):
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
