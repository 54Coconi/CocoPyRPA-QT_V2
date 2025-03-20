import json
from collections import OrderedDict

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QLineEdit, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QMessageBox


class CmdLibAndSearchBar(QWidget):
    """
    创建指令库树型界面和搜索栏
    """

    def __init__(self, search_bar: QLineEdit, tree_widget: QTreeWidget, json_path: str):
        """
        初始化指令库
        :param search_bar: 搜索栏控件
        :param tree_widget: 指令库树型控件
        :param json_path: 指令库 JSON 文件路径
        """
        super().__init__(parent=None)
        self.searchBar = search_bar
        self.treeWidget = tree_widget
        self.json_path = json_path
        self.cmd_library = {}

        # 连接搜索栏的变化信号
        self.searchBar.textChanged.connect(self.searchItems)

        # 加载 JSON 配置文件并初始化树形控件
        self.load_json_and_init_tree()

    def load_json_and_init_tree(self):
        """
        加载 JSON 文件并初始化树形控件
        """
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.cmd_library = json.load(f, object_pairs_hook=OrderedDict)
        except Exception as e:
            QMessageBox.critical(self.treeWidget, "加载错误", f"无法加载指令库文件：{e}")
            return

        self.initTreeWidget()

    def initTreeWidget(self):
        """
        初始化指令库树形控件
        """
        # 清除现有节点
        self.treeWidget.clear()

        # 添加根节点和子节点
        for category, commands in self.cmd_library.items():
            root_item = QTreeWidgetItem([category])
            # 禁止拖动根节点
            root_item.setFlags(root_item.flags() & ~Qt.ItemIsDragEnabled)
            self.treeWidget.addTopLevelItem(root_item)

            for command in commands:
                command_name = command["name"]  # 命令名称
                command_icon = command.get("icon", "")  # 命令图标
                command_data = command.get("data", {})  # 命令数据

                sub_item = QTreeWidgetItem([command_name])
                sub_item.setIcon(0, QIcon(command_icon))  # 设置图标
                sub_item.setData(0, Qt.UserRole, command_data)  # 存储数据到用户角色
                root_item.addChild(sub_item)

                # 判断当前节点是否为 <If 判断> 节点
                if command["name"] == "If 判断":
                    then_item = QTreeWidgetItem(sub_item, ["成立"])  # 创建 then 节点
                    then_item.setIcon(0, QIcon(":/icons/if-true"))  # 设置图标
                    # 设置then节点不可拖拽，但是可以接受拖入
                    then_item.setFlags(then_item.flags() & ~Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)

                    else_item = QTreeWidgetItem(sub_item, ["不成立"])  # 创建 else 节点
                    else_item.setIcon(0, QIcon(":/icons/if-false"))  # 设置图标
                    # 设置else节点不可拖拽，但是可以接受拖入
                    else_item.setFlags(else_item.flags() & ~Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                # 判断当前节点是否为 <Loop 循环> 节点
                elif command["name"] == "Loop 循环":
                    count = command_data.get("params", {}).get("count", {})  # 获取循环次数
                    loop_item = QTreeWidgetItem(sub_item, [f"重复 {count} 次"])
                    # loop_item.setIcon(0, QIcon(":/icons/loop"))
                    # 设置loop节点不可拖拽，但是可以接受拖入
                    loop_item.setFlags(loop_item.flags() & ~Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)

    def searchItems(self, text):
        """
        搜索树形控件中的所有项目
        :param text: 输入的搜索文本
        """
        iterator = QTreeWidgetItemIterator(self.treeWidget)
        while iterator.value():
            item = iterator.value()
            # 当搜索栏不为空时处理搜索逻辑，展开匹配的项目及其父项目
            if text:
                if text.lower() in item.text(0).lower():
                    item.setHidden(False)
                    # 展开所有父项目以显示搜索到的子项目
                    parent = item.parent()
                    while parent:
                        parent.setExpanded(True)  # 展开父项目
                        parent.setHidden(False)  # 确保父项目也可见
                        parent = parent.parent()
                else:
                    item.setHidden(True)
            else:
                # 当搜索栏为空时，重置所有项目为未隐藏状态，但不自动展开父项目
                item.setHidden(False)
            iterator += 1

    def get_selected_item_data(self):
        """
        获取选中节点的数据
        :return: 选中节点的 data 数据
        """
        selected_item = self.treeWidget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "提示", "请先选择一个指令节点")
            return None

        data = selected_item.data(0, Qt.UserRole)
        if data:
            return data
        else:
            QMessageBox.warning(self, "提示", "当前选择的节点没有附加数据")
            return None
