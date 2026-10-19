# Runbook and delivery guide

## Put this documentation into the project

The ZIP contains `README.md` and a `docs/` directory with Markdown guides and image assets. Extract it into a temporary folder first. Copy those two items into the root of `PHONEPE_LAKEHOUSE`; preserve any existing documentation you want to retain. No application code or secret files are included in this package.

GitHub renders the Mermaid diagram in README. Keep image filenames and relative paths unchanged so the screenshots load.

## Manual operational sequence

| Stage | Execution location | Gate before continuing |
| --- | --- | --- |
| Pin and profile source | Local Python | Commit recorded, JSON validity and coverage reviewed |
| Raw ingestion | Local uploader / S3 | Manifest totals and failed-file count checked |
| Bronze and Silver | Databricks notebooks | Parsing, source counts and business keys validated |
| Analytical models | dbt project | Full build/tests successful for current snapshot |
| Model development | Databricks ML notebook | Temporal comparison and frozen holdout evaluation |
| Register/promote | MLflow / Unity Catalog | Prediction parity, signature and metadata verified |
| Score | Databricks batch notebook | 36 valid states, one feature period and one target period |
| Publish forecasts | Delta merge | Expected rows and duplicate keys checked |
| Serve results | Streamlit | Correct snapshot, period, version and cache refresh |

Do not automatically retrain on every dashboard refresh. Source ingestion, transformation, retraining, scoring and UI refresh are separate operations. Airflow has not been implemented.

## Local startup

Git Bash, from repository root:

```bash
source .venv/Scripts/activate
cd streamlit_app
streamlit run app.py
```

The application requires its actual connection configuration, warehouse access and existing Gold/forecast tables. This documentation package alone is not the executable project.

## Documentation server

From the dbt project directory, with its configured credentials:

```bash
dbt docs generate
dbt docs serve --port 8080
```

The local docs address is `http://localhost:8080`. Documentation generation can succeed with metadata warnings; inspect both the generated catalog and model pages. It does not execute the entire test suite. Keep `manifest.json`, `catalog.json` and related generated files out of public hosting until reviewed for metadata disclosure.

## Forecast repeatability

The existing batch merge updates a record when state, target quarter and model version match. It retains separate target periods/versions, but not an immutable record of every repeat run. For stronger auditability, add a run identifier and input fingerprint, pin the resolved model version, and preserve a run-level manifest.

Use explicit batch filters when showing forecasts. Selecting the latest record independently for each state can mix periods or model versions. Check all 36 states belong to the intended feature/target period and model version.

## Public-hosting choices — not deployed yet

**Live warehouse-backed app:** requests query Databricks through server-side credentials. This needs least-privilege access, secrets management, quota/cost controls, caching, availability checks and careful control over public query-triggering actions.

**Snapshot demonstration:** a separately implemented mode reads sanitized, permitted-to-redistribute analytical extracts. It avoids a live warehouse dependency but must clearly display the snapshot and refresh dates. The uploaded evidence does not establish that this mode already exists.

Choose the mode before deployment. A GitHub repository does not by itself host a running Streamlit application. Do not publish credentials or expose a warehouse administrator identity to serve a public dashboard.

## Suggested release evidence

- Source commit and file-count manifest.
- Software environment versions from the actual run.
- dbt build output and sanitized test results.
- Model parameters, split dates, experiment/run identity and metric definitions.
- Registered-model prediction parity results.
- Scoring batch period/version/row-count checks.
- Dashboard smoke tests for all seven pages, empty filters and missing values.
- License/attribution review and secret scan.

## Git handoff

After copying the documentation, review only the intended files:

```bash
git status --short
git add README.md docs/
git diff --cached --stat
git diff --cached --check
git commit -m "docs: document PhonePe lakehouse analytics and forecasting"
```

Do not use `git add .` until unrelated and sensitive files have been reviewed. Confirm the intended remote before pushing. This guide does not create a remote, push code, deploy the dashboard or change the existing application.
