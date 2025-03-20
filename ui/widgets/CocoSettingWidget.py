import os
import configparser
import json

from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QComboBox, QLineEdit, QCheckBox, QDoubleSpinBox, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt, QEvent, QObject, pyqtSignal
from PyQt5.QtWidgets import QPushButton


class ConfigManager(QObject):
    """ 全局配置管理器 """
    config_changed = pyqtSignal(dict)  # 配置更改信号,传递更改后的配置

    # 默认配置
    DEFAULT_CONFIG = {
        "General": {
            "Theme": "默认",
            "Language": "zh",
            "RunMode": "debug",
            "EditMode": "normal",
            "Window": {
                "StaysOnTopHint": True,
                "CloseMode": "system_tray",
            },
        },
        "ImageMatch": {
            "Threshold": 0.8,
        },
        "ImageOcr": {
            "Threshold": 0.8,
            "ModelName": "PaddleOCR",
        },
    }

    def __init__(self, config_file="config.ini"):
        super().__init__()
        self.config_file = config_file  # 配置文件路径
        self.config = {}  # 当前配置
        self.parser = self._get_parser()

        if os.path.exists(self.config_file):
            self.load_config()
        else:
            self.reset_to_default()

    @staticmethod
    def _get_parser():
        """获取配置文件解析器，保持键名大小写不变"""
        class CaseSensitiveConfigParser(configparser.ConfigParser):
            """保持键名大小写"""
            def optionxform(self, optionstr: str) -> str:
                """保持键名大小写"""
                return optionstr

        return CaseSensitiveConfigParser()

    def _flatten_config(self, data, parent_key=""):
        """将嵌套的配置展平为 'Section.Key' 格式"""
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(self._flatten_config(value, new_key).items())
            else:
                items.append((new_key, value))
        return dict(items)

    @staticmethod
    def _expand_config(flat_data):
        """将展平的配置还原为嵌套结构"""
        result = {}
        for key, value in flat_data.items():
            keys = key.split(".")
            d = result
            for part in keys[:-1]:
                d = d.setdefault(part, {})
            d[keys[-1]] = value
        return result

    def load_config(self):
        """加载配置文件"""
        self.parser.read(self.config_file, encoding="utf-8")
        flat_config = {}  # 展平的配置

        for section in self.parser.sections():
            for key, value in self.parser.items(section):
                try:
                    # 尝试解析为 JSON，否则直接使用原始值
                    flat_config[f"{section}.{key}"] = json.loads(value) if value else value
                except json.JSONDecodeError:
                    flat_config[f"{section}.{key}"] = value  # 直接存储原始值

        self.config = self._expand_config(flat_config)

    def save_config(self):
        """保存配置到文件"""
        flat_config = self._flatten_config(self.config)  # 展平配置

        for key, value in flat_config.items():
            section, _, sub_key = key.partition(".")
            if section not in self.parser:
                self.parser[section] = {}
            # 将值转换为 JSON 字符串或直接保存
            if isinstance(value, (dict, list, bool, int, float)):
                self.parser[section][sub_key] = json.dumps(value)
            else:
                self.parser[section][sub_key] = str(value)

        with open(self.config_file, "w", encoding="utf-8") as f:
            self.parser.write(f)
        # 发送配置更改信号
        self.config_changed.emit(self.config)

    def reset_to_default(self):
        """恢复默认配置"""
        self.config = self.DEFAULT_CONFIG
        self.save_config()


