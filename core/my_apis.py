"""
@author: 54Coconi
@date: 2024-12-12
@version: 1.0.0
@path: core/my_apis.py
@software: PyCharm 2023.1.2
@officialWebsite: https://github.com/54Coconi
@description:
    - CocoPyRPA_v2.0.0 - 自定义 API
    用于管理 Python 代码执行环境中的自定义类
"""

# 所有自定义类及其属性和方法
CUSTOM_APIS = {
    'MousePressReleaseCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'target_pos', 'press_times', 'hold_time', 'is_release',
                       'button', 'duration', 'use_pynput']
    },
    'MouseClickCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'target_pos', 'clicks', 'interval',
                       'button', 'duration', 'use_pynput']
    },
    'MouseMoveToCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'target_pos', 'duration', 'use_pynput']
    },
    'MouseMoveRelCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'offset', 'duration', 'use_pynput']
    },
    'MouseDragToCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'target_pos', 'button', 'duration', 'use_pynput']
    },
    'MouseDragRelCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'offset', 'button', 'duration', 'use_pynput']
    },
    'MouseScrollCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'scroll_direction', 'scroll_units', 'use_pynput']
    },
    'MouseScrollHCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'scroll_direction', 'scroll_units', 'use_pynput']
    },
    'KeyPressCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries', 'key', 'use_pynput']
    },
    'KeyReleaseCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries', 'key', 'use_pynput']
    },
    'KeyTapCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries', 'key', 'use_pynput']
    },
    'HotKeyCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries', 'keys', 'hold_time', 'use_pynput']
    },
    'KeyTypeTextCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries', 'text_str', 'interval', 'use_pynput']
    },
    'ImageMatchCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'error_retries', 'error_retries_time',
                       'template_img', 'threshold']
    },
    'ImageClickCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'error_retries', 'error_retries_time',
                       'template_img', 'threshold',
                       'clicks', 'interval', 'button', 'duration', 'use_pynput']
    },
    'ImageOcrCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'error_retries', 'error_retries_time',
                       'text', 'match_mode', 'is_ignore_case', 'use_regex', 'threshold']
    },
    'ImageOcrClickCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active', 'retries',
                       'error_retries', 'error_retries_time',
                       'text', 'match_mode', 'is_ignore_case', 'use_regex', 'threshold',
                       'clicks', 'interval', 'button', 'duration', 'use_pynput']
    },
    'ExecuteDosCmd': {
        'type': 'class',
        'methods': ['execute()'],
        'attributes': ['name', 'is_active',
                       'dos_cmd', 'working_dir', 'timeout']
    },
}
