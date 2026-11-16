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
