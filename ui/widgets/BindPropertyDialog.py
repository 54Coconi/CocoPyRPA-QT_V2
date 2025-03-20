# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QComboBox, QLabel, QPushButton, QMessageBox
from pydantic import BaseModel


class PropertyBindingManager:
    """管理指令属性绑定的全局单例"""
    _bindings = {}
    all_tasks_cmd = []

    @classmethod
    def bind_property(cls, source_cmd, source_attr, target_cmd, target_attr):
        """绑定属性"""
        source_key = id(source_cmd)  # 使用源指令对象的 id 作为键
        target_key = id(target_cmd)  # 使用目标指令对象的 id 作为键
        cls._bindings[(target_key, target_attr)] = (source_key, source_attr)

    @classmethod
    def get_bound_value(cls, cmd, attr):
        """获取绑定属性的值"""
        key = id(cmd)  # 使用指令对象的 id
        binding = cls._bindings.get((key, attr))
        if binding:
            source_key, source_attr = binding
            # 遍历找到与 source_key 匹配的指令对象
            source_cmd = next((cmd for cmd in cls.all_tasks_cmd if id(cmd) == source_key), None)
            if source_cmd:
                return getattr(source_cmd, source_attr, None)
        return None


class BindPropertyDialog(QDialog):
    """属性绑定对话框"""

    def __init__(self, all_tasks_cmd, parent=None):
        super().__init__(parent)
        self.setWindowTitle("绑定属性")
        self.setFixedSize(400, 300)
        self.all_tasks_cmd = all_tasks_cmd

        layout = QVBoxLayout()
        self.source_cmd_combo = QComboBox()
        self.source_attr_combo = QComboBox()
        self.target_cmd_combo = QComboBox()
        self.target_attr_combo = QComboBox()

        self.source_cmd_combo.addItem("选择源指令")
        self.target_cmd_combo.addItem("选择目标指令")
        for cmd in all_tasks_cmd:
            print(f"(BindPropertyDialog) 当前指令：{cmd.name}")
            self.source_cmd_combo.addItem(cmd.name)
            self.target_cmd_combo.addItem(cmd.name)

        self.source_cmd_combo.currentIndexChanged.connect(self.update_source_attrs)
        self.target_cmd_combo.currentIndexChanged.connect(self.update_target_attrs)

        layout.addWidget(QLabel("源指令"))
        layout.addWidget(self.source_cmd_combo)
        layout.addWidget(QLabel("源属性"))
        layout.addWidget(self.source_attr_combo)
        layout.addWidget(QLabel("目标指令"))
        layout.addWidget(self.target_cmd_combo)
        layout.addWidget(QLabel("目标属性"))
        layout.addWidget(self.target_attr_combo)

        self.bind_button = QPushButton("绑定")
        self.bind_button.clicked.connect(self.bind_properties)
        layout.addWidget(self.bind_button)

        self.setLayout(layout)

    def filter_command_attributes(self, command):
        """
        过滤指令的自定义属性，排除继承自 BaseModel 的字段。
        """
        base_model_fields = set(BaseModel.model_fields.keys())  # 获取 BaseModel 的字段
        custom_fields = set(command.model_fields.keys())  # 获取指令的字段
        return custom_fields - base_model_fields  # 返回差集，即自定义字段

    def update_source_attrs(self):
        """更新源属性列表"""
        self.source_attr_combo.clear()
        cmd_index = self.source_cmd_combo.currentIndex() - 1
        if cmd_index >= 0:
            command = self.all_tasks_cmd[cmd_index]
            custom_attrs = self.filter_command_attributes(command)
            self.source_attr_combo.addItems(sorted(custom_attrs))

    def update_target_attrs(self):
        """更新目标属性列表"""
        self.target_attr_combo.clear()
        cmd_index = self.target_cmd_combo.currentIndex() - 1
        if cmd_index >= 0:
            command = self.all_tasks_cmd[cmd_index]
            custom_attrs = self.filter_command_attributes(command)
            self.target_attr_combo.addItems(sorted(custom_attrs))

    def bind_properties(self):
        """绑定属性"""
        source_cmd_index = self.source_cmd_combo.currentIndex() - 1
        target_cmd_index = self.target_cmd_combo.currentIndex() - 1
        if source_cmd_index >= 0 and target_cmd_index >= 0:
            source_cmd = self.all_tasks_cmd[source_cmd_index]
            target_cmd = self.all_tasks_cmd[target_cmd_index]
            source_attr = self.source_attr_combo.currentText()
            target_attr = self.target_attr_combo.currentText()

            PropertyBindingManager.all_tasks_cmd = self.all_tasks_cmd
            PropertyBindingManager.bind_property(source_cmd, source_attr, target_cmd, target_attr)
            QMessageBox.information(self, "绑定成功",
                                    f"{source_cmd.name}.{source_attr} -> {target_cmd.name}.{target_attr}")
