"""
主题管理器模块

该模块提供了主题管理功能，支持动态切换应用程序的主题
支持从 app_root/resources/theme 目录下加载不同的主题样式表
"""

from pathlib import Path
from typing import Optional, Dict

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget

MAIN_THEME_NAME = 'main.css'


class ThemeManager(QObject):
    """
    主题管理器类，用于管理应用程序的主题样式

    Args:
        app_root (str): 应用程序根目录路径

    Attributes:
        themeChanged (pyqtSignal[str]): 主题改变信号
        THEMES (Dict[str, str]): 主题名称与主题文件夹名称的映射
    """
    # 主题改变信号，参数为主题名称
    themeChanged = pyqtSignal(str)

    # 主题文件夹名称映射
    THEMES = {
        "默认": "default",
        "浅色": "light",
        "深色": "dark",
        "护眼": "eye"
    }

    def __init__(self, app_root: str):
        """ 初始化主题管理器 """
        super().__init__()
        self.app_root = app_root
        self.themes_dir = Path(app_root) / "resources" / "theme"
        self.current_theme = "默认"
        self.stylesheets_cache = {}  # 缓存已加载的样式表

    def get_theme_path(self, theme_name: str) -> Optional[Path]:
        """
        获取主题文件夹路径
        
        Args:
            theme_name (str): 主题显示名称
            
        Returns:
            Optional[Path]: 主题文件夹路径，如果主题不存在则返回None
        """
        theme_dir = self.THEMES.get(theme_name)
        if not theme_dir:
            return None

        theme_path = self.themes_dir / theme_dir
        return theme_path if theme_path.exists() else None

    def load_stylesheet(self, theme_name: str) -> str:
        """
        加载主题样式表
        
        Args:
            theme_name (str): 主题显示名称
            
        Returns:
            str: 加载的样式表内容
        """
        # 如果主题已缓存，则直接返回
        if theme_name in self.stylesheets_cache:
            return self.stylesheets_cache[theme_name]

        theme_path = self.get_theme_path(theme_name)
        if not theme_path:
            return ""

        # 加载主样式表
        main_css = theme_path / MAIN_THEME_NAME
        if not main_css.exists():
            return ""

        # 读取样式表内容
        with open(main_css, encoding='utf-8') as f:
            stylesheet = f.read()

        # 缓存样式表
        self.stylesheets_cache[theme_name] = stylesheet
        return stylesheet

    @pyqtSlot(str, QObject)
    def change_theme(self, theme_name: str, target: QObject | QWidget) -> bool:
        """
        切换主题
        
        Args:
            theme_name (str): 要切换到的主题名称
            target (QObject): 要应用样式的目标对象（通常是主窗口）
            
        Returns:
            bool: 主题是否切换成功
        """
        if theme_name not in self.THEMES:
            return False

        stylesheet = self.load_stylesheet(theme_name)
        if not stylesheet:
            return False

        # 应用样式表
        target.setStyleSheet(stylesheet)
        self.current_theme = theme_name

        # 发送主题改变信号
        self.themeChanged.emit(theme_name)
        return True

    def get_available_themes(self) -> Dict[str, str]:
        """
        获取可用的主题列表
        
        Returns:
            Dict[str, str]: 主题显示名称到主题文件夹名称的映射
        """
        available_themes = {}
        for name, folder in self.THEMES.items():
            theme_path = self.themes_dir / folder
            if theme_path.exists() and (theme_path / "main.css").exists():
                available_themes[name] = folder

        return available_themes

    def get_current_theme(self) -> str:
        """
        获取当前主题名称
        
        Returns:
            str: 当前主题的显示名称
        """
        return self.current_theme
