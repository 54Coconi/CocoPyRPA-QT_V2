"""
@author: 54Coconi
@date: 2024-11-25
@version: 1.0.0
@path: core/commands/image_commands.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    图像相关操作指令模块

    包括:
        - 图片匹配指令
        - 图片点击指令
        - 文字识别指令
        - 文字点击指令
"""
import os
import time
from typing import Tuple, Optional

import pyautogui
from pydantic import Field
from pynput.mouse import Controller

from config.app_config import debug
from ui.widgets.CocoSettingWidget import config_manager
from utils.debug import print_func_time
from utils.image_process.ocr_tools import OCRTool, find_matching_texts
from utils.image_process.screenshot_tool import EasyScreenshot
from .base_command import RetryCmd, CommandRunningException
from .mouse_commands import move_with_duration_pynput, click_pynput, TweenFuncs

_DEBUG = False

DET_MODEL_DIR = '../../models/det/ch/ch_PP-OCRv4_det_infer'
REC_MODEL_DIR = '../../models/rec/ch/ch_PP-OCRv4_rec_infer'
CLS_MODEL_DIR = '../../models/cls/ch/ch_PP-OCRv4_cls_infer'


def get_threshold():
    """
    获取图片匹配度阈值
    :return: threshold - (float): 图片匹配度阈值
    """
    threshold = config_manager.config.get('ImageMatch', {}).get('Threshold', 0.8)
    return threshold


def save_matching_result():
    """
    保存匹配结果图片
    :return: save_path - (str): 保存路径
    """
    save_path = config_manager.config.get('ImageMatch', {}).get('SavePath', None)
    return save_path


def get_ocr_threshold():
    """
    获取 OCR 文字识别阈值
    :return: threshold - (float): OCR 文字识别阈值
    """
    threshold = config_manager.config.get('ImageOcr', {}).get('Threshold', 0.8)
    return threshold


