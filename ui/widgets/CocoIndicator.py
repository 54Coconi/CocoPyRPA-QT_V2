from PyQt5.QtWidgets import QApplication, QStyle, QProxyStyle
from PyQt5.QtGui import QIcon, QColor, QPen, QPainter
from PyQt5.QtCore import Qt, QPoint

import resources_rc

# 画笔宽度 和 拖拽指示器颜色
PEN_WIDTH = [0, 1, 2, 3, 4, 5, 6]
DRAG_INDICATOR_COLOR = [
    QColor('#FF0000'),  # 0, red 红色
    QColor('#00FF00'),  # 1, green 绿色
    QColor('#0000FF'),  # 2, blue 蓝色
    QColor('#FFFF00'),  # 3, yellow 黄色
    QColor('#FF00FF'),  # 4, purple 紫色
    QColor('#00FFFF'),  # 5, cyan 青色
    QColor('#FFFFFF'),  # 6, white 白色
    QColor('#000000'),  # 7, black 黑色
    QColor('#FF6600')  # 8, orange 橙色
]

# TODO: 从资源文件中加载分支展开/折叠图标
BRANCH_OPEN_ICON = QIcon(':/icons/down-indicator')  # 分支展开图标
BRANCH_CLOSED_ICON = QIcon(':/icons/right-indicator')  # 分支折叠图标

_DEBUG = False


# 定义一个自定义的树形控件分支指示器样式类，继承自QProxyStyle，用于修改默认的展开/折叠图标。
class CustomTreeIndicatorStyle(QProxyStyle):
    """
    自定义树形控件指示器样式类(重写了分支折叠/展开图标、拖拽指示器颜色方法)
    """

    def __init__(self, pen_width: int = None,
                 drag_indicator_color: QColor = None,
                 style=None):
        super().__init__(style or QApplication.style())
        self.pen_width = pen_width or PEN_WIDTH[5]  # 设置画笔宽度, 默认为5
        self.drag_indicator_color = drag_indicator_color or DRAG_INDICATOR_COLOR[8]  # 设置拖拽指示器颜色, 默认为橙色

    # 重写drawPrimitive方法，该方法负责绘制各种基本图形元素。
    def drawPrimitive(self, element, option, painter, widget=None):
        """
        重写drawPrimitive方法, 用于绘制分支指示器
        :param element: 要绘制的元素类型，如QStyle.PE_IndicatorBranch代表分支指示器。
        :param option: 一个QStyleOption对象，包含绘制该元素所需的所有状态和样式信息。
        :param painter: QPainter对象，用于实际执行绘图操作。
        :param widget: 当前绘制操作关联的QWidget对象，如果有的话。
        :return: None
        """

        # 判断当前需要绘制的元素是否为分支指示器
        if element == QStyle.PE_IndicatorBranch:
            # 检查选项状态，判断该节点是否有子节点（State_Children）及节点当前是否展开（State_Open）
            if option.state & QStyle.State_Children:
                # 如果节点已展开，使用自定义的向下箭头蓝色图标
                if option.state & QStyle.State_Open:
                    print('open')
                    icon = BRANCH_OPEN_ICON  # 使用自定义分支展开图标
                # 如果节点未展开，使用自定义的向右箭头蓝色图标
                else:
                    icon = BRANCH_CLOSED_ICON  # 使用自定义分支折叠图标

                # 在指定的矩形区域内居中绘制图标
                icon.paint(painter, option.rect, Qt.AlignCenter)
            # 如果满足条件，直接返回，不再执行后续默认绘制逻辑
            return
        # 对于非分支指示器的其他元素，调用父类方法进行默认绘制
        else:
            super().drawPrimitive(element, option, painter, widget)

        # 检查需要绘制的元素是否为视图项的拖放指示器
        if element == QStyle.PE_IndicatorItemViewItemDrop and not option.rect.isNull():
            # 获取绘制区域矩形
            rect = option.rect

            # TODO: 设置画笔颜色为特定的 RGB 值
            pen = QPen(self.drag_indicator_color)
            # TODO: 设置画笔宽度, 修改此值可以修改树形控件拖放指示器线条宽度
            pen.setWidth(self.pen_width)

            # 将设置好的画笔应用于painter
            painter.setPen(pen)
            # 启用抗锯齿渲染，使得线条和形状边缘更平滑
            painter.setRenderHint(QPainter.Antialiasing)

            # 根据指示器的高度调整绘制逻辑
            if option.rect.height() == 0:
                # 圆心相对视图边界偏移量
                rotundity_offset = 5
                # 圆宽度
                rotundity_width = 5
                # 圆高度
                rotundity_height = 5
                # 圆心位置(圆心点距离视图左边界的水平距离,圆心点距离视图顶部的垂直距离)
                rotundity_pos_left = QPoint(rotundity_offset, option.rect.top())
                rotundity_pos_right = QPoint(widget.width() - rotundity_offset, option.rect.top())
                # 横线起点位置(横线起点距离视图左边界的水平距离,横线起点距离视图顶部的垂直距离)
                line_start = QPoint(rotundity_offset + rotundity_width, rect.top())
                # 横线终点位置(横线终点距离视图左边界的水平距离,横线终点距离视图顶部的垂直距离)
                line_end = QPoint(widget.width() - rotundity_offset - rotundity_width, rect.top())

                print(f'左侧圆形圆心坐标：{rotundity_pos_left} ' if _DEBUG else '', end='')
                print(f'右侧圆形圆心坐标：{rotundity_pos_right}\n' if _DEBUG else '', end='')
                # 绘制左侧圆形
                painter.drawEllipse(rotundity_pos_left, rotundity_width, rotundity_height)
                # 绘制横线
                painter.drawLine(line_start, line_end)
                # 绘制右侧圆形
                painter.drawEllipse(rotundity_pos_right, rotundity_width, rotundity_height)
            else:
                # 如果有高度，绘制一个矩形来指示拖放区域
                rect.setLeft(2)  # 调整矩形左边界
                rect.setRight(widget.width() - 2)  # 调整矩形右边界
                painter.drawRect(rect)  # 绘制矩形
        # 如果当前元素不是我们关注的拖放指示器，则调用父类方法进行默认处理
        else:
            super().drawPrimitive(element, option, painter, widget)


