"""
自定义日志模块，支持自定义多个日志文件路径、控制台日志级别颜色
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Literal

# 全局变量
_loggers = {}  # key: log_path, value: Logger instance
DEFAULT_LOG_PATH = r"logs/@CocoPyRPA.log"
LEVEL = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# 添加 Windows 终端颜色支持
if os.name == 'nt':
    os.system('')


class ColorFormatter(logging.Formatter):
    """为日志添加颜色支持"""
    COLOR_CODES = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[31m',
        'RESET': '\033[0m'
    }

    def format(self, record):
        """格式化日志记录"""
        caller_name = getattr(record, 'caller', record.module)
        record.caller = f'{caller_name}'
        color_code = self.COLOR_CODES.get(record.levelname, '')
        record.color_start = color_code
        record.color_end = self.COLOR_CODES["RESET"]
        return super().format(record)


def init_logger(name=__name__, log_path=DEFAULT_LOG_PATH, level: LEVEL = "DEBUG"):
    """
    初始化日志器，支持多个日志路径。
    
    该函数创建并配置一个日志记录器，支持同时输出到控制台和文件。控制台输出带有颜色标记，
    文件输出采用轮转方式防止文件过大。日志器会缓存以避免重复创建。
    
    Args:
        name: 日志器名称，默认为当前模块名
        log_path: 日志文件路径，默认为 DEFAULT_LOG_PATH
        level: 日志级别，可选值为 "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"，默认为 "DEBUG"

    Return:
        配置好的 Logger 实例
    """
    print(f"(init_logger) - 初始化日志器，日志路径：{log_path}")
    abs_log_path = os.path.abspath(log_path)  # 获取绝对路径
    unique_name = f"{name}_{abs_log_path.replace(os.path.sep, '_')}"  # 唯一名称

    # 创建日志记录器
    logger = logging.getLogger(unique_name)
    logger.setLevel(LEVEL_MAP[level])  # 设置日志级别
    logger.propagate = False  # 禁止向父 logger 传递日志

    # 移除所有现有处理器（避免重复日志）
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 清除根日志记录器的处理器，防止第三方库添加的处理器导致重复输出
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 初始化控制台 handler
    console_handler = logging.StreamHandler()
    console_formatter = ColorFormatter(
        "%(asctime)s - %(color_start)s[%(levelname)s](%(filename)s:%(lineno)d)%(color_end)s - %(message)s",
        "%Y/%m/%d %H:%M:%S")
    console_handler.setFormatter(console_formatter)
    # 添加控制台 handler
    logger.addHandler(console_handler)

    # 初始化文件 handler
    try:
        log_dir = os.path.dirname(abs_log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            abs_log_path,
            mode='w',  # 覆盖模式
            maxBytes=10 * 1024 * 1024,  # 10MB，maxBytes>0 时 mode='a'
            backupCount=5,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter("%(asctime)s - [%(levelname)s](%(filename)s:%(lineno)d) - %(message)s",
                                           "%Y/%m/%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        # 添加文件 handler
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"[警告] 无法为 {abs_log_path} 创建文件处理程序：{e}")

    # 缓存日志器
    _loggers[abs_log_path] = logger
    return logger


def get_logger(log_path=DEFAULT_LOG_PATH):
    """
    获取或创建日志器实例。
    
    该函数用于获取指定路径的日志器实例。如果该路径的日志器尚未创建，
    则会自动调用 init_logger 函数创建新的日志器实例并缓存。

    Args:
        log_path: 日志文件路径，默认为 DEFAULT_LOG_PATH

    Returns:
        指定路径对应的 Logger 实例
    """
    abs_log_path = os.path.abspath(log_path)
    if abs_log_path not in _loggers:
        init_logger(log_path=abs_log_path)
    return _loggers[abs_log_path]


# 简化 API
def log_debug(message, log_path=DEFAULT_LOG_PATH):
    """
    记录 DEBUG 级别的日志信息。
    
    该函数用于记录调试级别的日志信息，通常用于记录程序运行过程中的详细信息，
    便于调试和诊断问题。
    
    Args:
        message: 要记录的日志消息内容
        log_path: 日志文件路径，默认为 DEFAULT_LOG_PATH

    Returns:
        None
    """
    logger = get_logger(log_path)
    logger.debug(message)


def log_info(message, log_path=DEFAULT_LOG_PATH):
    """
    记录 INFO 级别的日志信息。
    
    该函数用于记录信息级别的日志，通常用于记录程序运行过程中的一般信息，如程序启动、关键操作完成等。
    
    Args:
        message: 要记录的日志消息内容
        log_path: 日志文件路径，默认为 DEFAULT_LOG_PATH
        
    Returns:
        None
    """
    logger = get_logger(log_path)
    logger.info(message)


def log_warning(message, log_path=DEFAULT_LOG_PATH):
    """
    记录 WARNING 级别的日志信息。
    
    该函数用于记录警告级别的日志信息，通常用于记录程序运行过程中出现的可预见的问题或异常情况，
    这些问题不会导致程序终止但仍需引起注意。
    
    Args:
        message: 要记录的日志消息内容
        log_path: 日志文件路径，默认为 DEFAULT_LOG_PATH
        
    Returns:
        None
    """
    logger = get_logger(log_path)
    logger.warning(message)


def log_error(message, log_path=DEFAULT_LOG_PATH):
    """
    记录 ERROR 级别的日志信息。
    
    该函数用于记录错误级别的日志信息，通常用于记录程序运行过程中发生的错误，
    这些错误会导致某些功能无法正常执行，但程序仍可继续运行。
    
    Args:
        message: 要记录的日志消息内容
        log_path: 日志文件路径，默认为 DEFAULT_LOG_PATH
        
    Returns:
        None
    """
    logger = get_logger(log_path)
    logger.error(message)


def log_critical(message, log_path=DEFAULT_LOG_PATH):
    """
    记录 CRITICAL 级别的日志信息。
    
    该函数用于记录严重错误级别的日志信息，通常用于记录程序运行过程中发生的严重错误，
    这些错误可能导致程序无法继续正常运行。
    
    Args:
        message: 要记录的日志消息内容
        log_path: 日志文件路径，默认为 DEFAULT_LOG_PATH
        
    Returns:
        None
    """
    logger = get_logger(log_path)
    logger.critical(message)


# 测试代码
if __name__ == "__main__":
    # 默认路径日志
    log_info("这是默认日志记录, 来自 main 函数")

    # 自定义路径日志
    log_info("这条信息写入 custom_logs/custom.log - 来自 main 函数", "custom_logs/custom.log")

    # 不同路径日志
    log_debug("调试信息写入 log1.log", "logs/log1.log")
    log_error("错误信息写入 log2.log", "logs/log2.log")
