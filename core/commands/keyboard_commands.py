"""
@author: 54Coconi
@date: 2024-11-13
@version: 1.0.0
@path: /core/commands/keyboard_commands.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    - 键盘控制模块
    - 包括键盘按下、键盘释放、键盘按下并释放、键盘热键组合、键盘输入字符串，支持 pyautogui 和 pynput
"""
import time

import pyautogui

from pynput.keyboard import Controller as KeyboardController, Key, KeyCode
from pydantic import Field

from utils.debug import print_func_time
from .base_command import RetryCmd, CommandRunningException

_DEBUG = False

PYNPUT_SPECIAL_KEY_MAP = {
    'esc',
    'tab',
    'caps_lock',
    'shift',
    'shift_r',
    'ctrl',
    'ctrl_l',
    'ctrl_r',
    'f1',
    'f2',
    'f3',
    'f4',
    'f5',
    'f6',
    'f7',
    'f8',
    'f9',
    'f10',
    'f11',
    'f12',
    'f13',
    'f14',
    'f15',
    'f16',
    'f17',
    'f18',
    'f19',
    'f20',
    'f21',
    'f22',
    'f23',
    'f24',
    'backspace',
    'home',
    'end',
    'page_up',
    'page_down',
    'num_lock',
    'up',
    'down',
    'left',
    'right',
    'insert',
    'alt_l',
    'alt_r',
    'media_volume_up',
    'media_volume_down',
    'media_volume_mute',
    'media_previous',
    'media_play_pause',
    'cmd',
    'cmd_r',
    'print_screen',
    'alt',
    'alt_gr',
    'delete',
    'enter',
    'scroll_lock',
    'pause',
    'space',
    'media_next',
    'menu',
}


def is_pynput_key_supported(key: str) -> bool:
    """
    判断给定的按键是否在 pynput 支持的按键集合中，忽略大小写。
    :param key: 要检查的按键字符串
    :return: 如果支持，返回 True；否则返回 False
    """
    # 将 key 转换为小写，以忽略大小写
    key = key.lower()

    # pynput 支持的特殊按键集合，转换为小写名称
    pynput_special_keys = {k.name.lower() for k in Key}

    # pynput 支持的普通按键（字母、数字等），转换为小写
    pynput_standard_keys = {chr(i).lower() for i in range(32, 127)}  # ASCII 可打印字符
    pynput_standard_keys.update({str(i) for i in range(10)})  # 数字键 "0" - "9"

    # 将特殊按键和标准按键组合成支持的按键集合
    supported_keys = pynput_special_keys | pynput_standard_keys
    # print(sorted(supported_keys) if _DEBUG else "")
    return key in supported_keys


def is_pyautogui_key_supported(key: str) -> bool:
    """
    判断给定的按键是否在 pyautogui 支持的按键集合中，忽略大小写。

    :param key: 要检查的按键字符串
    :return: 如果支持，返回 True；否则返回 False
    """
    # 将 key 转换为小写，以忽略大小写
    key = key.lower()

    # 将 pyautogui 支持的按键集合也转换为小写
    pyautogui_keys = {k.lower() for k in pyautogui.KEYBOARD_KEYS}

    return key in pyautogui_keys


def get_pynput_key(key: str) -> Key | KeyCode | None:
    """
    根据用户输入的按键字符串获取 `pynput` 对应的按键对象。

    :param key: 用户输入的按键字符串
    :return: 如果是普通字符，返回 :class:`KeyCode`；如果是特殊按键，返回 :class:`Key` 对象；如果不支持，则返回 None
    """
    # 如果按键是一个字符，直接返回 KeyCode
    if len(key) == 1:
        return KeyCode.from_char(key)

    # 如果按键字符串长度不为 1，尝试在 Key 中查找特殊按键
    try:
        return getattr(Key, key.lower())
    except AttributeError:
        print(f"[WARN] - 按键 '{key}' 不在 pynput 支持的特殊按键列表中")
        return None


# 转换 Windows 键、 Command 键、 Super 键为 pynput 支持的按键 Key.cmd
def get_pynput_cmd_key(key: str) -> str | None:
    """
    将 Windows 键、 Command 键、 Super 键转换为 cmd 键
    :param key: 要转换的按键
    :return: Key.cmd
    """
    if key.lower() in ["win", "window", "windows", "command", "super"]:
        return "cmd"


