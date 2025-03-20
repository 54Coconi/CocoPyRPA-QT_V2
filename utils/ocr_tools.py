"""
文字识别模块

"""
import os
import re
import time
import cv2
import numpy as np
import pyautogui
from paddleocr import PaddleOCR

from utils.debug import print_func_time


_DEBUG = True

# 当前文件路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# OCR模型路径
# 当前文件路径的上一级目录下的模型
DET_MODEL_DIR = os.path.join(CURRENT_DIR, '..', 'models', 'det', 'ch', 'ch_PP-OCRv4_det_infer')
REC_MODEL_DIR = os.path.join(CURRENT_DIR, '..', 'models', 'rec', 'ch', 'ch_PP-OCRv4_rec_infer')
CLS_MODEL_DIR = os.path.join(CURRENT_DIR, '..', 'models', 'cls', 'ch', 'ch_PP-OCRv4_cls_infer')
# DET_MODEL_DIR = '/models/det/ch/ch_PP-OCRv4_det_infer'
# REC_MODEL_DIR = '/models/rec/ch/ch_PP-OCRv4_rec_infer'
# CLS_MODEL_DIR = '/models/cls/ch/ch_PP-OCRv4_cls_infer'

# 颜色常量(BGR格式)
RECTANGLE_COLOR = [
    (255, 0, 0),  # 蓝色
    (255,175,0),  # 青色
    (0, 255, 0),  # 绿色
    (0, 0, 255),  # 红色
]


@print_func_time(debug=_DEBUG)
def find_matching_texts(result, text="", match_mode="完全匹配", ignore_case=False,
                        use_regex=False, confidence_threshold=0.0) -> list[tuple[str, tuple[int, int, int, int]]]:
    """
    从OCR识别结果中匹配指定文本并返回其文本和文本区域框

    :param result: OCR识别结果
    :param text: 待匹配的文字，默认为空
    :param match_mode: 匹配模式 ("完全匹配" 或 "部分匹配")，默认为 "完全匹配"
    :param ignore_case: 是否忽略大小写，默认为 False
    :param use_regex: 是否使用正则表达式匹配，默认为 False
    :param confidence_threshold: 置信度阈值，默认为 0.0
    :return: 匹配成功的结果列表，每个元素为 (recognized_text, (x1, y1, x2, y2))
    """
    matching_results = []  # 用于存储匹配成功的结果
    pattern = None  # 初始化为 None，避免未赋值错误

    # 编译正则表达式（如果启用正则匹配）
    if use_regex:
        try:
            flags = re.IGNORECASE if ignore_case else 0
            pattern = re.compile(text, flags)
        except re.error as e:
            print(f"正则表达式编译失败: {e}")
            return []  # 返回空列表

    # 遍历识别结果
    for line in result:
        for detection in line:
            # 获取识别到的文本、区域框和置信度
            coords = detection[0]  # 文本块的四个顶点坐标
            recognized_text = detection[1][0]  # 原始识别文本
            confidence = detection[1][1]  # 置信度

            # 跳过低置信度的结果
            if confidence < confidence_threshold:
                continue

            # 处理忽略大小写的匹配（不改变原始文本，仅改变比较方式）
            comparison_text = recognized_text.lower() if ignore_case else recognized_text

            # 根据匹配模式进行匹配
            if use_regex:
                if pattern.search(comparison_text):  # 正则表达式匹配
                    matching_results.append((recognized_text, _extract_bounding_box(coords)))
            elif match_mode == "完全匹配" and comparison_text == (text.lower() if ignore_case else text):
                matching_results.append((recognized_text, _extract_bounding_box(coords)))
            elif match_mode == "部分匹配" and (text.lower() if ignore_case else text) in comparison_text:
                matching_results.append((recognized_text, _extract_bounding_box(coords)))
            elif match_mode not in ["完全匹配", "部分匹配"]:
                raise ValueError(f"无效的匹配模式 '{match_mode}',应为 '完全匹配' 或 '部分匹配'")

    return matching_results


def _extract_bounding_box(coords) -> tuple:
    """
    从OCR的多边形顶点提取矩形框
    :param coords: OCR文本块的四个顶点坐标
    :return: (x1, y1, x2, y2) 的四元组表示的矩形框
    """
    x1, y1 = int(coords[0][0]), int(coords[0][1])  # 左上角
    x2, y2 = int(coords[2][0]), int(coords[2][1])  # 右下角
    return x1, y1, x2, y2


