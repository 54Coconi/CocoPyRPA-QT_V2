"""
mouse_recorder.core
核心逻辑模块，将鼠标/键盘监听与 UI 解耦，可被其它程序直接复用

本模块不依赖任何界面组件，仅通过 Qt 信号向外部发布事件，因此可以在 CLI 或 GUI 程序中复用
"""

from __future__ import annotations

import datetime
import time
from typing import List, Tuple, Optional

import keyboard
import mss
import pyautogui
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from pynput import mouse
from screeninfo import get_monitors

# 定义模块的公开接口，当使用 `from module import *` 时，仅导出指定的名称。
__all__ = [
    "MouseRecorderCore",
    "DEFAULT_RECORD_KEY",
    "DEFAULT_EXIT_KEY",
    "ActionType"
]

from config.app_config import error


# 动作类型常量
class ActionType:
    """动作类型常量"""
    MOVE_TO = "moveTo"
    CLICK = "click"
    SCROLL_V = "scrollV"
    DRAG_TO = "dragTo"


# 动作名称映射 (中文 -> 英文)
ACTION_MAPPING = {
    # 移动
    "定点移动": ActionType.MOVE_TO,
    # 点击
    "左键单击": ActionType.CLICK,
    "左键双击": ActionType.CLICK,
    "中键点击": ActionType.CLICK,
    "右键单击": ActionType.CLICK,
    # 滚动
    "竖直滚动": ActionType.SCROLL_V,
    # 拖动
    "左键拖动": ActionType.DRAG_TO
}

# 默认快捷键
DEFAULT_RECORD_KEY = "enter"
DEFAULT_EXIT_KEY = "esc"
# 鼠标移动刷新率
MOUSE_FPS = 30


# --------------------------------------------------------------------------------------
# 工具函数
# --------------------------------------------------------------------------------------

def safe_get_pixel(x: int, y: int) -> Tuple[int, int, int]:
    """尽量使用最轻量的方式获取像素点 RGB 色值。这里使用 `pyautogui.screenshot` 的 1×1 区域截取，
    相比整屏截图会更快一些。若获取失败(例如鼠标位于屏幕之外)则返回 (0,0,0)。"""
    try:
        # 仅截取 (x,y) 处 1×1 的图像，性能远优于整屏截图
        img = pyautogui.screenshot(region=(x, y, 1, 1))
        return img.getpixel((0, 0))
    except Exception:
        return 0, 0, 0


def get_screen_resolution() -> tuple[int, int]:
    """
    获取屏幕分辨率

    :return: 屏幕的宽度和高度
    """
    # 获取当前系统的显示器信息
    monitor = get_monitors()[0]
    # 返回主显示器的宽度和高度
    return monitor.width, monitor.height


def normalize_coordinates(x, y, w, h) -> tuple[int, int]:
    """规范坐标值
    :param x: 横坐标
    :param y: 纵坐标
    :param w: 屏幕宽度
    :param h: 屏幕高度
    """
    return max(0, min(x, w - 1)), max(0, min(y, h - 1))


def get_rgb_at_pos(x, y) -> tuple[int, int, int]:
    """ 获取当前坐标的 RGB 值，每次只获取一个像素，如果获取失败返回 (0,0,0) """
    with mss.mss() as sct:
        monitor = {"top": y, "left": x, "width": 1, "height": 1}
        sct_img = sct.grab(monitor)  # 截图
        return sct_img.pixel(0, 0)


# --------------------------------------------------------------------------------------
# 鼠标监听线程
# --------------------------------------------------------------------------------------

