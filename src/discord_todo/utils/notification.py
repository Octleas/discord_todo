import re
from typing import Dict


def parse_notification_time(time_str: str) -> int:
    """
    通知時間文字列を分単位の数値に変換します。
    時間単位（h）または日単位（d）で指定可能です。
    例：
        "1h" -> 60 (1時間前)
        "1d" -> 1440 (1日前)
        "24h" -> 1440 (24時間前)
    """
    if not (time_str.endswith('h') or time_str.endswith('d')):
        raise ValueError("通知時間は時間単位（例：1h, 24h）または日単位（例：1d, 7d）で指定してください。")
    
    try:
        unit = time_str[-1]  # 'h' または 'd'
        value = int(time_str[:-1])
        
        if value <= 0:
            raise ValueError("通知時間は正の数で指定してください。")
        
        # 時間を分に変換
        if unit == 'h':
            if value > 720:  # 30日を超える通知は設定不可
                raise ValueError("時間指定の場合、最大720時間（30日）までです。")
            minutes = value * 60
        else:  # unit == 'd'
            if value > 30:  # 30日を超える通知は設定不可
                raise ValueError("日指定の場合、最大30日までです。")
            minutes = value * 24 * 60
            
        return minutes
        
    except ValueError as e:
        if str(e).startswith("通知時間は") or str(e).startswith("時間指定") or str(e).startswith("日指定"):
            raise
        raise ValueError("通知時間は数値で指定してください。") 