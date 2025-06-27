"""
启动主窗口

# LOGO1 = "      ______                 ____       ____   ____  ___                        "
# LOGO2 = "     / ____/___  _________  / __ \__ __/ __ \ / __ \/   |       _      __ ___   "
# LOGO3 = "    / /   / __ \/ ___/ __ \/ /_/ / / / / /_/ / /_/ / /| |      | |    / / ___ \\"
# LOGO4 = "   / /___/ /_/ / /__/ /_/ / ____/ /_/ / _, _/ ____/ ___ |      | |   / / ___/ / "
# LOGO5 = "   \____/\____/\___/\____/_/    \__, /_/ |_/_/   /_/  |_|      | |  / / / ___/  "
# LOGO6 = "                               /____/                          | ___ / /_____/  "
"""
import sys

from PyQt5.QtCore import QFile, QObject, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication

from ui.main_window import CocoPyRPA_v2
from ui.widgets.CocoSettingWidget import config_manager

from utils.QSSLoader import QSSLoader as QL

import resources_rc


MAIN_THEME = {
    "默认": "resources/theme/default/main.css",
    "深色": "resources/theme/dark/main.css",
    "浅色": "resources/theme/light/main.css",
    "护眼": "resources/theme/eye/eye.css"
}

MAIN_THEME_RES = {
    "默认": ":/theme/default",
    "深色": ":/theme/dark",
    "浅色": ":/theme/light",
    "护眼": ":/theme/eye"
}


def load_main_theme() -> str:
    """
    加载主窗口主题
    :return: 主窗口主题 CSS 文件路径
    """
    theme = config_manager.config.get("General", {}).get("Theme", "深色")
    return MAIN_THEME[theme]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = CocoPyRPA_v2()
    # ------------------------------------------------------------------

    # 通过文件加载 qss 样式资源
    mainWindow.setStyleSheet(QL.read_qss_file(load_main_theme()))

    # 通过资源加载qss样式资源
    # sty_f = QtCore.QFile(":/theme/dark")
    # sty_f.open(QtCore.QIODevice.ReadOnly)
    # mainWindow.setStyleSheet(((sty_f.readAll()).data()).decode("latin1"))

    # ------------------------------------------------------------------
    mainWindow.show()
    sys.exit(app.exec_())
