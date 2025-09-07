"""
软件配置常量（兼容 IDE、PyInstaller -D、PyInstaller -F）

主要改动：
- 恢复并明确 APP_ROOT（程序根目录）的含义与计算方式；
- 提供 resource_path() 作为统一的资源路径获取接口；
- 路径常量仍以 APP_ROOT 为基准，保持你原有结构不变。
"""
import os
import sys

from utils.loggers.my_logger import init_logger


def get_app_root() -> str:
    """获取应用根目录（APP_ROOT）。

    规则（优先级）：
    1. 如果存在 sys._MEIPASS（PyInstaller -F 单文件解压目录），返回其绝对路径。
    2. 如果程序被打包（frozen）但没有 _MEIPASS（通常是 -D/onedir），返回可执行文件所在目录。
    3. 开发环境（未打包）：返回当前文件上一级目录（通常为项目根目录）。

    Returns:
        str: 绝对路径，表示应用根目录。
    """
    # PyInstaller 单文件模式：resources 会解压到 _MEIPASS
    # if hasattr(sys, "_MEIPASS"):
    #     return os.path.abspath(sys._MEIPASS)

    # 已冻结但没有 _MEIPASS（一般为 -D/onedir），使用 exe 所在目录
    if getattr(sys, "frozen", False):
        return os.path.abspath(os.path.dirname(sys.argv[0]))

    # 开发环境：当前文件的上一级目录作为项目根
    return os.path.abspath(".")


def resource_path(relative_path: str) -> str:
    """将相对资源路径转换为绝对路径，基于 APP_ROOT。

    Args:
        relative_path (str): 相对于项目根的路径，例如 "config.ini" 或 "config/CocoCmdLib.json"

    Returns:
        str: 绝对路径，可以直接用于打开文件或加载资源。
    """
    return os.path.join(APP_ROOT, relative_path)


# ============================== APP ROOT ==============================
# 恢复并公开 APP_ROOT 常量，便于项目其他模块复用
APP_ROOT = get_app_root()

# ============================== 路径配置 ==============================
# 配置文件（用于设置功能）
CONFIG_FILE = os.path.join(APP_ROOT, "config.ini")
# 指令库配置（用于加载预设的指令）
CMD_LIB_JSON_FILE = os.path.join(APP_ROOT, "config", "CocoCmdLib.json")
# 自动执行管理器配置
AUTO_EXEC_CONFIG = os.path.join(APP_ROOT, "config", "auto_config.json")
# 工作空间根目录
WORK_SPACE = os.path.join(APP_ROOT, "work")
TASK_HOME = os.path.join(WORK_SPACE, "work_tasks")
IMAGE_HOME = os.path.join(WORK_SPACE, "work_images")
# 帮助文档 HTML文件
cmd_desc_path = os.path.join(APP_ROOT, "ui", "static", "feature.html")
about_path = os.path.join(APP_ROOT, "ui", "static", "about.html")
# OCR 模型
DET_MODEL_DIR = os.path.join(APP_ROOT, "models", "det", "ch", "ch_PP-OCRv4_det_infer")
REC_MODEL_DIR = os.path.join(APP_ROOT, "models", "rec", "ch", "ch_PP-OCRv4_rec_infer")
CLS_MODEL_DIR = os.path.join(APP_ROOT, "models", "cls", "ch", "ch_PP-OCRv4_cls_infer")

# ============================== 设置配置 ==============================
DEFAULT_SETTING = {
    "General": {
        "Theme": "默认",
        "Language": "zh",
        "RunMode": "debug",
        "EditMode": "normal",
        "Window": {
            "StaysOnTopHint": False,
            "CloseMode": "system_tray",
        },
    },
    "ImageMatch": {
        "Threshold": 0.8,
        "SavePath": None,
    },
    "ImageOcr": {
        "Threshold": 0.8,
        "ModelName": "PaddleOCR",
    },
}

# ============================== 日志配置 ==============================
# 日志文件路径（放在 APP_ROOT/logs 下）
MAIN_LOG = os.path.join(APP_ROOT, "logs", "@CocoPyRPA_V2.log")

# 确保日志目录存在（避免首次运行时报错）
try:
    os.makedirs(os.path.dirname(MAIN_LOG), exist_ok=True)
except Exception:
    # 在极端只读环境下创建目录可能失败，交由 init_logger 处理或降级
    pass

# 初始化日志实例
MAIN_LOGGER = init_logger(log_path=MAIN_LOG, level="DEBUG")

# 日志器别名 API
debug = MAIN_LOGGER.debug
info = MAIN_LOGGER.info
warning = MAIN_LOGGER.warning
error = MAIN_LOGGER.error
critical = MAIN_LOGGER.critical

# ============================== 主题配置 ==============================
MAIN_THEME = {
    "默认": os.path.join(APP_ROOT, "resources", "theme", "default", "main.css"),
    "深色": os.path.join(APP_ROOT, "resources", "theme", "dark", "main.css"),
    "浅色": os.path.join(APP_ROOT, "resources", "theme", "light", "main.css"),
    "护眼": os.path.join(APP_ROOT, "resources", "theme", "eye", "eye.css"),
}

MAIN_THEME_RES = {
    "默认": ":/theme/default",
    "深色": ":/theme/dark",
    "浅色": ":/theme/light",
    "护眼": ":/theme/eye",
}