# @ <键盘按下按键> 指令
class KeyPressCmd(RetryCmd):
    """
    :class:`KeyPressCmd` 用于模拟按下单个按键，支持 `pyautogui` 和 `pynput`

    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        key:(str): 要按下的按键
        use_pynput:(bool) = 是否使用 pynput 库

    Note:
        - 在使用 `pynput` 库时,在 PC 平台上,cmd 键对应于 Super 键或 Windows 键,在 Mac 上,它对应于 Command 键
    """
    name: str = Field(f"<键盘按下按键>", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    key: str = Field(..., description="要按下的按键")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    @print_func_time(_DEBUG)
    def run_command(self, **kwargs):
        """ 执行按下按键的操作 """
        try:
            if self.use_pynput:
                if key := get_pynput_cmd_key(self.key):
                    self.key = key
                if not is_pynput_key_supported(self.key):
                    raise ValueError(f"[pynput] 不支持的按键 '{self.key}' ")
                keyboard = KeyboardController()
                keyboard.press(get_pynput_key(self.key))
                print(f"[INFO] - (KeyPressCmd)[pynput] 按下按键 '{self.key}' ")
            else:
                if not is_pyautogui_key_supported(self.key):
                    raise ValueError(f"[pyautogui] 不支持的按键 '{self.key}' ")
                pyautogui.keyDown(self.key)
                print(f"[INFO] - (KeyPressCmd)[pyautogui] 按下按键 '{self.key}' ")
        except Exception as e:
            raise CommandRunningException(e)


# @ <键盘释放按键> 指令
class KeyReleaseCmd(RetryCmd):
    """
    :class:`KeyReleaseCmd` 用于模拟释放单个按键，支持 `pyautogui` 和 `pynput`
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        key:(str): 要释放的按键
        use_pynput:(bool): 是否使用 pynput 库

    Note:
        - 在使用 `pynput` 库时,在 PC 平台上,cmd 键对应于 Super 键或 Windows 键,在 Mac 上,它对应于 Command 键
    """
    name: str = Field(f"键盘释放按键", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    key: str = Field(..., description="要释放的按键")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    def run_command(self, **kwargs):
        """ 执行按下按键的操作 """
        try:
            if self.use_pynput:
                if key := get_pynput_cmd_key(self.key):
                    self.key = key
                if not is_pynput_key_supported(self.key):
                    raise ValueError(f"[pynput] 不支持的按键 '{self.key}' ")
                keyboard = KeyboardController()
                keyboard.release(get_pynput_key(self.key))
                print(f"[INFO] - (KeyReleaseCmd)[pynput] 释放按键 '{self.key}' ")
            else:
                if not is_pyautogui_key_supported(self.key):
                    raise ValueError(f"[pyautogui] 不支持的按键 '{self.key}' ")
                pyautogui.keyUp(self.key)
                print(f"[INFO] - (KeyReleaseCmd)[pyautogui] 释放按键 '{self.key}' ")
        except Exception as e:
            raise CommandRunningException(e)


# @ <键盘按下并释放按键> 指令
class KeyTapCmd(RetryCmd):
    """
    :class:`KeyTapCmd` 用于模拟按下并释放单个按键，支持 `pyautogui` 和 `pynput`
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        key:(str): 要按下并释放的按键
        use_pynput:(bool): 是否使用 pynput 库

    Note:
        - 在使用 `pynput` 库时,在 PC 平台上,cmd 键对应于 Super 键或 Windows 键,在 Mac 上,它对应于 Command 键
    """
    name: str = Field("键盘按下并释放按键", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    key: str = Field(..., description="要按下并释放的按键")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    def run_command(self, **kwargs):
        """ 执行按下按键的操作 """
        try:
            if self.use_pynput:
                if key := get_pynput_cmd_key(self.key):
                    self.key = key
                if not is_pynput_key_supported(self.key):
                    raise ValueError(f"[pynput] 不支持的按键 '{self.key}' ")
                keyboard = KeyboardController()
                keyboard.tap(get_pynput_key(self.key))
                print(f"[INFO] - (KeyTapCmd)[pynput] 按下按键 '{self.key}' ")
            else:
                if not is_pyautogui_key_supported(self.key):
                    raise ValueError(f"[pyautogui] 不支持的按键 '{self.key}' ")
                pyautogui.press(self.key)
                print(f"[INFO] - (KeyTapCmd)[pyautogui] 按下按键 '{self.key}' ")
        except Exception as e:
            raise CommandRunningException(e)


# @ <键盘热键组合> 指令
class HotKeyCmd(RetryCmd):
    """
    HotKeyCmd 用于模拟按下组合热键，支持 `pyautogui` 和 `pynput`

    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        keys:(list): 热键组合 (如 ['ctrl', 'c'])
        hold_time:(float): 热键保持按住持续时间，单位为秒
        use_pynput:(bool): 是否使用 pynput 库

    Note:
        - 在使用 `pynput` 库时,在 PC 平台上,cmd 键对应于 Super 键或 Windows 键,在 Mac 上,它对应于 Command 键
        hold_time 参数尽量设置为 0
        """
    name: str = Field("键盘热键组合", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    keys: list = Field([], description="热键组合 (如 ['ctrl', 'c'])")
    hold_time: float | int = Field(0.0, description="热键保持按住持续时间，单位为秒")
    use_pynput: bool = Field(False, description="是否使用 pynput 库")

    def run_command(self, **kwargs):
        """ 执行组合热键的操作 """
        if len(self.keys) == 0:
            return
        try:
            if self.use_pynput:
                for i, key in enumerate(self.keys):
                    if _key := get_pynput_cmd_key(key):
                        self.keys[i] = _key
                        key = _key
                    if not is_pynput_key_supported(key):
                        raise ValueError(f"[pynput] 不支持的按键 '{key}' ")
                keyboard = KeyboardController()
                # 顺序按下组合键
                for key in self.keys:
                    print(f"**** 转换成 pynput 按键:{get_pynput_key(key.lower()) if _DEBUG else ''} ****", )
                    # TODO: 这里的 `key` 必须是小写形式，否则热键执行失败，下面逆序释放同理
                    keyboard.press(get_pynput_key(key.lower()))
                time.sleep(self.hold_time)  # 热键保持按住持续时间
                # 逆序释放组合键
                for key in reversed(self.keys):
                    keyboard.release(get_pynput_key(key.lower()))
                print(f"[INFO] - (HotKeyCmd)[pynput] 按下组合热键 {self.keys} ")
            else:
                for key in self.keys:
                    if not is_pyautogui_key_supported(key):
                        raise ValueError(f"[pyautogui] 不支持的按键 '{key}' ")
                pyautogui.hotkey([key.lower() for key in self.keys])
                print(f"[INFO] - (HotKeyCmd)[pyautogui] 按下组合热键 {self.keys} ")
        except Exception as e:
            raise CommandRunningException(e)


# @ <键盘输入字符串> 指令
class KeyTypeTextCmd(RetryCmd):
    """
    键盘输入字符串指令，支持 `pyautogui` 和 `pynput`
    Attributes:
        name:(str): 指令名称
        is_active:(bool): 指令是否生效
        retries:(int): 指令重复执行次数

        text_str:(str): 要输入的字符串内容，默认支持ASCII字符
        interval:(float|int): 输入每个字符之间的时间间隔
        use_pynput:(bool): 是否使用 pynput 库 (默认使用 pynput 库,支持中文、全角字符)

    Note:
        - 在使用 `pynput` 库时,在 PC 平台上,cmd 键对应于 Super 键或 Windows 键,在 Mac 上,它对应于 Command 键
     """
    name: str = Field("键盘输入字符串", description="指令名称")
    is_active: bool = Field(True, description="指令是否生效")
    retries: int = Field(0, description="指令重复执行次数")

    text_str: str = Field(..., description="要输入的字符串内容，默认支持ASCII字符")
    interval: float | int = Field(0.0, description="输入每个字符之间的时间间隔")
    use_pynput: bool = Field(True, description="是否使用 pynput 库,默认使用 pynput 库,支持输入中文、全角字符")

    def run_command(self, **kwargs):
        """ 执行键盘输入字符串的操作 """
        try:
            # 使用 pynput 库
            if self.use_pynput:
                keyboard = KeyboardController()
                for i, char in enumerate(self.text_str, start=1):
                    keyboard.press(char)
                    keyboard.release(char)
                    if i < len(self.text_str):  # 避免键入最后一个字符后仍间隔时间
                        time.sleep(self.interval)
                print(f"[INFO] - (KeyTypeTextCmd)[pynput] 输入字符串 '{self.text_str}' ")
            # 使用 pyautogui 库
            else:
                pyautogui.typewrite(self.text_str, interval=self.interval)
                print(f"[INFO] - (KeyTypeTextCmd)[pyautogui] 输入字符串 '{self.text_str}' ")
        except Exception as e:
            raise CommandRunningException(e)
