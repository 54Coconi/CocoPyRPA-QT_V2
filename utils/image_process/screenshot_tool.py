"""
屏幕截图工具

支持:
    1. 全屏截图（多显示器）
    2. 区域截图
    3. 激活窗口截图（Windows / macOS / Linux 分别实现）

    同时内置了 Open CV 模板匹配功能，支持全屏模板匹配和指定标题窗口内模板匹配
    适配多显示器、不同分辨率、不同 DPI 缩放的场景
"""
import ctypes
import platform
import re
import subprocess
import sys
from ctypes import wintypes
from typing import Tuple

import cv2
import mss
import numpy as np
from PIL import Image

if platform.system() == "Windows":
    import win32gui
    import win32con
elif platform.system() == "Darwin":
    import Quartz
    from AppKit import NSWorkspace
elif platform.system() == "Linux":
    pass


# 修复 Windows DPI 缩放导致的截图比例异常
# ---------------------------------------------------------
#                           Note
# ---------------------------------------------------------
# 如果进程在启动时没有声明自己是 DPI aware，
# 那么 Windows 会给它一个缩放后的虚拟坐标系，
# mss 截到的图是经过缩放补偿的，结果可能出现黑边或比例异常
if sys.platform.startswith("win"):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # Windows 7 fallback
        except Exception:
            pass

# 基本类型
Box = Tuple[int, int, int, int]
Point2D = Tuple[int, int]
# DWM 窗口边框宽度
DWMWA_EXTENDED_FRAME_BOUNDS = 9


# ============================== utils ==============================
def get_client_area_rect(hwnd):
    """
    获取窗口客户区（不含边框/阴影）的屏幕坐标
    """
    # 获取客户区大小（相对窗口左上角的坐标）
    left, top, right, bottom = win32gui.GetClientRect(hwnd)

    # 客户区左上角转换为屏幕坐标
    client_pos = win32gui.ClientToScreen(hwnd, (left, top))
    client_left, client_top = client_pos

    # 右下角也转换
    client_right_top = win32gui.ClientToScreen(hwnd, (right, bottom))
    client_right, client_bottom = client_right_top

    return client_left, client_top, client_right, client_bottom


def get_window_rect_no_shadow(hwnd):
    """
    获取窗口矩形（保留标题栏和边框，但去掉 Windows 阴影）
    适用 Windows Vista 及以上系统。
    """
    rect = wintypes.RECT()
    dwmapi = ctypes.windll.dwmapi
    res = dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect),
        ctypes.sizeof(rect)
    )
    if res != 0:  # 失败时回退到原方法
        import win32gui
        return win32gui.GetWindowRect(hwnd)
    return rect.left, rect.top, rect.right, rect.bottom


