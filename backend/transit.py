from .fees import PortVersion


def calculate_fare(age: int, port_version: PortVersion) -> int:
    senior = age > 65 if port_version == "flawed" else age >= 65
    return 100 if senior else 200
