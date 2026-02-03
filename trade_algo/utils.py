from datetime import datetime, time

def parse_time(time_str: str) -> time:
    """Parses HH:MM string into a datetime.time object."""
    return datetime.strptime(time_str, "%H:%M").time()

def time_to_minutes(t: time) -> int:
    """Converts time object to minutes since midnight."""
    return t.hour * 60 + t.minute

def is_later_or_equal(current_time: time, target_time_str: str) -> bool:
    """Checks if current_time is >= target_time."""
    target = parse_time(target_time_str)
    return current_time >= target