class ScreenshotTool:
    """
    截图工具
    """

    def __init__(self):
        self.system = platform.system()
        self.sct = mss.mss()  # 复用 mss 实例，减少初始化开销

    @staticmethod
    def _mss_to_pil(img):
        """mss raw -> PIL.Image (RGB)"""
        return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")

    @staticmethod
    def _mss_to_cv2(img):
        """mss raw -> numpy.ndarray (BGR)"""
        arr = np.frombuffer(img.bgra, dtype=np.uint8).reshape(img.height, img.width, 4)
        return arr[:, :, :3]  # 去掉 alpha 通道，保持 BGR 顺序

    # =========================== 截图功能 ===========================
    # 截取全屏
    def capture_fullscreen(self, save_path=None, as_cv2=False, virtual=False, screen_index=None):
        """
        截取全屏（支持多显示器）
        :param save_path: 保存路径（可选）
        :param as_cv2: 是否返回 OpenCV 格式
        :param virtual: 是否截取虚拟大屏（可能有黑边），为 True 时 screen_index 参数无效
        :param screen_index: 指定物理屏幕编号（从 1 开始），默认为 None 表示所有物理屏
        """
        results = []

        if virtual:
            # 原来的方式，可能会有黑边
            img = self.sct.grab(self.sct.monitors[0])
            results.append(self._mss_to_cv2(img) if as_cv2 else self._mss_to_pil(img))
        else:
            monitors = self.sct.monitors[1:]  # 跳过虚拟大屏
            if screen_index:
                if screen_index < 1 or screen_index > len(monitors):
                    raise ValueError(f"Invalid screen index: {screen_index}")
                monitors = [monitors[screen_index - 1]]  # 获取指定屏幕

            for mon in monitors:
                img = self.sct.grab(mon)
                results.append(self._mss_to_cv2(img) if as_cv2 else self._mss_to_pil(img))

        # 如果只截取一个屏幕，直接返回
        if len(results) == 1:
            out = results[0]
            if save_path:
                if as_cv2:
                    import cv2
                    cv2.imwrite(save_path, out)
                else:
                    out.save(save_path)
            return out

        return results

    # 截取所有物理屏幕并拼接成一张大图
    def capture_fullscreen_stitched(self, save_path=None, as_cv2=False):
        """
        截取所有物理屏幕并拼接成一张图，同时返回屏幕坐标映射表
        :param save_path: 拼接大图保存路径
        :param as_cv2: 是否返回 OpenCV 格式
        :return: (拼接图, mapping)
                拼接图: PIL.Image 或 np.ndarray
                mapping: {screen_index: (offset_x, offset_y)}
                          offset_x/offset_y 是该屏幕左上角相对于拼接图的坐标
        """
        monitors = self.sct.monitors[1:]
        if not monitors:
            raise RuntimeError("No physical monitors found.")

        # 计算画布边界
        min_x = min(m["left"] for m in monitors)
        min_y = min(m["top"] for m in monitors)
        max_x = max(m["left"] + m["width"] for m in monitors)
        max_y = max(m["top"] + m["height"] for m in monitors)

        canvas_w = max_x - min_x
        canvas_h = max_y - min_y

        from PIL import Image
        stitched_img = Image.new("RGB", (canvas_w, canvas_h))
        mapping = {}

        for idx, mon in enumerate(monitors, start=1):
            img = self.sct.grab(mon)
            pil_img = self._mss_to_pil(img)
            offset_x = mon["left"] - min_x
            offset_y = mon["top"] - min_y
            stitched_img.paste(pil_img, (offset_x, offset_y))
            mapping[idx] = (offset_x, offset_y)

        if as_cv2:
            import cv2
            stitched_cv2 = cv2.cvtColor(np.array(stitched_img), cv2.COLOR_RGB2BGR)
            if save_path:
                cv2.imwrite(save_path, stitched_cv2)
            return stitched_cv2, mapping

        if save_path:
            stitched_img.save(save_path)

        return stitched_img, mapping

    # 按区域截图
    def capture_region(self, region: Box, save_path=None, as_cv2=False):
        """
        按区域截图
        :param region: 区域坐标 Box(left, top, right, bottom)
        :param save_path: 保存路径
        :param as_cv2: 是否返回 OpenCV 格式，默认返回 PIL Image
        """
        left, top, right, bottom = region
        width, height = right - left, bottom - top
        img = self.sct.grab({"left": left, "top": top, "width": width, "height": height})
        if as_cv2:
            arr = self._mss_to_cv2(img)
            if save_path:
                import cv2
                cv2.imwrite(save_path, arr)
            return arr
        else:
            pil_img = self._mss_to_pil(img)
            if save_path:
                pil_img.save(save_path)
            return pil_img

    # 激活窗口截图
    def capture_active_window(self, title=None, make_active=False, regex=False, as_cv2=False):
        """
        激活窗口截图
        :param title: 窗口标题
        :param make_active: 是否激活窗口
        :param regex: 是否使用正则匹配
        :param as_cv2: 是否返回 OpenCV 格式
        """
        if self.system == "Windows":
            return self._capture_active_window_windows(title, make_active, regex, as_cv2)
        elif self.system == "Darwin":
            return self._capture_active_window_macos(title, make_active, as_cv2)
        elif self.system == "Linux":
            return self._capture_active_window_linux(title, make_active, as_cv2)
        else:
            raise NotImplementedError(f"{self.system} not supported")

    # 坐标转换 (拼接图 -> 真实屏幕)
    def stitched_to_screen_coords(self, stitched_x, stitched_y, mapping) -> tuple:
        """
        将拼接图中的坐标转换为真实屏幕坐标和屏幕编号
        :param stitched_x: 拼接图中的 X 坐标
        :param stitched_y: 拼接图中的 Y 坐标
        :param mapping: capture_fullscreen_stitched 返回的 mapping 字典
        :return: (screen_index, real_x, real_y)  或  (None, None, None) 如果不在任何屏幕内
        """
        for idx, (ox, oy) in mapping.items():
            mon = self.sct.monitors[idx]
            if ox <= stitched_x < ox + mon["width"] and oy <= stitched_y < oy + mon["height"]:
                real_x = stitched_x - ox + mon["left"]
                real_y = stitched_y - oy + mon["top"]
                return idx, real_x, real_y
        return None, None, None

    # 坐标转换 (真实屏幕 -> 拼接图)
    def screen_to_stitched_coords(self, real_x, real_y, mapping) -> tuple:
        """
        从真实屏幕坐标（某个显示器上的绝对位置）映射回拼接大图上的坐标位置

        当在真实屏幕中得到了一个点击点、检测点，想在拼接图上做可视化标记时很有用

        :param real_x: 真实屏幕 X 坐标
        :param real_y: 真实屏幕 Y 坐标
        :param mapping: capture_fullscreen_stitched 返回的 mapping 字典
        :return: (stitched_x, stitched_y) 或 (None, None) 如果坐标不在任何已知屏幕范围内
        """
        for idx, (ox, oy) in mapping.items():
            mon = self.sct.monitors[idx]
            if mon["left"] <= real_x < mon["left"] + mon["width"] and \
                    mon["top"] <= real_y < mon["top"] + mon["height"]:
                stitched_x = real_x - mon["left"] + ox
                stitched_y = real_y - mon["top"] + oy
                return stitched_x, stitched_y
        return None, None

    # =========================== Open CV ===========================

    def match_template(self, template_img, method=cv2.TM_CCOEFF_NORMED,
                       threshold=0.8, return_screen_coords=False,
                       max_results=None, save_path=None, nms_threshold=0.5):
        """
        在拼接全屏截图中进行模板匹配，支持单个或多个结果，带 NMS 去重，可保存标注图
        :param template_img: 模板图 (numpy array, BGR 格式)
        :param method: OpenCV 模板匹配方法
        :param threshold: 匹配阈值
        :param return_screen_coords: True返回真实屏幕坐标，False返回拼接图坐标
        :param max_results: 限制返回的最大匹配数量（None 表示全部）
        :param save_path: 保存标注后的拼接截图路径（None表示不保存）
        :param nms_threshold: NMS去重IOU阈值
        :return: [(center_x, center_y, score), ...] 匹配结果列表
        """
        full_img, mapping = self.capture_fullscreen_stitched(as_cv2=True)

        if template_img is None or not isinstance(template_img, np.ndarray):
            raise ValueError("模板图必须是有效的 numpy 数组")

        h, w = template_img.shape[:2]

        # 模板匹配
        result = cv2.matchTemplate(full_img, template_img, method)
        locations = np.where(result >= threshold)

        boxes = []
        scores = []
        for pt_y, pt_x in zip(*locations):
            boxes.append([pt_x, pt_y, pt_x + w, pt_y + h])  # (x1, y1, x2, y2)
            scores.append(float(result[pt_y, pt_x]))
        boxes = np.array(boxes)
        scores = np.array(scores)

        # 执行NMS去重
        keep = self._nms(boxes, scores, nms_threshold)
        boxes = boxes[keep]
        scores = scores[keep]

        # 限制最大返回数量
        if max_results is not None and len(scores) > max_results:
            idxs = np.argsort(-scores)[:max_results]
            boxes = boxes[idxs]
            scores = scores[idxs]

        matches = []
        for (x1, y1, x2, y2), score in zip(boxes, scores):
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            if return_screen_coords:
                screen_idx, real_x, real_y = self.stitched_to_screen_coords(center_x, center_y, mapping)
                if screen_idx is not None:
                    matches.append((real_x, real_y, score))
            else:
                matches.append((center_x, center_y, score))

        # 保存标注图
        if save_path:
            annotated_img = full_img.copy()
            for (x1, y1, x2, y2), score in zip(boxes, scores):
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 0, 255), 2, cv2.LINE_AA)
                cv2.putText(annotated_img, f"{score:.2f}", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA)
            cv2.imwrite(save_path, annotated_img)

        return matches

    def match_template_center(self, template_img, method=cv2.TM_CCOEFF_NORMED,
                              threshold=None, return_screen_coords=False, save_path=None) -> tuple:
        """
        在拼接全屏截图中进行模板匹配，并返回匹配模板的中心坐标
        :param template_img: 模板图 (numpy array, BGR 格式)
        :param method: OpenCV 模板匹配方法
        :param threshold: 匹配阈值（None 表示忽略阈值）
        :param return_screen_coords: 如果为 True，返回真实屏幕坐标，否则返回拼接图坐标
        :param save_path: 匹配结果图片保存路径
        :return: (center_x, center_y, max_val) 或 (None, None, None) 如果未匹配到
        """
        # 截取拼接全屏图
        full_img, mapping = self.capture_fullscreen_stitched(as_cv2=True)

        if template_img is None or not isinstance(template_img, np.ndarray):
            raise ValueError("模板图必须是有效的 numpy 数组")

        # 模板匹配
        result = cv2.matchTemplate(full_img, template_img, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # 阈值判断
        if threshold is not None and max_val < threshold:
            return None, None, None

        # 计算模板中心点（拼接图坐标）
        h, w = template_img.shape[:2]
        center_x = max_loc[0] + w // 2
        center_y = max_loc[1] + h // 2

        if return_screen_coords:
            screen_idx, real_center_x, real_center_y = self.stitched_to_screen_coords(center_x, center_y, mapping)
            if screen_idx is None:
                return None, None, None
            return real_center_x, real_center_y, max_val
        else:
            return center_x, center_y, max_val

    def match_template_all_centers(self, template_img, method=cv2.TM_CCOEFF_NORMED,
                                   threshold=0.8, return_screen_coords=False) -> list:
        """
        在拼接全屏截图中进行批量模板匹配，并返回所有匹配模板的中心坐标
        :param template_img: 模板图 (numpy array, BGR 格式)
        :param method: OpenCV 模板匹配方法
        :param threshold: 匹配阈值（默认 0.8）
        :param return_screen_coords: 如果为 True，返回真实屏幕坐标，否则返回拼接图坐标
        :return: [(center_x, center_y, score), ...] 匹配结果列表
        """
        full_img, mapping = self.capture_fullscreen_stitched(as_cv2=True)

        if template_img is None or not isinstance(template_img, np.ndarray):
            raise ValueError("模板图必须是有效的 numpy 数组")

        # 模板匹配
        result = cv2.matchTemplate(full_img, template_img, method)
        h, w = template_img.shape[:2]

        # 找到所有大于阈值的位置
        locations = np.where(result >= threshold)
        matches = []

        for pt_y, pt_x in zip(*locations):
            center_x = pt_x + w // 2
            center_y = pt_y + h // 2

            score = result[pt_y, pt_x]

            if return_screen_coords:
                screen_idx, real_x, real_y = self.stitched_to_screen_coords(center_x, center_y, mapping)
                if screen_idx is not None:
                    matches.append((real_x, real_y, float(score)))
            else:
                matches.append((center_x, center_y, float(score)))

        return matches

    def match_template_in_window(self, hwnd=None, title=None, template_img=None,
                                 method=cv2.TM_CCOEFF_NORMED, threshold=0.8,
                                 return_screen_coords=False, max_results=None,
                                 save_path=None, nms_threshold=0.5, regex=False, make_active=False):
        """
        在指定窗口内部进行模板匹配，避免匹配到其它窗口的模板

        支持两种输入方式 → 直接传入 hwnd 句柄或通过 title 标题查找窗口

        :param hwnd: 目标窗口句柄（优先使用），为 None 时通过 title 查找
        :param title: 目标窗口标题（可部分匹配或正则匹配，若 regex=True 则 title 为正则表达式）
        :param template_img: 模板图 (numpy array, BGR 格式)
        :param method: OpenCV 模板匹配方法
        :param threshold: 匹配阈值
        :param return_screen_coords: 是否返回真实屏幕坐标
        :param max_results: 最大返回数量（默认 None 表示返回全部）
        :param save_path: 保存标注结果路径
        :param nms_threshold: NMS 去重阈值
        :param regex: 是否正则匹配窗口标题，默认为 False
        :param make_active: 截图前是否激活窗口，会有一定的性能损耗
        :return: [(center_x, center_y, score), ...]
        """
        if template_img is None or not isinstance(template_img, np.ndarray):
            raise ValueError("模板图必须是有效的 numpy 数组")

        # 获取窗口句柄
        if hwnd is None:
            hwnd = None
            matched_hwnds = []

            def _enum_handler(h, _):
                win_text = win32gui.GetWindowText(h)
                if win_text:
                    if regex and re.search(title, win_text, re.IGNORECASE):
                        matched_hwnds.append(h)
                    elif not regex and title.lower() in win_text.lower():
                        matched_hwnds.append(h)
                return True

            win32gui.EnumWindows(_enum_handler, None)
            if matched_hwnds:
                hwnd = matched_hwnds[0]
            else:
                raise RuntimeError(f"未找到与标题 “{title}” 匹配的窗口")

        # 使用句柄激活窗口（可选）
        if make_active:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                import time
                time.sleep(0.3)
            except Exception as e:
                print(f"[WARN] 激活窗口失败: {e}")

        # 截取窗口区域（去阴影）
        left, top, right, bottom = get_window_rect_no_shadow(hwnd)
        _win_img = self.capture_region((left, top, right, bottom), as_cv2=True)

        # 模板匹配
        h, w = template_img.shape[:2]
        result = cv2.matchTemplate(_win_img, template_img, method)
        locations = np.where(result >= threshold)

        boxes = []
        scores = []
        for pt_y, pt_x in zip(*locations):
            boxes.append([pt_x, pt_y, pt_x + w, pt_y + h])
            scores.append(float(result[pt_y, pt_x]))
        boxes = np.array(boxes)
        scores = np.array(scores)

        # NMS 去重
        keep = self._nms(boxes, scores, nms_threshold)
        boxes = boxes[keep]
        scores = scores[keep]

        if max_results is not None and len(scores) > max_results:
            idxs = np.argsort(-scores)[:max_results]
            boxes = boxes[idxs]
            scores = scores[idxs]

        # 保存匹配结果：中心坐标 + 分数
        matches = []
        for (x1, y1, x2, y2), score in zip(boxes, scores):
            center_x = x1 + w // 2
            center_y = y1 + h // 2
            if return_screen_coords:
                matches.append((left + center_x, top + center_y, score))
            else:
                matches.append((center_x, center_y, score))

        # 保存标注图：矩形框 + 分数
        if save_path:
            annotated_img = _win_img.copy()
            for (x1, y1, x2, y2), score in zip(boxes, scores):
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(annotated_img, f"{score:.2f}", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            cv2.imwrite(save_path, annotated_img)

        return matches

    @staticmethod
    def _nms(boxes, scores, iou_threshold):
        """
        非极大值抑制 (NMS)

        用于去除重复的匹配结果，保留置信度最高的匹配框

        :param boxes: ndarray [N, 4] 格式 (x1, y1, x2, y2)
        :param scores: ndarray [N] 分数
        :param iou_threshold: IOU阈值
        :return: 保留的索引列表
        """
        if len(boxes) == 0:
            return []

        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]

        return keep

    # ---------------- Windows 实现 ----------------

    def _capture_active_window_windows(self, title, make_active, regex, as_cv2):
        hwnd = None
        if title:
            matched_hwnds = []

            def _enum_handler(h, _):
                win_text = win32gui.GetWindowText(h)
                if win_text:
                    if regex and re.search(title, win_text, re.IGNORECASE):
                        matched_hwnds.append(h)
                    elif not regex and title.lower() in win_text.lower():
                        matched_hwnds.append(h)
                return True

            win32gui.EnumWindows(_enum_handler, None)
            if matched_hwnds:
                hwnd = matched_hwnds[0]  # 取第一个
            else:
                raise RuntimeError(f"未找到与标题 '{title}' 匹配的窗口")
        else:
            # 未指定 title时，获取当前激活窗口
            hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            raise RuntimeError("未找到激活窗口")

        if make_active:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                import time
                time.sleep(0.1)  # 等待窗口激活
            except Exception as e:
                from config.app_config import warning
                warning(f"激活窗口 title='{title}' 失败：{e}")

        left, top, right, bottom = get_window_rect_no_shadow(hwnd)
        return self.capture_region((left, top, right, bottom), as_cv2=as_cv2)

    # ---------------- macOS 实现 ----------------
    def _capture_active_window_macos(self, title, make_active, as_cv2):
        options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
        window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)

        frontmost_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        pid = frontmost_app.processIdentifier()

        for window in window_list:
            if window.get("kCGWindowOwnerPID", None) == pid:
                bounds = window.get("kCGWindowBounds", {})
                x = int(bounds.get("X", 0))
                y = int(bounds.get("Y", 0))
                w = int(bounds.get("Width", 0))
                h = int(bounds.get("Height", 0))
                return self.capture_region((x, y, x + w, y + h), as_cv2=as_cv2)

        raise RuntimeError("No active window found on macOS.")

    # ---------------- Linux 实现 ----------------
    def _capture_active_window_linux(self, title, make_active, as_cv2):
        try:
            win_id = subprocess.check_output(["xdotool", "getactivewindow"]).strip().decode()
            geom = subprocess.check_output(["xwininfo", "-id", win_id]).decode()
            left, top, width, height = None, None, None, None
            for line in geom.splitlines():
                if "Absolute upper-left X" in line:
                    left = int(line.split(":")[1])
                elif "Absolute upper-left Y" in line:
                    top = int(line.split(":")[1])
                elif "Width" in line:
                    width = int(line.split(":")[1])
                elif "Height" in line:
                    height = int(line.split(":")[1])

            if None in (left, top, width, height):
                raise RuntimeError("Failed to get active window geometry on Linux.")

            return self.capture_region((left, top, left + width, top + height), as_cv2=as_cv2)
        except Exception as e:
            raise RuntimeError(f"Linux active window capture failed: {e}")

    def close(self):
        """
        关闭截图工具实例，释放相关资源
        
        该方法会关闭内部的 mss 实例，释放系统资源
        使用完截图工具后，应当调用此方法以避免资源泄露
        """
        self.sct.close()


