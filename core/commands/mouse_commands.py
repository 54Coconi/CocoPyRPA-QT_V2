"""
@author: 54Coconi
@date: 2024-11-11
@version: 1.0.0
@path: /core/commands/mouse_commands.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    - 鼠标操作指令模块
    - 包括鼠标点击, 鼠标定点移动, 鼠标相对移动, 鼠标定点拖动, 鼠标相对拖动, 鼠标滚轮滚动, 支持 pyautogui 和 pynput
"""

import time
import pyautogui

from typing import Tuple
from pydantic import Field
from pynput.mouse import Controller, Button
from pytweening import linear, easeInQuad, easeInOutQuad, easeOutQuad

from utils.debug import print_func_time

from .base_command import RetryCmd, CommandRunningException

_DEBUG = False

# 二次补间函数[线性补间函数; 开始时缓慢然后加速; 加速到达中点然后减速; 开始时加速然后减速]
TweenFuncs = [linear, easeInQuad, easeInOutQuad, easeOutQuad]

# 设置 pyautogui 的失败安全模式，当鼠标移动到屏幕边缘时触发错误
pyautogui.FAILSAFE = True

# 获取当前屏幕分辨率
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
# 设置 pynput 鼠标按键映射
PYNPUT_BUTTON = {
    'left': Button.left,
    'right': Button.right,
    'middle': Button.middle
}


# 绘图时建议采用该方法，保证鼠标不会跳跃
def move_with_duration_pynput(duration: float | int, position: Tuple[int, int], mouse: Controller):
    """
    使用 pynput 缓慢移动鼠标到目标位置，受 duration 控制。
    """
    start_pos = mouse.position  # 记录初始位置
    steps = int(duration * 40)  # 分为 100 * duration 个小步
    interval = duration / steps  # 每一步的时间间隔

    for step in range(steps):
        # 计算每一步的位置，避免累积误差
        new_x = start_pos[0] + (position[0] - start_pos[0]) * (step + 1) / steps
        new_y = start_pos[1] + (position[1] - start_pos[1]) * (step + 1) / steps
        mouse.position = (int(new_x), int(new_y))  # 移动鼠标到当前步的目标位置
        time.sleep(interval)

    # 确保最终位置精确到达目标位置
    mouse.position = position


# 对于时间敏感的操作，建议使用该方法，保证在最短时间内到达目标位置
@print_func_time(debug=_DEBUG)
def move_with_duration_pynput_dynamic(duration: float | int, position: Tuple[int, int], mouse: Controller):
    """
    使用 pynput 缓慢移动鼠标到目标位置，受 duration 控制
    使用动态时间调整以减少误差
    :param duration: (float|int): 移动持续时间(秒)
    :param position: (Tuple[int, int]): 移动目标位置 (x, y)
    :param mouse: (Controller): pynput 鼠标控制器
    """
    start_pos = mouse.position  # 记录初始位置
    steps = int(duration * 50)  # 使用更高的步数来减少时间片误差
    interval = duration / steps  # 每一步的目标间隔时间
    target_time = time.time() + duration  # 记录目标结束时间
    print(f"steps: {steps}, interval: {interval}" if _DEBUG else "", end="")

    # 逐步移动鼠标位置
    for step in range(steps):
        # 计算当前步的目标位置, 避免累积误差
        new_x = start_pos[0] + (position[0] - start_pos[0]) * (step + 1) / steps
        new_y = start_pos[1] + (position[1] - start_pos[1]) * (step + 1) / steps
        mouse.position = (int(new_x), int(new_y))  # 移动鼠标到当前步的目标位置

        # 动态调整休眠时间，基于当前时间和目标时间的差值
        remaining_time = target_time - time.time()
        if remaining_time <= interval * 0.1:
            break  # 如果已到达目标时间，直接结束
        # 使用动态时间调整，避免时间片误差
        sleep_time = min(interval, remaining_time / (steps - step))
        # if sleep_time <= interval * 0.1:
        #     break
        time.sleep(sleep_time)

    # 最终确保到达目标位置
    mouse.position = position


