import sys
from pathlib import Path

import pcbasic


def main():
    keys = sys.stdin.read().replace("\n", "\r")
    fixture = Path(__file__).with_name("overdue.bas")
    with pcbasic.Session() as session, fixture.open("rb") as source:
        program = session.bind_file(source, name="OVERDUE.BAS")
        session.execute(f'LOAD "{program}"')
        session.press_keys(keys)
        session.execute("RUN")


if __name__ == "__main__":
    main()
