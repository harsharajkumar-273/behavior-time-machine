# Behavior parity requirements

## 1. Observe both calculators

- When given a whole number from 0 through 365 and a port version, the service shall execute the bundled BASIC program and return both fees in cents, the comparison result, and the relevant BASIC lines.
- If input is invalid, the service shall return a validation error. If the interpreter fails, the service shall report an execution error and omit parity claims.

## 2. Find counterexamples

- When a visitor runs a sweep, the service shall evaluate all 366 supported inputs in increasing order and report the total checked, total differences, and the smallest differing input.
- When the initial port receives four overdue days, the comparison shall report a 25-cent modern fee and a 100-cent legacy fee. The workbench shall make that observed behavior available as an acceptance criterion and a pytest regression.

## 3. Preserve the confirmed behavior

- The corrected port shall waive fees through day three. Starting on day four it shall charge 25 cents per overdue day from the original due date, capped at 1,000 cents.
- Given a return four days overdue, when the corrected calculator evaluates the return, it shall charge 100 cents.
- When swept against the original fixture, the corrected port shall match all 366 supported inputs.

## 4. Verify registered scalar migrations

- The manifest shall declare sources, range, parser, and labels without expected outputs. Invalid manifests shall return an invalid_manifest error.
- Compare and sweep shall share the same generated BASIC batch driver. A comparison shall execute a range containing one value.
- Integer bounds shall describe at most 10,000 inputs within the supported GW-BASIC loop range.
- The parser shall reject missing, extra, blank, fractional, or non-integer output lines.
- The transit initial port shall differ exactly at age 65 over 0–100. The corrected port shall match all 101 inputs.
- Each run report shall include the manifest, source and driver hashes, checked range, checked count, all observed comparisons, and every mismatch. Downloaded reports shall preserve these fields.

## 5. Inspect and reproduce evidence

- A completed sweep shall show a filterable, paginated results table and a range overview derived from actual comparisons.
- Inspecting a row shall update the displayed outputs and available regression evidence without discarding the completed sweep.
- A local replay command shall rerun a downloaded report against the registered case and compare its recorded evidence and source hashes.
- Invalid report ranges shall fail before interpreter execution. A changed recorded output or hash shall cause reproduction to fail.
