import re
from typing import Dict


def parse_notification_time(time_str: str) -> int:
    """通知時間文字列を分単位の数値に変換する

    Args:
        time_str (str): 通知時間文字列（例: "1h", "30m", "1d"）

    Returns:
        int: 分単位の通知時間

    Raises:
        ValueError: 不正な形式の場合
    """
    # 時間単位の定義（分単位での値）
    units: Dict[str, int] = {
        "m": 1,  # 分
        "h": 60,  # 時間
        "d": 1440,  # 日
    }

    match = re.match(r"^(\d+)([mhd])$", time_str.lower())
    if not match:
        raise ValueError(
            f"不正な通知時間形式です: {time_str}. 正しい形式: 数字 + 単位(m/h/d)"
        )

    value, unit = int(match.group(1)), match.group(2)
    return value * units[unit] 