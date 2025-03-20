from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget
from .position_xy_ui import Ui_Form


class PositionXY(QWidget, Ui_Form):
    """ 自定义坐标控件 """

    # 定义自定义信号，发送坐标值
    valueChanged = QtCore.pyqtSignal(int, int)  # 信号携带 x 和 y 的整数值

    def __init__(self, x, y):
        super().__init__()
        self.setupUi(self)

        # 设置初始值
        self.pos_x_spinBox.setValue(x)
        self.pos_y_spinBox.setValue(y)

        # 绑定 SpinBox 的值改变信号到本地处理函数
        self.pos_x_spinBox.valueChanged.connect(self._emit_value_changed)
        self.pos_y_spinBox.valueChanged.connect(self._emit_value_changed)

    def _emit_value_changed(self):
        """内部方法，当值改变时触发 valueChanged 信号"""
        x, y = self.get_pos()
        self.valueChanged.emit(x, y)

    def get_pos(self) -> tuple:
        """获取当前坐标值"""
        return self.pos_x_spinBox.value(), self.pos_y_spinBox.value()

    def set_pos(self, x, y):
        """设置坐标值"""
        self.pos_x_spinBox.setValue(x)
        self.pos_y_spinBox.setValue(y)

    def clear(self):
        """清空坐标值"""
        self.pos_x_spinBox.setValue(0)
        self.pos_y_spinBox.setValue(0)
