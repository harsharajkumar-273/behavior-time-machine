from typing import Literal

PortVersion = Literal["flawed", "corrected"]
MAX_DAYS = 365


def calculate_fee(days_overdue: int, port_version: PortVersion) -> int:
    if days_overdue <= 3:
        return 0
    billable_days = days_overdue - 3 if port_version == "flawed" else days_overdue
    return min(25 * billable_days, 1000)
