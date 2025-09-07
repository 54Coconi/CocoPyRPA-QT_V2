"""
启动主窗口

# "      ______                 ____       ____   ____  ___                        "
# "     / ____/___  _________  / __ \__ __/ __ \ / __ \/   |       _      __ ___   "
# "    / /   / __ \/ ___/ __ \/ /_/ / / / / /_/ / /_/ / /| |      | |    / / ___ \\"
# "   / /___/ /_/ / /__/ /_/ / ____/ /_/ / _, _/ ____/ ___ |      | |   / / ___/ / "
# "   \____/\____/\___/\____/_/    \__, /_/ |_/_/   /_/  |_|      | |  / / / ___/  "
# "                               /____/                          | ___ / /_____/  "
"""
import ctypes
import sys

# 修复 Windows DPI 缩放导致的截图比例异常
# ---------------------------------------------------------
#                           Note
# ---------------------------------------------------------
# 如果进程在启动时没有声明自己是 DPI aware，
# 那么 Windows 会给它一个缩放后的虚拟坐标系，
# mss 截到的图是经过缩放补偿的，结果可能出现黑边或比例异常
# 所以需要在导入 PyQt5 之前设置每个显示器的 DPI 感知模式
if sys.platform.startswith("win"):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # Windows 7 fallback
        except Exception:
            pass

from PyQt5.QtWidgets import QApplication

from config.app_config import MAIN_THEME
from ui.main_window import CocoPyRPA_v2
from ui.widgets.CocoSettingWidget import config_manager

from utils.QSSLoader import QSSLoader as QL


_DEBUG = True


def load_main_theme() -> str:
    """
    加载主窗口主题
    :return: 主窗口主题 CSS 文件路径
    """
    theme = config_manager.config.get("General", {}).get("Theme", "默认")
    return MAIN_THEME[theme]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = CocoPyRPA_v2()
    # ------------------------------------------------------------------

    # 通过文件加载 css 样式资源
    mainWindow.setStyleSheet(QL.read_qss_file(load_main_theme()))

    # TODO: 通过资源加载 css 样式资源
    # sty_f = QtCore.QFile(":/theme/dark")
    # sty_f.open(QtCore.QIODevice.ReadOnly)
    # mainWindow.setStyleSheet(((sty_f.readAll()).data()).decode("latin1"))

    # ------------------------------------------------------------------
    mainWindow.show()
    sys.exit(app.exec_())
