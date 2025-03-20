"""
使用 pynput 进行鼠标移动

"""
import time
from typing import Tuple

from pynput.mouse import Controller


_DEBUG = False


# 绘图时建议采用该方法，保证鼠标不会跳跃, 但是速度较慢会有一定误差不能在指定 duration 内到达目标位置
def move_with_duration_pynput(duration: float | int, position: Tuple[int, int], mouse: Controller):
    """
    使用 pynput 缓慢移动鼠标到目标位置，受 duration 控制
    :param duration: (float|int): 移动持续时间(秒)
    :param position: (Tuple[int, int]): 移动目标位置 (x, y)
    :param mouse: (Controller): pynput 鼠标控制器

    Note:
        - 绘图时建议采用该方法，保证鼠标不会跳跃, 但是速度较慢会有一定误差不能在指定 duration 内到达目标位置
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


# 对于时间敏感的操作，建议使用该方法，保证在指定 duration 时间内到达目标位置
def move_with_duration_pynput_dynamic(duration: float | int, position: Tuple[int, int], mouse: Controller):
    """
    使用 pynput 缓慢移动鼠标到目标位置，受 duration 控制，使用动态时间调整以减少误差
    :param duration: (float|int): 移动持续时间(秒)
    :param position: (Tuple[int, int]): 移动目标位置 (x, y)
    :param mouse: (Controller): pynput 鼠标控制器

    Note:
        - 对于时间敏感的操作，建议使用该方法，保证在指定 duration 时间内到达目标位置
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