class _MouseListenerThread(QThread):
    """独立线程监听鼠标事件，不直接与界面交互，通过信号向外部发送事件数据"""

    rgb_signal = pyqtSignal(tuple)  # 发射当前像素 RGB 颜色 (r,g,b)
    preview_signal = pyqtSignal(str)  # 发射操作预览文本 (供 UI 实时显示)
    cmd_ready_signal = pyqtSignal(dict)  # 发射解析后的单条指令

    def __init__(self):
        super().__init__()
        self.listener: Optional[mouse.Listener] = None
        # 用于区分单击/双击/拖动
        self._last_click_time: float = 0.0
        self._is_dragging: bool = False
        self._start_pos: Tuple[int, int] | None = None
        # 滚轮累积量，正负表示方向(以 pynput 的 dy 为准)
        self._scroll_acc: int = 0
        self._is_scrolling: bool = False  # 判断是否在滚动
        self._running: bool = True
        # 快速刷新限制: 连续移动事件中过滤掉 10ms 内的高频调用，避免 UI 卡顿
        self._last_move_emit: float = 0.0
        self._screen_width, self._screen_height = get_screen_resolution()

    # ----------------------------------------------------------------------------------
    # QThread API
    # ----------------------------------------------------------------------------------

    def run(self):
        """线程入口：创建并阻塞 mouse.Listener。"""
        self.listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self.listener.start()
        # 阻塞直到 stop() 被调用
        self.listener.join()

    def stop(self):
        """停止鼠标监听"""
        self._running = False
        if self.listener.is_alive():
            self.listener.stop()
        self.quit()

    # ----------------------------------------------------------------------------------
    # 鼠标事件处理
    # ----------------------------------------------------------------------------------

    def _emit_rgb(self, x: int, y: int):
        rgb = get_rgb_at_pos(x, y)
        self.rgb_signal.emit(rgb)

    @staticmethod
    def _format_preview(action: str, current_pos=None, start_pos=None, end_pos=None,
                        duration: float | None = None, scroll_cnt: int | None = None) -> str:
        """按照模板格式化预览文本。"""
        lines = [f"操作类型: {action}"]
        if current_pos is not None:
            lines.append(f"当前坐标: {current_pos}")
        if start_pos is not None:
            lines.append(f"起点坐标: {start_pos}")
        if end_pos is not None and start_pos is not None:
            lines.append(f"终点坐标: {end_pos}")
        if duration is not None:
            lines.append(f"拖动时长: {duration:.2f} s")
        if scroll_cnt is not None:
            direction = "向上" if scroll_cnt > 0 else "向下"
            lines.append(f"滚动次数: {direction} {abs(scroll_cnt)} 次")
        return "\n".join(lines)

    def _emit_preview(self, action: str, **kwargs):
        text = self._format_preview(action, **kwargs)  # 格式化文本
        self.preview_signal.emit(text)

    def _on_move(self, x: int, y: int):
        x, y = normalize_coordinates(x, y, self._screen_width, self._screen_height)
        self._is_scrolling = False
        now = time.time()
        # 限制最快 25FPS 更新，防止过度刷新导致卡顿
        if now - self._last_move_emit < 1 / MOUSE_FPS:  # ~25 次/秒
            return
        self._last_move_emit = now
        self._emit_rgb(x, y)
        cmd = self._make_cmd("定点移动", target_pos=(x, y))
        self.cmd_ready_signal.emit(cmd)
        self._emit_preview("定点移动", current_pos=(x, y))

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        """综合判断单/双击/拖动等操作，生成指令字典。"""
        self._is_scrolling = False
        current_time = time.time()
        if button == mouse.Button.left:
            if pressed:
                # 判断是否双击
                if current_time - self._last_click_time < 0.4:
                    # 左键双击
                    cmd = self._make_cmd("左键双击", target_pos=(x, y))
                    self.cmd_ready_signal.emit(cmd)
                    self._emit_preview("左键双击", current_pos=(x, y))
                    self._is_dragging = False
                    self._start_pos = None
                else:
                    self._start_pos = (x, y)
                    self._is_dragging = True
            else:
                # 左键释放
                if self._is_dragging:
                    duration = current_time - self._last_click_time
                    # 拖动阈值: 时间 >0.2s 且位置变化
                    if duration >= 0.2 and self._start_pos != (x, y):
                        cmd = self._make_cmd("左键拖动", target_pos=(x, y), start_pos=self._start_pos,
                                             duration=duration)
                        self.cmd_ready_signal.emit(cmd)
                        self._emit_preview("左键拖动", current_pos=(x, y), start_pos=self._start_pos, end_pos=(x, y),
                                           duration=duration)
                    else:
                        cmd = self._make_cmd("左键单击", target_pos=(x, y))
                        self.cmd_ready_signal.emit(cmd)
                        self._emit_preview("左键单击", current_pos=(x, y))
                    self._is_dragging = False
                    self._start_pos = None
        elif button == mouse.Button.right and not pressed:
            cmd = self._make_cmd("右键单击", target_pos=(x, y))
            self.cmd_ready_signal.emit(cmd)
            self._emit_preview("右键单击", current_pos=(x, y))
        elif button == mouse.Button.middle and not pressed:
            cmd = self._make_cmd("中键点击", target_pos=(x, y))
            self.cmd_ready_signal.emit(cmd)
            self._emit_preview("中键单击", current_pos=(x, y))
        # 时间戳更新
        self._last_click_time = current_time

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """累积滚轮次数，dy 正负代表方向。每次滚动都实时发射预览，但只在按 Enter 记录时生成完整指令。"""
        if self._is_scrolling:
            self._scroll_acc += dy
        else:
            self._scroll_acc = 0  # 重置
            self._scroll_acc += dy
            self._is_scrolling = True
        # dy 单位为滚动刻度，累计统计
        self._scroll_acc += 0  # 保证类型
        self._emit_preview("竖直滚动", current_pos=(x, y), scroll_cnt=self._scroll_acc)
        # 立即生成指令，方便无 UI 使用者直接获取
        cmd = self._make_cmd("竖直滚动", target_pos=(x, y), scroll=(dx, self._scroll_acc))
        self.cmd_ready_signal.emit(cmd)

    # ----------------------------------------------------------------------------------
    # 指令构造
    # ----------------------------------------------------------------------------------

    @staticmethod
    def _translate_action(action_zh: str) -> str:
        """将中文动作名称转换为英文动作类型"""
        return ACTION_MAPPING.get(action_zh, action_zh)

    def _make_cmd(self, action_zh: str, **kwargs) -> dict:
        """
        创建标准化的指令字典
        :param action_zh: 中文动作名称
        :param kwargs: 其他指令参数
        :return: 包含中英文动作的指令字典
        """
        action_en = self._translate_action(action_zh)
        cmd = {
            "action_zh": action_zh,  # 保留中文动作名称用于显示
            "action": action_en,  # 英文动作名称用于执行
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            **kwargs
        }
        # 如果是点击类操作，添加额外的参数
        if action_en == "click":
            # 判断具体点击类型
            if action_zh == "左键单击":
                cmd["button"] = "left"
                cmd["clicks"] = '1'
            elif action_zh == "左键双击":
                cmd["button"] = "left"
                cmd["clicks"] = '2'
            elif action_zh == "中键点击":
                cmd["button"] = "middle"
                cmd["clicks"] = '1'
            elif action_zh == "右键单击":
                cmd["button"] = "right"
                cmd["clicks"] = '1'
        return cmd


