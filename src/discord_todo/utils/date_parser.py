from datetime import datetime


def parse_datetime(date_str: str) -> datetime:
    """
    文字列からdatetime型に変換する
    例: "2024-03-20 15:00" → datetime(2024, 3, 20, 15, 0)
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError("日付の形式は 'YYYY-MM-DD HH:MM' で入力してください") 