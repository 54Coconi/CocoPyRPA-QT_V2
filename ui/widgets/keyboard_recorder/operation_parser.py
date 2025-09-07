"""
用于解析结构化数据，并处理组合键的持续时间逻辑：
    - 对于组合键块，仅保留最长的持续时间 delay
    - 将时间插入到组合键中第一个释放的按键之前
"""

import time


def parse_operation_history(structured_history: list) -> list:
    """
    功能：
        1. 处理组合键的持续时间逻辑：
            - 对于组合键块，仅保留最长的 delay，过滤其他 delay
            - 然后将最长的 delay 插入到组合键中第一个释放的按键之前
            - 保持结构化格式输出
        2. 过滤掉仅按下而未释放的按键，确保所有按键均释放

    Args:
        structured_history (list): 结构化数据

    Returns:
        result (list): 处理后的结构化数据
    """
    result = []  # 结果
    combo_keys = []  # 当前组合
    key_down_time = {}  # {key_name: press_time}
    temp_block = []  # 当前组合块
    delays = []  # 持续时间

    i = 0
    while i < len(structured_history):
        entry = structured_history[i]

        if entry["type"] == "keyboard" and entry["action"] == "keyPress":
            key = entry["key"]
            combo_keys.append(key)
            key_down_time[key] = entry["time"]
            temp_block.append(entry)
            i += 1

        elif entry["type"] == "flow" and entry["action"] == "delay":
            delays.append((entry, i))
            i += 1

        elif entry["type"] == "keyboard" and entry["action"] == "keyRelease":
            key = entry["key"]
            temp_block.append(entry)

            if key in combo_keys:
                combo_keys.remove(key)

            # 当前组合块结束
            if not combo_keys:
                if delays:
                    delays.sort(key=lambda d: d[0]["delay_time"], reverse=True)
                    max_delay_entry = delays[0][0]
                    inserted = False
                    for j, sub_entry in enumerate(temp_block):
                        # 插入到第一个释放的按键之前
                        if sub_entry["type"] == "keyboard" and sub_entry["action"] == "keyRelease":
                            temp_block.insert(j, max_delay_entry)
                            inserted = True
                            break
                    if not inserted:
                        temp_block.append(max_delay_entry)

                result.extend(temp_block)
                temp_block = []
                delays = []
                key_down_time = {}

            i += 1

        else:
            i += 1

    return result


def operation_history_to_text(operation_history: list) -> list:
    """将操作历史转换为人类可读格式

    Args:
        operation_history (list): 操作历史数据

    Returns:
        list: 人类可读的操作历史数据
    """
    results = []
    for item in operation_history:
        if item["type"] == "keyboard":
            action = "按下 ↓" if item["action"] == "keyPress" else "释放 ↑"
            key = item.get("key", "")
            time_str = time.strftime("%H:%M:%S", time.localtime(item["time"]))
            results.append(f"{action}: {key} (时间: {time_str})")
        elif item["type"] == "flow" and item["action"] == "delay":
            results.append(f"持续 ⏱: {item['delay_time']:.2f} 秒")

    return results
