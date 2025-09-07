"""
指令映射模块
"""
from core.commands.flow_commands import *
from core.commands.script_commands import *
from core.commands.subtask_command import *
from core.commands.trigger_commands import *

COMMAND_MAP = {
    "trigger": {
        "processTrigger": ProcessTriggerCmd,
        "networkTrigger": NetworkConnectionTriggerCmd,
        "timeTrigger": DateTimeTriggerCmd
    },
    "mouse": {
        "pressRelease": MousePressReleaseCmd,
        "click": MouseClickCmd,
        "moveTo": MouseMoveToCmd,
        "moveRel": MouseMoveRelCmd,
        "dragTo": MouseDragToCmd,
        "dragRel": MouseDragRelCmd,
        "scrollV": MouseScrollCmd,
        "scrollH": MouseScrollHCmd
    },
    "keyboard": {
        "keyPress": KeyPressCmd,
        "keyRelease": KeyReleaseCmd,
        "keyTap": KeyTapCmd,
        "hotkey": HotKeyCmd,
        "keyType": KeyTypeTextCmd
    },
    "image": {
        "imageMatch": ImageMatchCmd,
        "imageClick": ImageClickCmd,
        "imageOcr": ImageOcrCmd,  # 文字识别类，需要提前加载模型
        "imageOcrClick": ImageOcrClickCmd  # 文字识别类，需要提前加载模型
    },
    "flow": {
        "delay": DelayCmd,
        "if": IfCommand,
        "loop": LoopCommand
    },
    "script": {
        "dos": ExecuteDosCmd,
        "python": ExecutePyCmd,
    },
    "subtask": {
        "runSubtask": SubtaskCommand
    },
}