def get_closest_point(_x, _y, centers: list) -> Optional[Tuple[int, int]]:
    """
    获取最近的点
    :param _x: x 坐标
    :param _y: y 坐标
    :param centers: 要计算的点的列表
    :return: closest_point - (Tuple[int, int]): 最近的点的坐标
    """
    closest_point = None
    min_distance = float('inf')
    for point in centers:
        distance = ((point[0] - _x) ** 2 + (point[1] - _y) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            closest_point = point
    return closest_point


def _click_with_pynput(target_pos: Tuple[int, int], button, duration, interval, clicks):
    mouse = Controller()
    current_position = mouse.position  # 获取当前鼠标位置
    if current_position != target_pos and duration > 0:
        move_with_duration_pynput(duration, target_pos, mouse)  # 移动到目标位置
    click_pynput(clicks, button, interval, mouse, target_pos)  # 点击


def _click_with_pyautogui(target_pos: Tuple[int, int], button, duration, interval, clicks):
    if pyautogui.position() == target_pos and duration > 0:
        duration = 0  # 如果目标位置与当前位置相同，则不需要移动
    pyautogui.click(
        x=target_pos[0],
        y=target_pos[1],
        clicks=clicks,
        interval=interval,
        button=button,
        duration=duration,
        tween=TweenFuncs[0]
    )


class ImageMatchCmd(RetryCmd):
    """
    <图片全屏匹配> 指令

    用于匹配模板图片在屏幕（支持多屏幕）中的位置（定位在图片中心）
    如果有多个匹配结果，默认取最相似的
    Attributes:
        name:(str): 指令名称
        retries:(int): 指令重复执行次数
        error_retries:(int): 指令执行出错时的重试次数
        is_active:(bool): 指令是否启用
        error_retries_time:(float | int): 指令执行出错时的重试间隔时间
        template_img:(str): 模板图片路径
        threshold:(float): 匹配度阈值
    """

    name: str = Field("图片匹配", description="图片匹配指令名称")
    retries: int = Field(0, description="指令重复执行次数")
    error_retries: int = Field(0, description="指令执行出错时的重试次数")
    is_active: bool = Field(True, description="指令是否启用")
    error_retries_time: float | int = Field(0, description="指令执行出错时的重试间隔时间")

    template_img: str = Field(None, description="模板图片路径")
    threshold: float = Field(default_factory=get_threshold, description="匹配度阈值")
    save_path: str = Field(default_factory=save_matching_result, description="是否保存匹配结果图片")
    _template_img_center: Tuple[int, int] = None  # 存储模板图片的中心坐标

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        tool = EasyScreenshot()
        try:
            if not os.path.exists(self.template_img):
                raise FileNotFoundError(f"模板图片 '{self.template_img}' 不存在")
            matches = tool.find_template(self.template_img, self.threshold, save_path=self.save_path)
            if not matches:
                _error = f"全屏模板匹配结果为空"
                raise CommandRunningException(_error)
            center_x, center_y, score = matches[0]  # 取最佳匹配的一个结果
            self._template_img_center = (int(center_x), int(center_y))
            return  # self._template_img_center
        except KeyboardInterrupt:
            raise
        except Exception as e:
            raise CommandRunningException(e)
        finally:
            tool.close()

    @property
    def template_img_center(self):
        """获取模板图片的中心坐标"""
        return self._template_img_center

    @template_img_center.setter
    def template_img_center(self, value):
        self._template_img_center = value


class ImageClickCmd(ImageMatchCmd):
    """
    <图片全屏点击> 指令

    用于匹配模板图片在屏幕（支持多屏幕）中的位置（定位在图片中心），然后点击该位置
    如果有多个匹配结果，默认点击最相似的
    Attributes:
        name:(str): 指令名称
        retries:(int): 指令重复执行次数
        error_retries:(int): 指令执行出错时的重试次数
        is_active:(bool): 指令是否启用
        error_retries_time:(float|int): 指令执行出错时的重试间隔时间
        template_img:(str): 模板图片路径
        threshold:(float): 匹配度阈值
        clicks:(int): 点击次数
        interval:(float|int): 点击间隔
        duration:(float|int): 移动持续时间
        button:(str): 点击的鼠标按键类型 ('left', 'right', 'middle')
        use_pynput:(bool): 是否使用 pynput 库点击
    """

    name: str = Field("图片点击", description="指令名称")
    retries: int = Field(0, description="指令重复执行次数")
    error_retries: int = Field(0, description="指令执行出错时的重试次数")
    error_retries_time: float | int = Field(0, description="指令执行出错时的重试间隔时间")
    is_active: bool = Field(True, description="指令是否启用")
    template_img: str = Field(None, description="模板图片路径")
    threshold: float = Field(default_factory=get_threshold, description="匹配度阈值")

    clicks: int = Field(1, description="点击次数")
    interval: float | int = Field(0.2, description="点击间隔")
    button: str = Field("left", description="点击的鼠标按键类型 ('left', 'right', 'middle')")
    duration: float | int = Field(0, description="移动持续时间")
    use_pynput: bool = Field(False, description="是否使用pynput库点击")

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        super().run_command()
        debug(f"<{self.name}> 点击坐标为: {self.template_img_center}")
        self.click_image(self.use_pynput)

    def click_image(self, use_pynput) -> None:
        """
        点击图片
        """
        if self.template_img_center:
            # 使用 pynput 进行移动和点击操作
            if use_pynput:
                _click_with_pynput(self.template_img_center, self.button,
                                   self.duration, self.interval, self.clicks)
            # 使用 pyautogui 库进行点击操作
            else:
                _click_with_pyautogui(self.template_img_center, self.button,
                                      self.duration, self.interval, self.clicks)


class ImageOcrCmd(RetryCmd):
    """
    <文字全屏识别> 指令

    用于识别全屏（支持多显示器）中的文字，返回给定文本的匹配结果

    Attributes:
        name:(str): 指令名称
        retries:(int): 指令重复执行次数
        error_retries:(int): 指令执行出错时的重试次数
        error_retries_time:(float|int): 指令执行出错时的重试间隔时间
        is_active:(bool): 指令是否启用

        threshold:(float): 匹配度阈值
    """

    name: str = Field("文字识别", description="指令名称")
    retries: int = Field(0, description="指令重复执行次数")
    error_retries: int = Field(0, description="指令执行出错时的重试次数")
    error_retries_time: float | int = Field(0, description="指令执行出错时的重试间隔时间")
    is_active: bool = Field(True, description="指令是否启用")

    text: str = Field(None, description="待识别的文本")
    match_mode: str = Field("完全匹配", description="文字匹配模式")
    is_ignore_case: bool = Field(False, description="对于字母是否忽略大小写")
    use_regex: bool = Field(False, description="是否使用正则表达式匹配")
    threshold: float = Field(default_factory=get_ocr_threshold, description="匹配度阈值")

    _matching_boxes: list[tuple[str,tuple[int,int,int,int]]] = []  # 存储所有匹配成功的文本区域框

    def __init__(self, ocr, **kwargs):
        super(ImageOcrCmd, self).__init__(**kwargs)
        self._ocr = ocr

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        tool = EasyScreenshot()
        try:
            img_array = tool.grab_full()
            # 创建 OCRTool 对象, 同时加载模型
            start_load_model_time = time.time()
            if self._ocr:  # 如果已经提前加载模型，直接使用
                ocr = self._ocr
            else:
                ocr = OCRTool(
                    det_model_dir=DET_MODEL_DIR,
                    rec_model_dir=REC_MODEL_DIR,
                    cls_model_dir=CLS_MODEL_DIR,
                    use_angle_cls=False)
            print(f"加载模型耗时: {time.time() - start_load_model_time:.5f} 秒") if _DEBUG else None

            result = ocr.perform_ocr(img_array)
            if not result:
                raise CommandRunningException("识别失败")
            matching_boxes = find_matching_texts(result, text=self.text,
                                                 match_mode=self.match_mode,
                                                 ignore_case=self.is_ignore_case,
                                                 use_regex=self.use_regex,
                                                 confidence_threshold=self.threshold)
            if not matching_boxes:
                raise CommandRunningException("文字匹配结果为空")

            self._matching_boxes = matching_boxes
        except Exception as e:
            raise CommandRunningException(e)
        finally:
            tool.close()

    @property
    def matching_boxes(self) -> list[tuple[str, tuple[int, int, int, int]]]:
        """
        获取匹配成功的结果列表 [(str1, (x1, y1, x2, y2)), (str2, (x1, y1, x2, y2)), ...]
        """
        return self._matching_boxes

    @matching_boxes.setter
    def matching_boxes(self, value: list[tuple[str, tuple[int, int, int, int]]]):
        self._matching_boxes = value


class ImageOcrClickCmd(ImageOcrCmd):
    """
    <文字识别点击> 指令

    用于点击识别匹配成功的结果

    Attributes:
        name: (str): 指令名称
        retries: (int): 指令重复执行次数
        error_retries: (int): 指令执行出错时的重试次数
        error_retries_time: (float|int): 指令执行出错时的重试间隔时间
        is_active: (bool): 指令是否启用

        text: (str): 待识别的文本
        match_mode: (str): 文字匹配模式
        is_ignore_case: (bool): 对于字母是否忽略大小写
        threshold: (float): 匹配度阈值

        clicks: (int): 点击次数
        interval: (float|int): 点击间隔
        duration: (float|int): 移动持续时间
        button: (str): 点击的鼠标按键类型 ('left', 'right', 'middle')
        use_pynput: (bool): 是否使用pynput库点击
    """

    name: str = Field("文字识别点击", description="指令名称")
    retries: int = Field(0, description="指令重复执行次数")
    error_retries: int = Field(0, description="指令执行出错时的重试次数")
    error_retries_time: float | int = Field(0, description="指令执行出错时的重试间隔时间")
    is_active: bool = Field(True, description="指令是否启用")

    text: str = Field(None, description="待识别的文本")
    match_mode: str = Field("完全匹配", description="文字匹配模式")
    is_ignore_case: bool = Field(False, description="对于字母是否忽略大小写")
    use_regex: bool = Field(False, description="是否使用正则表达式匹配")
    threshold: float = Field(default_factory=get_ocr_threshold, description="匹配度阈值")

    clicks: int = Field(1, description="点击次数")
    interval: float | int = Field(0.2, description="点击间隔")
    duration: float | int = Field(0, description="移动持续时间")
    button: str = Field("left", description="点击的鼠标按键类型 ('left', 'right', 'middle')")
    use_pynput: bool = Field(False, description="是否使用pynput库点击")

    _matching_boxes_center: list[tuple[int, int]] = []  # 存储所有匹配成功的文本区域中心点坐标

    def __init__(self, ocr: OCRTool = None, **kwargs):
        super(ImageOcrCmd, self).__init__(**kwargs)
        self._ocr = ocr

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        super().run_command(**kwargs)
        if self.matching_boxes:
            debug(f"点击的文本区域: {self.matching_boxes[0]}")
            self.click_text(self.use_pynput)
        else:
            debug(f"文字匹配结果为空")

    @print_func_time(debug=_DEBUG)
    def click_text(self, use_pynput: bool):
        """ 点击距离最近的文字识别匹配区域中心点
        :param use_pynput: 是否使用 pynput 库进行点击
        """
        # 获取所有匹配成功的文本区域坐标
        matching_boxes = [box[1] for box in self.matching_boxes]
        # 计算中心点
        self._matching_boxes_center = [((box[0] + box[2]) // 2, (box[1] + box[3]) // 2) for box in matching_boxes]
        # 计算当前鼠标与各个中心点的距离
        mouse_pos = pyautogui.position()
        nearest_center = get_closest_point(*mouse_pos, centers=self._matching_boxes_center)
        # 点击距离最近的中心点
        if use_pynput:
            _click_with_pynput(nearest_center, self.button, self.duration, self.interval, self.clicks)
        else:
            _click_with_pyautogui(nearest_center, self.button, self.duration, self.interval, self.clicks)

    @property
    def matching_boxes_center(self):
        """
        获取所有匹配成功的文本区域中心点
        :return:
        """
        return self._matching_boxes_center

    @matching_boxes_center.setter
    def matching_boxes_center(self, value: list[tuple[int, int]]):
        """
        设置所有匹配成功的文本区域中心点
        :param value:
        """
        self._matching_boxes_center = value
