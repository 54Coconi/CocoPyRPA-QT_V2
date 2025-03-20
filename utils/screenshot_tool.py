"""
截图工具模块
Path: utils/screenshot_tool.py
"""


import os
import time

import mss
import ctypes
import mss.tools
import numpy as np
import pygetwindow as gw
from typing import Tuple, Optional

from mss.screenshot import ScreenShot

from utils.debug import print_func_time


_DEBUG = True


class ScreenshotTool:
    """
    截图工具类
    """
    def __init__(self):
        """初始化 ScreenshotTool 类，支持多显示器适配及 DPI 缩放 """
        self.sct = mss.mss()
        self.dpi_scale = self._get_dpi_scale()
        self.image = None
        print(f"DPI 缩放比例: {self.dpi_scale}\n" if _DEBUG else "", end="")

    @print_func_time(_DEBUG)
    def full_screen(self, output_file: Optional[str] = None, file_format: str = "png") -> ScreenShot | None:
        """
        截取全屏截图，适配多个显示器
        :param output_file: 输出文件路径
        :param file_format: 保存格式，支持 png, jpeg, bmp
        """
        monitor = self.sct.monitors[0]  # 捕获所有显示器内容
        screenshot = self.sct.grab(monitor)  # 捕获所有显示器内容
        if output_file:
            self._save_screenshot(screenshot, output_file, file_format)
            print(f"全屏截图已保存至: {output_file}\n" if _DEBUG else "", end="")
        else:
            self.image = screenshot
            print("全屏截图已保存到内存中\n" if _DEBUG else "", end="")
            return screenshot

    @print_func_time(_DEBUG)
    def region_screenshot(self, region: Tuple[int, int, int, int], output_file: Optional[str] = None, file_format: str = "png") -> ScreenShot | None:
        """
        截取指定区域的截图，适配 DPI 缩放。
        :param region: 截图区域 (left, top, width, height)。
        :param output_file: 输出文件路径。
        :param file_format: 保存格式，支持 png, jpeg, bmp。
        """
        # 调整区域坐标和尺寸以适配 DPI 缩放
        scaled_region = self._scale_region(region)
        if not self._validate_region(scaled_region):
            print("区域参数无效！请确保 left, top, width, height 都是正数且区域不为空")
            return

        screenshot = self.sct.grab({
            "left": scaled_region[0],
            "top": scaled_region[1],
            "width": scaled_region[2],
            "height": scaled_region[3]
        })
        if output_file:
            self._save_screenshot(screenshot, output_file, file_format)
            print(f"区域截图已保存至: {output_file}\n" if _DEBUG else "", end="")
        else:
            self.image = screenshot
            print("区域截图已保存到内存中\n" if _DEBUG else "", end="")
            return screenshot

    @print_func_time(_DEBUG)
    def active_window(self, output_file: Optional[str] = None, file_format: str = "png") -> None | ScreenShot | str:
        """
        截取当前活动窗口的截图，适配 DPI 缩放
        :param output_file: 输出文件路径
        :param file_format: 保存格式，支持 png, jpeg, bmp
        :return: 输出文件路径或 None
        """
        try:
            active_window = gw.getActiveWindow()
            if not active_window:
                print("未找到活动窗口，无法截图")
                return None

            bbox = (
                active_window.left,
                active_window.top,
                active_window.width,
                active_window.height
            )
            # 调整窗口边界以适配 DPI 缩放
            scaled_bbox = self._scale_region(bbox)
            if not self._validate_region(scaled_bbox):
                print("活动窗口超出屏幕范围，无法截图")
                return None

            screenshot = self.sct.grab({
                "left": scaled_bbox[0],
                "top": scaled_bbox[1],
                "width": scaled_bbox[2],
                "height": scaled_bbox[3]
            })
            if output_file:
                self._save_screenshot(screenshot, output_file, file_format)
                print(f"活动窗口截图已保存至: {output_file}\n" if _DEBUG else "", end="")
            else:
                self.image = screenshot
                print("活动窗口截图已保存到内存中\n" if _DEBUG else "", end="")
                return screenshot
            return output_file
        except Exception as e:
            print(f"活动窗口截图失败: {e}")
            return None

    @print_func_time(_DEBUG)
    def get_image_as_numpy_array(self) -> np.ndarray:
        """
        将截图转换为 numpy 数组
        :return: 返回截图的 numpy 数组
        """
        if self.image is None:
            raise ValueError("没有截图数据，请先截取图像。")

        # 提取屏幕截图的 RGB 数据
        screenshot_rgb = self.image.rgb

        # 获取截图的宽度和高度
        width, height = self.image.size

        # 将 RGB 数据转换为 NumPy 数组，reshape 成 (height, width, 3) 的形状
        img_array = np.frombuffer(screenshot_rgb, dtype=np.uint8).reshape((height, width, 3))

        return img_array

    def _save_screenshot(self, screenshot, output_file: str, file_format: str) -> None:
        """保存截图到指定文件，支持多种格式。"""
        file_format = file_format.lower()
        valid_formats = {"png", "jpeg", "bmp"}

        if file_format not in valid_formats:
            raise ValueError(f"无效的文件格式: {file_format}，支持的格式有: {valid_formats}")

        if not output_file.lower().endswith(f".{file_format}"):
            output_file = f"{os.path.splitext(output_file)[0]}.{file_format}"

        mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_file)

    def _validate_region(self, region: Tuple[int, int, int, int]) -> bool:
        """验证区域参数是否合法。"""
        left, top, width, height = region
        return all(isinstance(value, int) and value >= 0 for value in region) and width > 0 and height > 0

    def _scale_region(self, region: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """
        根据 DPI 缩放调整区域坐标。
        :param region: (left, top, width, height)
        :return: 调整后的区域
        """
        left, top, width, height = region
        return (
            int(left * self.dpi_scale),
            int(top * self.dpi_scale),
            int(width * self.dpi_scale),
            int(height * self.dpi_scale)
        )

    def _get_dpi_scale(self) -> float:
        """
        获取当前屏幕的 DPI 缩放比例
        :return: DPI 缩放比例
        """
        try:
            # 使用 ctypes 调用 Windows API 获取 DPI 信息
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return dpi / 96.0  # 96 DPI 是标准比例
        except Exception as e:
            print(f"无法获取 DPI 缩放比例，默认使用 1.0: {e}")
            return 1.0

    def close(self):
        """释放资源。"""
        self.sct.close()


# 示例用法
if __name__ == "__main__":
    tool = ScreenshotTool()
    time.sleep(2)
    # 全屏截图
    tool.full_screen()

    # 区域截图
    tool.region_screenshot((100, 100, 800, 600), "region_screenshot.png")

    # 活动窗口截图
    tool.active_window("active_window.png")

    # 释放资源
    tool.close()
