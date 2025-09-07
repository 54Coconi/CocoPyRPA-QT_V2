"""
软件配置常量
"""
import os

from utils.loggers.my_logger import init_logger

# ============================== 路径配置 ==============================
APP_ROOT = os.path.dirname(os.path.dirname(__file__))
# 配置文件（用于设置功能）
CONFIG_FILE = os.path.join(APP_ROOT, 'config.ini')
# 指令库配置（用于加载预设的指令）
CMD_LIB_JSON_FILE = os.path.join(APP_ROOT, 'config/CocoCmdLib.json')
# 自动执行管理器配置
AUTO_EXEC_CONFIG = os.path.join(APP_ROOT, 'config/auto_config.json')
# 工作空间根目录
WORK_SPACE = os.path.join(APP_ROOT, 'work')
TASK_HOME = os.path.join(WORK_SPACE, 'work_tasks')
IMAGE_HOME = os.path.join(WORK_SPACE, 'work_images')
# 帮助文档 HTML文件
cmd_desc_path = os.path.join(APP_ROOT, 'ui/static/feature.html')
about_path = os.path.join(APP_ROOT, 'ui/static/about.html')
# OCR 模型
DET_MODEL_DIR = os.path.join(APP_ROOT, 'models/det/ch/ch_PP-OCRv4_det_infer')
REC_MODEL_DIR = os.path.join(APP_ROOT, 'models/rec/ch/ch_PP-OCRv4_rec_infer')
CLS_MODEL_DIR = os.path.join(APP_ROOT, 'models/cls/ch/ch_PP-OCRv4_cls_infer')

# ============================== 设置配置 ==============================
# 默认配置
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
# 日志文件路径
MAIN_LOG = r'logs/@CocoPyRPA_V2.log'
# 初始化日志实例
MAIN_LOGGER = init_logger(log_path=MAIN_LOG, level='DEBUG')
# 日志器别名 API
debug = MAIN_LOGGER.debug
info = MAIN_LOGGER.info
warning = MAIN_LOGGER.warning
error = MAIN_LOGGER.error
critical = MAIN_LOGGER.critical

# ============================== 主题配置 ==============================
# 主窗口主题样式表
MAIN_THEME = {
    "默认": "resources/theme/default/main.css",
    "深色": "resources/theme/dark/main.css",
    "浅色": "resources/theme/light/main.css",
    "护眼": "resources/theme/eye/eye.css"
}
# 主窗口主题资源路径
MAIN_THEME_RES = {
    "默认": ":/theme/default",
    "深色": ":/theme/dark",
    "浅色": ":/theme/light",
    "护眼": ":/theme/eye"
}