@print_func_time(debug=_DEBUG)
def click_pynput(clicks, button, interval,
                 mouse: Controller, target_pos: Tuple[int, int] = None):
    """ 使用 pynput 进行点击操作 """
    mouse.position = target_pos
    for _ in range(clicks):
        # 点击操作，默认为左键
        mouse.click(PYNPUT_BUTTON.get(button, Button.left))
        if _ + 1 < clicks:  # 当执行最后一次点击时，不用延时
            time.sleep(float(interval))


def _is_within_screen_bounds(x: int, y: int) -> bool:
    """
    检查坐标 (x, y) 是否在当前屏幕的分辨率范围内
    :param x: (int): 要检查的 x 坐标
    :param y: (int): 要检查的 y 坐标
    :return: (bool): 坐标是否在屏幕范围内
    """
    # 判断坐标是否在屏幕范围内
    if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
        return True
    else:
        return False


# @ <鼠标点击> 指令
class MouseClickCmd(RetryCmd):
    """
    <鼠标点击> 指令
    用于模拟鼠标点击，支持 pyautogui 和 pynput,
    如果指定了 x 和 y 坐标，且点击位置不同于当前鼠标位置，则 duration 参数用于控制移动到目标位置的持续时间
    Attributes:
        name:(str): 指令名称, 默认为 "<鼠标点击>"
        is_active:(bool): 指令是否生效, 默认为 True
        retries:(int): 指令重复执行次数, 默认为 0

        target_pos:(tuple): 需要点击的目标位置(x, y)
        clicks:(int): 点击次数, 默认为1
        interval:(float|int): 点击间隔(秒), 默认为0.2s
        button:(str): 鼠标按键类型('left', 'right', 'middle'), 默认为 'left'
        duration:(float|int): 移动持续时间(秒), 默认为0
        use_pynput:(bool): 是否使用 pynput 库, 默认为 False
    """
    name: str = Field(f"鼠标点击", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    target_pos: Tuple[int, int] = Field(..., description="点击位置 (x, y)")
    clicks: int = Field(1, description="点击次数")
    interval: float | int = Field(0.2, description="点击间隔 (秒)")
    button: str = Field('left', description="鼠标按键类型 ('left', 'right', 'middle')")
    duration: float | int = Field(0, description="移动持续时间 (秒)")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        """ 执行鼠标点击操作，支持 pyautogui 和 pynput 两种库 """
        _msg = ["[INFO] - (MouseClickCmd)", f"成功'{self.button}'键点击坐标 {self.target_pos} {self.clicks} 次"]
        _error = f"鼠标点击的目标位置 {self.target_pos} 不在屏幕分辨率 {SCREEN_WIDTH}x{SCREEN_HEIGHT} 以内"
        try:
            if not _is_within_screen_bounds(self.target_pos[0], self.target_pos[1]):
                raise CommandRunningException(_error)
            # 使用 pynput 进行移动和点击操作
            if self.use_pynput:
                mouse = Controller()
                current_position = mouse.position  # 获取当前鼠标位置
                if current_position != self.target_pos and self.duration > 0:
                    move_with_duration_pynput(self.duration, self.target_pos, mouse)  # 移动到目标位置
                click_pynput(self.clicks, self.button, self.interval, mouse, self.target_pos)  # 点击
                print(_msg[0] + "[pynput] " + _msg[1])
            # 使用 pyautogui 库进行点击操作
            else:
                if pyautogui.position() == self.target_pos and self.duration > 0:
                    self.duration = 0  # 如果目标位置与当前位置相同，则不需要移动
                pyautogui.click(
                    x=self.target_pos[0],
                    y=self.target_pos[1],
                    clicks=self.clicks,
                    interval=self.interval,
                    button=self.button,
                    duration=self.duration,
                    tween=TweenFuncs[0]
                )
                print(_msg[0] + "[pyautogui] " + _msg[1])
        except Exception as e:
            raise CommandRunningException(e)

    @print_func_time(debug=_DEBUG)
    def _click_pynput(self, mouse: Controller):
        """ 使用 pynput 进行点击操作 """
        # mouse.position = self.target_pos
        for _ in range(self.clicks):
            # 点击操作，默认为左键
            mouse.click(PYNPUT_BUTTON.get(self.button, Button.left))
            if _ + 1 < self.clicks:  # 当执行最后一次点击时，不用延时
                time.sleep(float(self.interval))


# @ <鼠标定点移动> 指令
class MouseMoveToCmd(RetryCmd):
    """
    <鼠标定点移动> 指令
    支持 pyautogui 和 pynput
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        target_pos:(Tuple[int, int]): 鼠标定点移动目标位置 (x, y)
        duration:(float|int): 移动持续时间(秒)
        use_pynput:(bool): 是否使用 pynput 库
    """
    name: str = Field("鼠标定点移动", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    target_pos: Tuple[int, int] = Field(..., description="鼠标定点移动目标位置 (x, y)")
    duration: float | int = Field(0, description="移动持续时间 (秒)")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        # 判断目标位置是否在屏幕分辨率内
        if not _is_within_screen_bounds(self.target_pos[0], self.target_pos[1]):
            _error = f"定点移动目标位置 {self.target_pos} 不在屏幕分辨率 {SCREEN_WIDTH}x{SCREEN_HEIGHT} 内"
            raise CommandRunningException(_error)
        # 执行移动操作
        try:
            if self.use_pynput:
                # 使用 pynput 进行移动操作
                mouse = Controller()
                if self.duration > 0:
                    move_with_duration_pynput(self.duration, self.target_pos, mouse)  # 移动到目标位置
                else:
                    mouse.position = self.target_pos
                print(f"[INFO] - (MouseMoveCmd)[pynput] 成功定点移动到坐标:{self.target_pos}")
            else:
                # 使用 pyautogui 进行移动操作
                pyautogui.moveTo(self.target_pos[0], self.target_pos[1],
                                 duration=self.duration,
                                 tween=TweenFuncs[0]  # 二次补间函数(当duration不为0时使用）默认为线性
                                 )
                print(f"[INFO] - (MouseMoveCmd)[pyautogui] 成功定点移动到坐标:{self.target_pos}")
        except Exception as e:
            raise CommandRunningException(e)


# @ <鼠标相对移动>指令
class MouseMoveRelCmd(RetryCmd):
    """
    <鼠标相对移动>指令 支持 pyautogui 和 pynput
    用于将鼠标相对当前位置移动指定距离
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        offset:(Tuple[int, int]): 相对偏移量 (dx, dy)
        duration:(float|int): 移动持续时间(秒)
        use_pynput:(bool): 是否使用 pynput 库
    """
    name: str = Field("鼠标相对移动", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    offset: Tuple[int, int] = Field(..., description="相对偏移量 (dx, dy)")
    duration: float | int = Field(0, description="移动持续时间 (秒)")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        """
        执行鼠标相对移动操作，支持 pyautogui 和 pynput
        """
        try:
            dx, dy = self.offset
            mouse = Controller()
            start_pos = mouse.position  # 获取当前鼠标位置
            target_pos = (start_pos[0] + dx, start_pos[1] + dy)  # 根据当前位置计算目标位置
            if not _is_within_screen_bounds(target_pos[0], target_pos[1]):
                _error = f"相对位置 {target_pos} 不在屏幕分辨率 {SCREEN_WIDTH}x{SCREEN_HEIGHT} 内"
                raise CommandRunningException(_error)
            # 执行移动操作
            if self.use_pynput:
                # 使用 pynput 进行相对移动
                if self.duration > 0:
                    move_with_duration_pynput(self.duration, target_pos, mouse)  # 移动到目标位置
                else:
                    mouse.move(dx, dy)
                print(f"[INFO] - (MouseMoveRelCmd)[pynput] 成功相对移动 {self.offset} 到 {target_pos}")
            else:
                # 使用 pyautogui 进行相对移动
                pyautogui.moveRel(dx, dy, duration=self.duration, tween=TweenFuncs[0])
                print(f"[INFO] - (MouseMoveRelCmd)[pyautogui] 成功相对移动 {self.offset} 到 {target_pos}")
        except Exception as e:
            raise CommandRunningException(f"{e}")


# @ <鼠标定点拖动> 指令
class MouseDragToCmd(RetryCmd):
    """
    <鼠标定点拖动> 指令 支持 pyautogui 和 pynput
    用于将鼠标从当前位置拖动到目标位置
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        target_pos:(Tuple[int, int]): 拖动目标位置 (x, y)
        duration:(float|int): 拖动的持续时间 (秒)，默认 1s
        button:(str): 拖动的鼠标按键类型 ('left', 'right')
        use_pynput:(bool): 是否使用 pynput 库
    """
    name: str = Field("鼠标定点拖动", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    target_pos: Tuple[int, int] = Field(..., description="拖动目标位置 (x, y)")
    duration: float = Field(1, description="拖动的持续时间 (秒)，默认 1s")
    button: str = Field('left', description="拖动的鼠标按键类型 ('left', 'right', 'middle')")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        """ 执行鼠标拖动操作，支持 pyautogui 和 pynput """
        try:
            if not _is_within_screen_bounds(self.target_pos[0], self.target_pos[1]):
                _error = f"定点拖动目标位置 {self.target_pos} 不在屏幕分辨率 {SCREEN_WIDTH}x{SCREEN_HEIGHT} 内"
                raise CommandRunningException(_error)
            if self.use_pynput:
                # 使用 pynput 进行拖动操作
                mouse = Controller()
                __button = PYNPUT_BUTTON.get(self.button, Button.left)  # 获取鼠标按键,默认为左键
                # 按下鼠标按钮
                mouse.press(__button)
                # 开始移动
                if self.duration > 0:
                    move_with_duration_pynput(self.duration, self.target_pos, mouse)
                else:
                    mouse.position = self.target_pos
                # 释放鼠标按钮
                mouse.release(__button)
                print(f"[INFO] - (MouseDragToCmd)[pynput] 鼠标成功定点拖动到 {self.target_pos}")
            else:
                # 使用 pyautogui 进行拖动操作
                pyautogui.dragTo(self.target_pos, duration=self.duration, button=self.button, tween=TweenFuncs[0])
                print(f"[INFO] - (MouseDragToCmd)[pyautogui] 鼠标成功定点拖动到 {self.target_pos}")
        except Exception as e:
            raise CommandRunningException(e)


# @ <鼠标相对拖动> 指令
class MouseDragRelCmd(RetryCmd):
    """
    <鼠标相对拖动> 指令 支持 pyautogui 和 pynput
    用于将鼠标从当前位置相对拖动指定距离
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        offset:(Tuple[int, int]): 相对偏移量 (dx, dy)
        duration:(float|int): 拖动的持续时间 (秒)，默认 1s
        button:(str): 拖动的鼠标按键类型 ('left', 'right')
        use_pynput:(bool): 是否使用 pynput 库
    """
    name: str = Field("鼠标相对拖动", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    offset: Tuple[int, int] = Field(..., description="相对偏移量 (dx, dy)")
    duration: float = Field(1, description="拖动的持续时间 (秒)，默认 1s")
    button: str = Field('left', description="拖动的鼠标按键类型 ('left', 'right', 'middle')")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        """ 执行鼠标相对拖动操作，支持 pyautogui 和 pynput """
        try:
            dx, dy = self.offset
            mouse = Controller()
            current_pos = mouse.position  # 获取当前鼠标位置
            target_pos = (current_pos[0] + dx, current_pos[1] + dy)  # 根据当前位置计算目标位置
            if not _is_within_screen_bounds(target_pos[0], target_pos[1]):
                _error = f"相对拖动目标位置 {target_pos} 不在屏幕分辨率 {SCREEN_WIDTH}x{SCREEN_HEIGHT} 内"
                raise CommandRunningException(_error)
            if self.use_pynput:
                # 使用 pynput 进行相对拖动操作
                __button = PYNPUT_BUTTON.get(self.button, Button.left)  # 获取鼠标按键,默认为左键
                # 按下鼠标按钮
                mouse.press(__button)
                # 开始移动
                if self.duration > 0:
                    move_with_duration_pynput(self.duration, target_pos, mouse)
                else:
                    mouse.move(dx, dy)
                # 释放鼠标按钮
                mouse.release(__button)
                print(f"[INFO] - (MouseDragRelCmd)[pynput] 鼠标成功相对拖动 {self.offset} 到 {target_pos}")
            else:
                # 使用 pyautogui 进行相对拖动操作
                pyautogui.dragRel(dx, dy, duration=self.duration, button=self.button, tween=TweenFuncs[0])
                print(f"[INFO] - (MouseDragRelCmd)[pyautogui] 鼠标成功相对拖动 {self.offset} 到 {target_pos}")
        except Exception as e:
            raise CommandRunningException(e)


# @ <鼠标竖直滚动> 指令
class MouseScrollCmd(RetryCmd):
    """
    <鼠标竖直滚动> 指令 支持 pyautogui 和 pynput
    用于模拟鼠标滚轮滚动

    Note：
        使用 pynput 时，滚动的单位为 1 个滚动单位,根据不同的操作系统
        和鼠标滚轮的不同，滚动的单位长度可能会有所不一样，而使用 pyautogui 时，
        滚动的单位为屏幕像素，根据分辨率的不同和鼠标滚动的速度，滚动的单位长度也会有所不一样
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        scroll_units:(int): 滚动的单位数量 (正数表示向上，负数表示向下)
        use_pynput:(bool): 是否使用 pynput 库
    """
    name: str = Field("鼠标竖直滚动", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    scroll_direction: str = Field("scrollV", description="滚动方向")
    scroll_units: int = Field(..., description="滚动的单位数量 (正数表示向上，负数表示向下)")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        """ 执行鼠标滚轮滚动操作，支持 pyautogui 和 pynput """
        try:
            if self.use_pynput:
                # 使用 pynput 进行滚轮滚动
                mouse = Controller()
                # 每次滚动的最小单位和滚动方向
                step = (1 if self.scroll_units > 0 else -1)
                # 一共滚动 self.scroll_units 次
                for _ in range(abs(self.scroll_units)):
                    if self.scroll_direction == "scrollV":
                        mouse.scroll(0, step)
                    elif self.scroll_direction == "scrollH":
                        mouse.scroll(step, 0)
                    else:
                        raise CommandRunningException(f"滚动方向 {self.scroll_direction} 不支持")
                    time.sleep(0.01)  # 控制滚动速度，避免快速滚动
                print(f"[INFO] - (MouseScrollCmd)[pynput] 成功滚动鼠标 {self.scroll_units} 单位")
            else:
                # 使用 pyautogui 进行滚轮滚动
                pyautogui.scroll(self.scroll_units)
                print(f"[INFO] - (MouseScrollCmd)[pyautogui] 成功滚动鼠标 {self.scroll_units} 单位")
        except Exception as e:
            raise CommandRunningException(e)


# @ <鼠标横向滚动> 指令
class MouseScrollHCmd(MouseScrollCmd):
    """  <鼠标横向滚动> 指令

    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        scroll_units:(int): 滚动的单位数量 (正数表示向右，负数表示向左)
        use_pynput:(bool): 是否使用 pynput 库
    """
    name: str = Field("鼠标横向滚动", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    scroll_direction: str = Field("scrollH", description="滚动方向")
    scroll_units: int = Field(..., description="滚动的单位数量 (正数表示向右，负数表示向左)")
    use_pynput: bool = Field(True, description="是否使用 pynput 库")

    @print_func_time(debug=_DEBUG)
    def run_command(self, **kwargs):
        """ 执行鼠标横向滚动操作，支持 pyautogui 和 pynput """
        super().run_command(**kwargs)
