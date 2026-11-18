"""Execute a generated batch driver with the real PC-BASIC interpreter."""
import io
import json
import re
import sys



def build_driver(source: str, lower: int, upper: int) -> str:
    lines = source.splitlines()
    statements = []
    for line in lines:
        match = re.fullmatch(r"(\d+) (.+)", line)
        if not match or not 1000 <= int(match[1]) <= 65529:
            raise ValueError("Fixture lines must be numbered from 1000 through 65529.")
        statements.append((int(match[1]), match[2]))
    numbers = [number for number, _ in statements]
    if numbers != sorted(set(numbers)):
        raise ValueError("Fixture line numbers must be unique and increasing.")
    if statements[0][1] != "INPUT X" or statements[-1][1] != "END":
        raise ValueError("Fixture must start with INPUT X and finish with END.")
    if sum(statement == "INPUT X" for _, statement in statements) != 1:
        raise ValueError("Fixture must consume exactly one integer.")
    # Adapt the scalar program to a subroutine. The driver supplies the input;
    # the original policy and PRINT statement execute unchanged for every value.
    adapted = [f"{number} {statement}" for number, statement in statements[1:-1]]
    return "\n".join([
        f"10 FOR X = {lower} TO {upper}",
        f"20 GOSUB {statements[1][0]}",
        "30 NEXT X",
        "40 END",
        *adapted,
        f"{statements[-1][0]} RETURN",
    ])


def main():
    import pcbasic

    payload = json.load(sys.stdin)
    program = build_driver(payload["source"], payload["minimum"], payload["maximum"])
    output = io.StringIO()
    with pcbasic.Session(output_streams=output, input_streams=()) as session:
        with io.BytesIO(program.encode("ascii")) as source:
            name = session.bind_file(source, name="BATCH.BAS")
            session.execute(f'LOAD "{name}"')
            session.execute("RUN")
    sys.stdout.write(output.getvalue())


if __name__ == "__main__":
    main()