# --------------------------------------------------------------------------------------
# 键盘监听线程
# --------------------------------------------------------------------------------------

class _KeyboardListenerThread(QThread):
    """使用 `keyboard` 库监听 record_key / exit_key
    record_key -> emit enter_pressed
    exit_key -> emit esc_pressed
    """

    enter_pressed = pyqtSignal()
    esc_pressed = pyqtSignal()

    def __init__(self, record_key: str = DEFAULT_RECORD_KEY, exit_key: str = DEFAULT_EXIT_KEY):
        super().__init__()
        self._record_key = record_key.lower()
        self._exit_key = exit_key.lower()

    def run(self):
        """启动线程"""
        keyboard.add_hotkey(self._record_key, lambda: self.enter_pressed.emit())
        # 阻塞等待 exit_key
        keyboard.wait(self._exit_key, suppress=True)
        # 当按下 Esc 时
        self.esc_pressed.emit()

    def stop(self):
        """停止线程"""
        try:
            keyboard.remove_hotkey(self._record_key)
            keyboard.unhook_all()
        except Exception as e:
            error(f"移除热键时出错：{e}")
        self.quit()


# --------------------------------------------------------------------------------------
# 对外主类
# --------------------------------------------------------------------------------------

class MouseRecorderCore(QObject):
    """核心封装类，对外提供统一的 API，屏蔽内部线程细节"""

    rgb_changed = pyqtSignal(tuple)  # (r,g,b)
    preview_changed = pyqtSignal(str)  # 预览文本
    command_created = pyqtSignal(dict)  # 单条指令创建完成
    finished = pyqtSignal()  # 录制结束

    def __init__(self, record_key: str = DEFAULT_RECORD_KEY, exit_key: str = DEFAULT_EXIT_KEY):
        super().__init__()
        self.record_key = record_key
        self.exit_key = exit_key
        self.mouse_thread = _MouseListenerThread()  # 鼠标监听
        self.keyboard_thread = _KeyboardListenerThread(record_key, exit_key)  # 键盘监听
        self.operations: List[dict] = []

        # 线程信号绑定到外部信号
        self.mouse_thread.rgb_signal.connect(self.rgb_changed)
        self.mouse_thread.preview_signal.connect(self.preview_changed)
        self.mouse_thread.cmd_ready_signal.connect(self._on_cmd_created)

        self.keyboard_thread.enter_pressed.connect(self._on_enter)
        self.keyboard_thread.esc_pressed.connect(self.stop_recording)

    # -----------------------------------------------------------------------------
    # 线程控制
    # -----------------------------------------------------------------------------

    def start(self):
        """启动鼠标与键盘监听线程"""
        self.mouse_thread.start()
        self.keyboard_thread.start()

    def stop_recording(self):
        """停止所有线程，并发射 finished 信号"""
        self.mouse_thread.stop()
        self.keyboard_thread.stop()
        self.finished.emit()

    # -----------------------------------------------------------------------------
    # 内部事件处理
    # -----------------------------------------------------------------------------

    def _on_cmd_created(self, cmd: dict):
        """鼠标线程生成的每条指令都会到此，只有当用户按 Enter 时才真正保存"""
        self._latest_cmd = cmd
        # 实时预览也需要通知外部
        # self.command_created.emit(cmd)

    def _on_enter(self):
        """按下 Enter，将当前最新指令写入列表，并发出 command_created 信号。"""
        if hasattr(self, "_latest_cmd"):
            self.operations.append(self._latest_cmd)
            self.command_created.emit(self._latest_cmd)

    # -----------------------------------------------------------------------------
    # 辅助 API
    # -----------------------------------------------------------------------------

    def get_operations(self) -> List[dict]:
        """返回已记录的全部操作列表。"""
        return self.operations.copy()