# ======== 简化 API 封装 ========

class EasyScreenshot(ScreenshotTool):
    """
    简化版 API，便于快速调用常用截图/模板匹配功能。
    继承 ScreenshotTool，内部封装了高频使用场景的简化调用。
    """

    def grab_full(self, save_path=None, as_cv2=True):
        """
        快速截取所有屏幕的拼接图。

        :param save_path: 保存路径，必须是完整路径
        :param as_cv2: 默认为 True 返回 OpenCV (numpy array) 格式，False 则返回 PIL Image
        :return: 截图图像对象
        """
        img, _ = self.capture_fullscreen_stitched(save_path=save_path, as_cv2=as_cv2)
        return img

    def grab_screen(self, screen_index=1, as_cv2=True):
        """
        截取指定编号的屏幕
        
        :param screen_index: 屏幕编号（从1开始，1表示主屏）
        :param as_cv2: True 返回 OpenCV 格式，False 返回 PIL
        :return: 截图图像对象
        """
        return self.capture_fullscreen(screen_index=screen_index, as_cv2=as_cv2)

    def grab_window(self, title=None, regex=False, make_active=False, as_cv2=True):
        """
        截取活动窗口
        
        :param title: 窗口标题（支持部分匹配或正则匹配）。
        :param regex: 是否启用正则匹配标题。
        :param make_active: 截图前是否先激活该窗口。
        :param as_cv2: True 返回 OpenCV 格式，False 返回 PIL。
        :return: 截图图像对象。
        """
        return self.capture_active_window(title=title, regex=regex, make_active=make_active, as_cv2=as_cv2)

    def grab_region(self, left, top, right, bottom, as_cv2=True):
        """
        按指定矩形区域截图。
        
        :param left: 区域左上角 X 坐标。
        :param top: 区域左上角 Y 坐标。
        :param right: 区域右下角 X 坐标。
        :param bottom: 区域右下角 Y 坐标。
        :param as_cv2: True 返回 OpenCV 格式，False 返回 PIL。
        :return: 截图图像对象。
        """
        return self.capture_region((left, top, right, bottom), as_cv2=as_cv2)

    def find_template(self, template_path, threshold=0.8, return_screen_coords=True, save_path=None):
        """
        模板匹配封装：传入模板路径，返回匹配中心点坐标及分数。
        
        :param template_path: 模板图片文件路径。
        :param threshold: 匹配分数阈值（默认0.8）。
        :param return_screen_coords: True 返回真实屏幕坐标，False 返回拼接图坐标。
        :param save_path: 如果不为 None，将保存带标注矩形和分数的拼接截图到该路径。
        :return: [(center_x, center_y, score), ...] 匹配结果列表。
        """
        import cv2
        tmpl = cv2.imread(template_path)
        return self.match_template(template_img=tmpl, threshold=threshold,
                                   return_screen_coords=return_screen_coords, save_path=save_path)

    def find_template_in_window(self, title, template_path, threshold=0.8, return_screen_coords=True, save_path=None, regex=False, make_active=True):
        """
        指定窗口内模板匹配封装：传入窗口标题、模板路径，返回匹配中心点坐标及分数。

        :param title: 窗口标题（支持部分匹配或正则匹配）
        :param template_path: 模板图片文件路径
        :param threshold: 匹配分数阈值（默认0.8）
        :param return_screen_coords: True 返回真实屏幕坐标，False 返回拼接图坐标
        :param save_path: 如果不为 None，将保存带标注矩形和分数的拼接截图到该路径
        :param regex: 是否启用正则匹配标题
        :param make_active: 截图前是否先激活该窗口，内置了激活等待
        :return: [(center_x, center_y, score), ...] 匹配结果列表
        """
        import cv2
        tmpl = cv2.imread(template_path)
        return self.match_template_in_window(title=title, template_img=tmpl, threshold=threshold,
                                             return_screen_coords=return_screen_coords,
                                             save_path=save_path, regex=regex, make_active=make_active)

    def find_template_in_screen(self, screen_index, template_path, threshold=0.8, return_screen_coords=True, save_path=None):
        """
        在指定编号屏幕内模板匹配

        :param screen_index: 屏幕编号（从1开始）
        :param template_path: 模板图片文件路径
        :param threshold: 匹配分数阈值（默认0.8）
        :param return_screen_coords: True 返回真实屏幕坐标，False 返回截图图坐标
        :param save_path: 如果不为 None，将保存带标注矩形和分数的截图到该路径
        :return: [(center_x, center_y, score), ...] 匹配结果列表
        """
        import cv2
        tmpl = cv2.imread(template_path)
        if tmpl is None:
            raise ValueError(f"无法读取模板图片: {template_path}")

        # 截取指定屏幕
        screen_img = self.capture_fullscreen(screen_index=screen_index, as_cv2=True)
        if screen_img is None:
            raise RuntimeError(f"无法截取屏幕 {screen_index}")

        # 模板匹配
        result = cv2.matchTemplate(screen_img, tmpl, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)

        h, w = tmpl.shape[:2]
        matches = []
        boxes = []
        scores = []

        for pt_y, pt_x in zip(*locations):
            boxes.append([pt_x, pt_y, pt_x + w, pt_y + h])
            scores.append(float(result[pt_y, pt_x]))

        boxes = np.array(boxes)
        scores = np.array(scores)

        if len(boxes) > 0:
            # NMS去重
            keep = self._nms(boxes, scores, 0.5)
            boxes = boxes[keep]
            scores = scores[keep]

            for (x1, y1, x2, y2), score in zip(boxes, scores):
                center_x = x1 + w // 2
                center_y = y1 + h // 2

                if return_screen_coords:
                    # 获取屏幕实际坐标偏移
                    monitors = self.sct.monitors[1:]
                    if screen_index < 1 or screen_index > len(monitors):
                        raise ValueError(f"无效的屏幕索引: {screen_index}")
                    mon = monitors[screen_index - 1]
                    real_x = center_x + mon["left"]
                    real_y = center_y + mon["top"]
                    matches.append((real_x, real_y, score))
                else:
                    matches.append((center_x, center_y, score))

        # 保存标注图
        if save_path and len(boxes) > 0:
            annotated_img = screen_img.copy()
            for (x1, y1, x2, y2), score in zip(boxes, scores):
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 0, 255), 2, cv2.LINE_AA)
                cv2.putText(annotated_img, f"{score:.2f}", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA)
            cv2.imwrite(save_path, annotated_img)

        return matches

