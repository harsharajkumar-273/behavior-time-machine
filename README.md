# Behavior Time Machine

Replay a GW-BASIC library fee calculator beside its Python migration. Find the first behavior difference and turn it into a regression test. An independent Kiroween Resurrection prototype.

## Run the demo

```sh
docker build -t behavior-time-machine .
docker run --rm -p 8080:8080 behavior-time-machine
```

Open http://localhost:8080. Select **Initial port**, then **Run boundary sweep**. The smallest mismatch is day 4, when BASIC charges $1.00 and Python charges $0.25. Inspect the BASIC lines and copy the acceptance criterion or pytest regression. Switch to **Corrected port** to rerun the sweep and then replay day 4.

The BASIC program is an original fictional library fixture. The server executes it through [PC-BASIC](https://github.com/robhagemans/pcbasic) on each run. The supported range is 0 through 365 whole days overdue. The demonstration includes two explicit Python variants so the regression and its fix remain replayable.

## Local development and tests

With Python 3.11 and Node 22 installed, run these commands from the project root.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm ci --prefix frontend
npm run build --prefix frontend
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000. For live frontend reloads, also run `npm run dev --prefix frontend` and open the Vite URL. OpenAPI documentation is available at `/docs`.

## Publish

Create a public GitHub repository and push the project with the root `.kiro/` directory. Connect the repository to a Docker-capable host such as Railway and deploy the root Dockerfile. The container listens on the platform's `PORT` or defaults to 8080. Enable a public HTTPS domain, then test the initial sweep, copied evidence, corrected sweep, and day-four replay in a private browser window. Keep the demo live through judging.

## Kiro workflow and attribution

The committed spec, steering rule, and hook are ready for Kiro IDE. The prototype was implemented in Codex. To demonstrate real Kiro work, open this project in Kiro IDE and perform a substantive migration follow-up. For example, exercise the same workflow on the fee-cap boundary with an intentionally uncapped version of the port, confirm the observed policy, have Kiro add the regression and fix the port, and save the resulting spec and test evidence. Restore the public demo to the original two variants before recording its walkthrough. Describe only the Kiro work actually performed in the Devpost write-up.

A demo recording can follow the main workflow in under three minutes. Explain the migration, run the initial sweep, show the day-four evidence, show the genuine Kiro session and regression, then run the corrected sweep and replay the failing input.