class OCRTool:
    """
    OCR工具类，支持截屏、OCR识别、结果显示及保存
    """

    def __init__(self, lang='ch',
                 det_model_dir=DET_MODEL_DIR,
                 rec_model_dir=REC_MODEL_DIR,
                 cls_model_dir=CLS_MODEL_DIR,
                 use_angle_cls=True):
        """
        初始化OCR工具类
        :param lang: 语言类型（'ch' 或 'en' 等）
        :param det_model_dir: 检测模型路径
        :param rec_model_dir: 识别模型路径
        :param cls_model_dir: 分类模型路径
        :param use_angle_cls: 是否启用角度分类器,如果为 True，则可以识别旋转 180 度的文本. 如果没有文本旋转 180 度,请使用 cls=False 以获得更好的性能
        """
        self.use_angle_cls = use_angle_cls
        if not os.path.exists(det_model_dir):
            raise FileNotFoundError(f"检测模型路径不存在：{det_model_dir}")
        if not os.path.exists(rec_model_dir):
            raise FileNotFoundError(f"识别模型路径不存在：{rec_model_dir}")
        if not os.path.exists(cls_model_dir):
            raise FileNotFoundError(f"分类模型路径不存在：{cls_model_dir}")

        self.ocr = PaddleOCR(lang=lang,
                             show_log=False,
                             det_model_dir=det_model_dir,
                             rec_model_dir=rec_model_dir,
                             cls_model_dir=cls_model_dir,
                             use_angle_cls=self.use_angle_cls)

    @staticmethod
    @print_func_time(debug=_DEBUG)
    def capture_screen(image_path: str, region: tuple = None):
        """
        截取屏幕并保存为图片文件
        :param image_path: 保存的图片路径
        :param region: 截屏区域，格式为 (x1, y1, x2, y2)
        :return: None
        """
        if region is None or region == ():
            # 截取全屏
            pyautogui.screenshot(image_path)
        else:
            # 截取指定区域
            pyautogui.screenshot(image_path, region=region)

        print(f"截图成功：{image_path}, 区域：{region}")

    @print_func_time(debug=_DEBUG)
    def perform_ocr(self, image):
        """
        对指定图片执行OCR识别
        :param image: 图片,可以是np.ndarray、数组、文件路径 或 BytesIO 对象
        :return: OCR识别结果
        """
        assert isinstance(image, (np.ndarray, list, str, bytes))
        print("开始OCR识别...")
        result = self.ocr.ocr(image, cls=self.use_angle_cls)
        return result

    @staticmethod
    def draw_results(image_path: str, results,
                     rectangle_color=RECTANGLE_COLOR[2], num_color=RECTANGLE_COLOR[1]):
        """
        绘制OCR识别结果到图片中
        :param image_path: 原图片路径,可以是np.ndarray、数组、文件路径 或 BytesIO 对象
        :param results: OCR识别结果
        :param rectangle_color: 矩形框颜色(BGR格式)
        :param num_color: 文本块编号颜色(BGR格式)
        :return: 带有矩形框和文本标注的图片
        """
        if os.path.isfile(image_path):
            _img = cv2.imread(image_path)
        else:
            _img = cv2.cvtColor(image_path, cv2.COLOR_BGR2RGB)
        color = rectangle_color  # 矩形框颜色
        _num_color = num_color
        result_boxes = 0  # 文本块计数

        for line in results:
            for detection in line:
                result_boxes += 1
                # coords: 文本块的四个顶点坐标,按顺时针从左上角开始,格式为 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                coords = detection[0]
                text_info = detection[1]  # 识别到的文本和置信度
                text, confidence = text_info  # 分别获取文本和置信度

                # 左上角坐标 [x1, y1]
                top_left = (int(coords[0][0]), int(coords[0][1]))
                # 右下角坐标 [x3, y3]
                bottom_right = (int(coords[2][0]), int(coords[2][1]))
                # 右上角坐标（用于绘制文字） [x2, y2]
                top_right = (int(coords[1][0]), int(coords[1][1]))

                # 绘制矩形框, 颜色为红色(BGR格式), 线条宽度为 1
                cv2.rectangle(_img, top_left, bottom_right, color, 1)
                # 绘制文本块编号
                text_pos = (bottom_right[0],
                            int(bottom_right[1] - (bottom_right[1] - top_right[1]) / 2))
                cv2.putText(_img, f"{result_boxes}", text_pos,
                            cv2.FONT_HERSHEY_TRIPLEX, 0.5, _num_color)

                # 输出识别结果
                print(f"----------------第{result_boxes}个----------------") if _DEBUG else None
                print(f"【文本】:\t{text}\n【置信度】:\t{confidence:.2f}") if _DEBUG else None

        return _img

    @staticmethod
    def show_results(image, save=True, save_path_prefix="OcrTest", show=False):
        """
        显示识别结果图片并选择是否保存
        :param image: 带有识别结果的图片
        :param save: 是否保存图片（默认False）
        :param save_path_prefix: 保存图片的前缀
        :param show: 是否显示图片（默认False）
        :return: None
        """
        if save:
            save_path = f"{save_path_prefix}-{time.strftime('%Y-%m-%d-%H%M%S')}.png"
            cv2.imwrite(save_path, image)
            print(f"图片已保存：{save_path}")

        if show:
            cv2.imshow("OCR Results", image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()


if __name__ == '__main__':
    print(CURRENT_DIR)
    print(DET_MODEL_DIR)
    print(REC_MODEL_DIR)
    print(CLS_MODEL_DIR)