class SettingsWindow(QDialog):
    """
    自定义设置窗口，使用 QTreeWidget 组织配置项
    """

    def __init__(self, _config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = _config_manager
        self.parent = parent
        self.setWindowTitle("设置")
        self.resize(600, 600)
        self.settings_widgets = {}  # 动态存储设置控件

        # 创建 QTreeWidget
        self.tree = QTreeWidget(self.parent)
        self.tree.setHeaderLabels(["配置名称", "值"])  # 设置表头
        # 设置表头文字居中
        self.tree.header().setStyleSheet("QHeaderView::section { text-align: center; }")
        # 设置列宽自适应
        self.tree.header().setStretchLastSection(True)
        # self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        # 设置列宽
        self.tree.setColumnWidth(0, 340)  # 设置第一列的宽度
        self.tree.setColumnWidth(1, 200)  # 设置第二列的宽度

        # 动态生成设置项
        self._generate_settings(self.config_manager.config)

        # 底部按钮
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        reset_button = QPushButton("恢复默认设置")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(save_button)
        button_layout.addWidget(reset_button)
        button_layout.addWidget(cancel_button)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tree)
        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)

        # 信号绑定
        save_button.clicked.connect(self.save_settings)
        reset_button.clicked.connect(self.reset_settings)
        cancel_button.clicked.connect(self.close)

    def eventFilter(self, obj, event):
        """ 事件过滤器，用于处理 QComboBox 的点击展开问题 """
        if isinstance(obj, QComboBox) and event.type() == QEvent.MouseButtonPress:
            if obj.view().isVisible():
                obj.hidePopup()  # 如果已经展开，则关闭下拉框
            else:
                obj.showPopup()  # 如果未展开，则展开下拉框
            return True  # 标记事件已处理
        return super().eventFilter(obj, event)

    def _generate_settings(self, config):
        """递归生成 QTreeWidget 配置项"""
        for category, settings in config.items():
            category_item = QTreeWidgetItem(self.tree)
            category_item.setText(0, self._translate_key(category))
            self._add_settings_to_tree(category_item, settings, category)

    def _add_settings_to_tree(self, parent_item, settings, category):
        """为某个类别添加具体的配置项"""
        for key, value in settings.items():
            full_key = f"{category}.{key}"
            if isinstance(value, dict):
                # 如果是子字典，递归处理
                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, self._translate_key(key))  # 设置映射后的文本
                self._add_settings_to_tree(child_item, value, full_key)
            else:
                # 添加配置项到树
                setting_item = QTreeWidgetItem(parent_item)
                setting_item.setText(0, self._translate_key(key))
                widget = self._create_widget(full_key, key, value)
                self.tree.setItemWidget(setting_item, 1, widget)
                self.settings_widgets[full_key] = widget

    def _create_widget(self, full_key, key, value):
        """ 根据键名和值类型创建适当的控件 """
        print(f"(_create_widget) 当前的键名是：{key},值是：{value}")
        if key == "Theme":
            # 主题采用下拉框
            widget = QComboBox()
            widget.addItems(["默认", "深色", "浅色", "护眼"])
            widget.setCurrentText(value)
            self._configure_combobox(widget)

        elif key == "Language":
            # 语言采用下拉框
            widget = QComboBox()
            widget.addItems(["中文", "English"])
            widget.setCurrentText("中文" if value == "zh" else "English")
            self._configure_combobox(widget)

        elif key == "RunMode":
            # 运行模式采用复选框（是否启用调试模式）
            widget = QCheckBox()
            widget.setText("启用调试模式")
            widget.setChecked(value == "debug")

        elif key == "EditMode":
            # 编辑模式采用下拉框
            widget = QComboBox()
            widget.addItems(["高级编辑", "普通编辑"])
            widget.setCurrentText("高级编辑" if value == "advanced" else "普通编辑")
            self._configure_combobox(widget)

        elif key == "CloseMode":
            # 关闭模式采用下拉框
            widget = QComboBox()
            widget.addItems(["放到系统托盘", "退出"])
            widget.setCurrentText("放到系统托盘" if value == "system_tray" else "退出")

        elif key == "ModelName":
            # OCR 模型名称采用下拉框
            widget = QComboBox()
            widget.addItems(["PaddleOCR"])
            widget.setCurrentText(value)
            self._configure_combobox(widget)

        elif isinstance(value, bool) and key == "StaysOnTopHint":
            widget = QCheckBox()
            widget.setText("始终在顶部")
            widget.setChecked(value)
            # 连接信号
            widget.stateChanged.connect(self.set_stays_on_top)
        elif isinstance(value, (int, float)):
            widget = QDoubleSpinBox()
            widget.setMinimum(0.00)  # 设置最小值
            widget.setMaximum(1.00)  # 设置最大值
            widget.setSingleStep(0.02)  # 设置步长
            widget.setValue(value)

        else:
            widget = QLineEdit()
            widget.setText(str(value))

        return widget

    def _configure_combobox(self, combobox):
        """配置 QComboBox 使其在 QTreeWidget 中正常展开"""
        combobox.setFocusPolicy(Qt.StrongFocus)  # 设置为强焦点模式
        combobox.setEditable(False)  # 禁用编辑状态，确保下拉框只可选择
        combobox.installEventFilter(self)  # 安装事件过滤器

    @staticmethod
    def _translate_key(key):
        """翻译键名为 中文(英文) 格式"""
        translations = {
            "General": "常规(General)",
            "Theme": "主题(Theme)",
            "Language": "语言(Language)",
            "RunMode": "运行模式(RunMode)",
            "EditMode": "编辑模式(EditMode)",
            "Window": "窗口(Window)",
            "StaysOnTopHint": "置顶窗口(StaysOnTopHint)",
            "CloseMode": "关闭模式(CloseMode)",
            "ImageMatch": "图像匹配(ImageMatch)",
            "Threshold": "阈值(Threshold)",
            "ImageOcr": "OCR配置(ImageOcr)",
            "ModelName": "模型名称(ModelName)"
        }
        return translations.get(key, f"{key} ({key})")

    def set_stays_on_top(self, state):
        """设置始终在顶部"""
        if state == Qt.Checked:
            self.parent.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.parent.setWindowFlags(self.parent.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)

    def save_settings(self):
        """保存设置"""
        config = self.config_manager.config
        for key, widget in self.settings_widgets.items():
            keys = key.split(".")
            d = config
            for part in keys[:-1]:
                d = d.setdefault(part, {})

            # 根据控件类型进行不同的处理
            # 处理复选框
            if isinstance(widget, QCheckBox):
                if keys[-1] == "RunMode":
                    # 保存运行模式为 "debug" 或 "normal"
                    d[keys[-1]] = "debug" if widget.isChecked() else "normal"
                else:
                    d[keys[-1]] = widget.isChecked()
            # 处理小数输入框
            elif isinstance(widget, QDoubleSpinBox):
                # 保存为两位浮点数
                d[keys[-1]] = float(f"{widget.value():.2f}")
                # d[keys[-1]] = widget.value()
            # 处理下拉框
            elif isinstance(widget, QComboBox):
                if keys[-1] == "Theme":
                    # 保存主题为 "默认" 或 "深色" 或 "浅色" 或 "护眼"
                    d[keys[-1]] = widget.currentText()
                elif keys[-1] == "Language":
                    # 保存语言为 "zh" 或 "en"
                    d[keys[-1]] = "zh" if widget.currentText() == "中文" else "en"

                elif keys[-1] == "EditMode":
                    # 保存编辑模式为 "advanced" 或 "normal"
                    d[keys[-1]] = "advanced" if widget.currentText() == "高级编辑" else "normal"

                elif keys[-1] == "CloseMode":
                    # 保存关闭模式为 "system_tray" 或 "quit"
                    d[keys[-1]] = "system_tray" if widget.currentText() == "放到系统托盘" else "quit"

                elif keys[-1] == "ModelName":
                    d[keys[-1]] = widget.currentText()

                else:
                    d[keys[-1]] = widget.currentText()
            # 处理文本输入框
            elif isinstance(widget, QLineEdit):
                d[keys[-1]] = widget.text()

        self.config_manager.save_config()
        QMessageBox.information(self, "成功", "设置已保存！")
        self.close()

    def reset_settings(self):
        """恢复默认设置"""
        self.config_manager.reset_to_default()
        self.tree.clear()
        self._generate_settings(self.config_manager.config)
        QMessageBox.information(self, "提示", "设置已恢复为默认值！")


# 全局单例
config_manager = ConfigManager()