# 自定义的拖拽指示器样式类，继承自QProxyStyle，目的是为了自定义在视图项上拖放时的指示效果。
class CustomDragDropIndicatorStyle(QProxyStyle):
    """
    自定义拖拽指示器
    """

    # 初始化方法，允许传入一个可选的样式对象作为基样式，若未提供则使用当前应用程序的默认样式。
    def __init__(self, style=None):
        # 调用父类的初始化方法，并传入处理过的样式参数
        super().__init__(style or QApplication.style())

    # 重写drawPrimitive方法，该方法负责绘制各种基本图形元素，这里主要用于自定义拖放指示图标。
    def drawPrimitive(self, element, option, painter, widget=None):
        """
        重写drawPrimitive方法, 用于绘制拖拽指示器
        :param element: 要绘制的元素类型，如 QStyle.PE_IndicatorItemViewItemDrop 代表拖拽指示器。
        :param option: 一个QStyleOption对象，包含绘制该元素所需的所有状态和样式信息。
        :param painter: QPainter对象，用于实际执行绘图操作。
        :param widget: 当前绘制操作关联的QWidget对象，如果有的话。
        :return: None
        """

        # 检查需要绘制的元素是否为视图项的拖放指示器
        if element == QStyle.PE_IndicatorItemViewItemDrop and not option.rect.isNull():
            # 获取绘制区域矩形
            rect = option.rect
            # 设置画笔颜色为特定的RGB值，模拟一种视觉效果
            pen = QPen(DRAG_INDICATOR_COLOR[1])
            # TODO: 设置画笔宽度, 修改此值可以修改拖拽指示器的宽度
            pen.setWidth(4)
            # 将设置好的画笔应用于painter
            painter.setPen(pen)
            # 启用抗锯齿渲染，使得线条和形状边缘更平滑
            painter.setRenderHint(QPainter.Antialiasing)

            # 根据指示器的高度调整绘制逻辑
            if option.rect.height() == 0:
                # 圆心相对视图边界偏移量
                rotundity_offset = 5
                # 圆宽度
                rotundity_width = 5
                # 圆高度
                rotundity_height = 5
                # 左侧圆心位置(圆心点距离视图左边界的水平距离,圆心点距离视图顶部的垂直距离)
                rotundity_pos_left = QPoint(rotundity_offset, option.rect.top())
                # 右侧圆心位置(圆心点距离视图右边界的水平距离,圆心点距离视图顶部的垂直距离)
                rotundity_pos_right = QPoint(widget.width() - rotundity_offset, option.rect.top())
                # 横线起点位置(横线起点距离视图左边界的水平距离,横线起点距离视图顶部的垂直距离)
                line_start = QPoint(rotundity_offset + rotundity_width, rect.top())
                # 横线终点位置(横线终点距离视图左边界的水平距离,横线终点距离视图顶部的垂直距离)
                line_end = QPoint(widget.width() - rotundity_offset - rotundity_width, rect.top())

                print(f'左侧圆形圆心坐标：{rotundity_pos_left} ' if _DEBUG else '', end='')
                print(f'右侧圆形圆心坐标：{rotundity_pos_right}\n' if _DEBUG else '', end='')
                # 绘制左侧圆形
                painter.drawEllipse(rotundity_pos_left, rotundity_width, rotundity_height)
                # 绘制横线
                painter.drawLine(line_start, line_end)
                # 绘制右侧圆形
                painter.drawEllipse(rotundity_pos_right, rotundity_width, rotundity_height)
            else:
                # 如果有高度，绘制一个矩形来指示拖放区域
                rect.setLeft(2)  # 调整矩形左边界
                rect.setRight(widget.width() - 2)  # 调整矩形右边界
                painter.drawRect(rect)  # 绘制矩形

        # 如果当前元素不是我们关注的拖放指示器，则调用父类方法进行默认处理
        else:
            super().drawPrimitive(element, option, painter, widget)
