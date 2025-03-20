"""
@author: 54Coconi
@data: 2024-12-6
@version: 1.0.0
@path: ui/widgets/IfCmdConditionBuilder.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    - 用于构建 if 判断指令的条件表达式
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox
)


class ConditionBuilder(QDialog):
    """条件构建器"""

    def __init__(self, all_commands_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("条件构建器")
        self.setFixedSize(450, 400)
        self.all_commands_data = all_commands_data  # 指令列表数据
        self.condition = ""  # 最终生成的条件表达式

        # 布局和控件
        layout = QVBoxLayout()
        self.command_selector = QComboBox()
        self.field_selector = QComboBox()
        self.operator_selector = QComboBox()
        self.value_editor = QLineEdit()  # 用户输入值
        self.value_combo = QComboBox()  # 用户选择值（布尔值或枚举值）

        # 初始化控件
        self.command_selector.addItem("指令")
        for cmd in all_commands_data:
            cmd_id = cmd["params"].get("id", "unknown_id")
            cmd_name = cmd["params"].get("name", "未知指令")
            self.command_selector.addItem(f"{cmd_name} (ID: {cmd_id})")

        self.command_selector.currentIndexChanged.connect(self.update_fields)
        self.field_selector.currentIndexChanged.connect(self.update_operators_and_values)

        # 初始状态：隐藏 `value_combo`
        self.value_combo.hide()

        # 添加控件到布局
        layout.addWidget(QLabel("选择指令"))
        layout.addWidget(self.command_selector)
        layout.addWidget(QLabel("选择属性"))
        layout.addWidget(self.field_selector)
        layout.addWidget(QLabel("选择判断符"))
        layout.addWidget(self.operator_selector)
        layout.addWidget(QLabel("输入或选择结果值"))
        layout.addWidget(self.value_editor)
        layout.addWidget(self.value_combo)

        # 添加按钮
        btn_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        self.ok_button.clicked.connect(self.confirm_condition)
        self.cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_button)
        btn_layout.addWidget(self.cancel_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def update_fields(self):
        """更新字段列表"""
        self.field_selector.clear()
        cmd_index = self.command_selector.currentIndex() - 1  # 获取选中的指令索引
        if cmd_index < 0:
            return

        command = self.all_commands_data[cmd_index]
        fields = command.get("params", {})  # 获取指令的字段

        self.field_selector.addItem("选择属性")
        for field, value in fields.items():
            self.field_selector.addItem(field)

    def update_operators_and_values(self):
        """更新判断符和结果值输入方式"""
        self.operator_selector.clear()
        selected_field = self.field_selector.currentText()
        cmd_index = self.command_selector.currentIndex() - 1

        if selected_field == "选择属性" or cmd_index < 0:
            self.value_editor.hide()
            self.value_combo.hide()
            return

        command = self.all_commands_data[cmd_index]
        field_value = command["params"].get(selected_field)

        # 设置判断符
        operators = ["==", "!=", ">", ">=", "<", "<="]
        self.operator_selector.addItems(operators)

        # 根据字段类型设置输入控件
        if selected_field == "status":
            self.value_combo.clear()
            self.value_combo.addItems(["0", "1", "2", "3"])  # 状态固定值
            self.value_editor.hide()
            self.value_combo.show()
        elif isinstance(field_value, bool):
            self.value_combo.clear()
            self.value_combo.addItems(["True", "False"])  # 布尔值
            self.value_editor.hide()
            self.value_combo.show()
        else:
            self.value_combo.hide()  # 非布尔值或状态时隐藏下拉框
            self.value_editor.clear()
            self.value_editor.show()

    def confirm_condition(self):
        """生成条件表达式并返回"""
        cmd_index = self.command_selector.currentIndex() - 1
        selected_field = self.field_selector.currentText()
        selected_operator = self.operator_selector.currentText()

        if cmd_index < 0 or selected_field == "选择属性" or not selected_operator:
            QMessageBox.warning(self, "错误", "请完整选择条件的各项内容")
            return

        # 获取值
        if self.value_combo.isVisible():
            selected_value = self.value_combo.currentText()
        else:
            selected_value = self.value_editor.text()

        if not selected_value:
            QMessageBox.warning(self, "错误", "请输入或选择一个值")
            return

        # 获取指令 ID
        cmd_id = self.all_commands_data[cmd_index]["params"].get("id", "unknown_id")

        # 构建条件表达式
        self.condition = f"results_list['{cmd_id}']['{selected_field}'] {selected_operator} {selected_value}"
        self.accept()


# 测试
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from collections import OrderedDict

    all_commands_data = [
        {'action': 'click', 'icon': ':/icons/mouse-click-left', 'params': OrderedDict(
            [('name', '鼠标左键点击'), ('target_pos', [0, 0]), ('clicks', 1), ('interval', 0.2),
             ('duration', 2.0), ('retries', 0), ('button', 'left'), ('is_active', True),
             ('use_pynput', False),('id','11111111')]), 'type': 'mouse'},

        {'action': 'moveTo', 'icon': ':/icons/mouse-move', 'params': OrderedDict(
            [('name', '鼠标定点移动(400,0)'), ('target_pos', [400, 0]), ('duration', 2.0),
             ('retries', 0), ('is_active', True), ('use_pynput', True),
             ('condition', 'results_list[1]["status"] == 3'),('id','22222222')]), 'type': 'mouse'},

        {'action': 'if', 'icon': ':/icons/if', 'params': OrderedDict(
            [('name', 'If 判断'), ('condition', 'results_list[0]["status"] == 3'),
             ('then_commands', [OrderedDict(
                 [('type', 'flow'), ('action', 'delay'), ('icon', ':/icons/delay'), ('params', OrderedDict(
                     [('name', '等待 3.00 秒'), ('delay_time', 3.0), ('is_active', True)]))]),
                 OrderedDict([('type', 'mouse'), ('action', 'moveRel'), ('icon', ':/icons/mouse-rel-move'),
                              ('params', OrderedDict([(
                                  'name', '鼠标相对移动(0,200)'), ('offset', [0, 200]), ('duration', 4.0),
                                  ('retries', 0), ('is_active', True), ('use_pynput', True)]))])]),
             ('else_commands', [OrderedDict([('type', 'flow'), ('action', 'delay'), ('icon', ':/icons/delay'),
                                             ('params', OrderedDict([('name', '等待 3.00 秒'), ('delay_time', 3.0),
                                                                     ('is_active', True)]))]),
                                OrderedDict(
                                    [('type', 'mouse'), ('action', 'moveRel'), ('icon', ':/icons/mouse-rel-move'),
                                     ('params',
                                      OrderedDict(
                                          [('name', '鼠标相对移动(1000,0)'), ('offset', [1000, 0]), ('duration', 4.0),
                                           ('retries', 0),
                                           ('is_active', True), ('use_pynput', True)]))])]),
             ('is_active', True),('id','33333333')]), 'type': 'flow'},

        {'action': 'delay', 'icon': ':/icons/delay',
         'params': OrderedDict([('name', '等待 3.00 秒'), ('delay_time', 3.0), ('is_active', True),('id','44444444')]),
         'type': 'flow'},

        {'action': 'moveRel', 'icon': ':/icons/mouse-rel-move', 'params': OrderedDict(
            [('name', '鼠标相对移动(0,200)'), ('offset', [0, 200]), ('duration', 4.0), ('retries', 0),
             ('is_active', True), ('use_pynput', True),('id','55555555')]), 'type': 'mouse'}

    ]

    app = QApplication(sys.argv)
    window = ConditionBuilder(all_commands_data)
    if window.exec_():
        print("条件表达式为: ",window.condition)
    sys.exit(app.exec_())
