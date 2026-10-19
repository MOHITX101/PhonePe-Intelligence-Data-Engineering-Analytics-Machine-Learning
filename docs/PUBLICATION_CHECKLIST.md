# Publication and research readiness

This review documents the supplied implementation; it does not modify or rerun the application.

## Before GitHub publication

- [ ] Fix district currency formatting. The screenshot shows Bengaluru value `2237234966747` as ₹22.37T; it is approximately ₹2.24T. Check trillion = `1_000_000_000_000`, billion = `1_000_000_000`, crore = `10_000_000`. Replace the screenshot after validating the code.
- [ ] Resolve the model clipping mismatch and verify full-test prediction parity described in the model card.
- [ ] Run the complete dbt build against the intended snapshot and save sanitized `run_results.json` evidence. Do not label 307 discovered tests as 307 passed tests.
- [ ] Add continuity tests for exact quarter intervals and expected dates. Row offsets are not date offsets when periods are missing.
- [ ] Review `metric_flag_consistency`: a NULL flag is not caught by equality to true/false. Pair it with a non-null flag test where required.
- [ ] Review strict-positive rules. `positive_value` allows NULLs but rejects zero; this is not a generic nonnegative test. A zero rolling standard deviation can be legitimate, so the scoring-mart strict-positive stddev test deserves revision.
- [ ] Compare training and scoring feature values for overlapping historical snapshots, not just column names.
- [ ] Relabel historical model scores as historical evaluation, rather than implying live drift or forecast-accuracy monitoring.
- [ ] Improve low-contrast refresh-button text and clipped gauge labels.
- [ ] Review geographic ranking scope and top-subset coverage; do not mix within-state source ranks into a national ranking.
- [ ] Reconcile country/state totals before choosing a national denominator, and keep registered-count snapshots separate from additive transaction flows.
- [ ] Inspect notebook outputs, SQL artifacts and tracked files for secrets, internal URLs and unnecessary identifiers.
- [ ] Ensure `.streamlit/secrets.toml`, `config/local/`, `.env`, `.venv/` and generated caches are ignored. If a secret was ever committed, rotate it; ignoring it now does not remove history.
- [ ] Verify source attribution and licensing for the pinned snapshot, exported data and public screenshots; choose a license for original code.
- [ ] Add the actual public application link only after deployment and an unauthenticated-access smoke test.

## Evidence scope

| Evidence | Review coverage |
| --- | --- |
| Intermediate/mart SQL and custom test macros | Read for model structure, joins, windows, target construction and test semantics |
| YAML model tests | Inspected for declared checks and coverage |
| EDA notebook | Reviewed national/statistical-analysis logic relevant to the documented findings |
| Training notebook | Reviewed split, baselines, residual model, tuning, evaluation, importance and registry logic |
| Batch notebook | Reviewed validation, alias loading, reconstruction and merge behavior |
| Dashboard screenshots | Visually reviewed; appearance is not runtime correctness evidence |
| Staging, ingestion and Streamlit implementation | Not provided in this review; operational behavior not independently reproduced |

## Research paper: a defensible next phase

### Working question

Does baseline-relative growth modeling improve one-quarter-ahead regional PhonePe transaction forecasting compared with direct count modeling and simple temporal baselines?

### Proposed contributions — to establish, not assume

1. A traceable pipeline from a pinned public snapshot to a documented state-quarter dataset.
2. A reproducible comparison of direct and growth-relative forecasting.
3. An error analysis examining large/small states, temporal regime shifts and geographic heterogeneity.

### Experiments still needed

| Question | Required experiment |
| --- | --- |
| Is improvement robust? | More held-out origins, paired baseline comparisons and dependence-aware uncertainty |
| Does the target transformation matter? | Same inputs/window/model class with count, log-count and log-growth targets |
| Do merchant/user signals help? | Transaction-only vs enriched feature ablation |
| Does the cutoff matter? | Compare full history with several predeclared recent-window choices |
| Is performance balanced? | State-level distributions, macro-averaged errors and volume-weighted errors |
| Is inference reproducible? | Full-test equality between evaluated and registered predictor |
| Is this realistic forecasting? | Data-release timestamps, revision policy and origin-specific feature availability |
| How uncertain are predictions? | Calibrated intervals evaluated on periods not used to calibrate them |

The district bootstrap currently samples districts independently. Spatial or state-level dependence can affect inference. Use a defensible clustered/block procedure or explicitly restrict conclusions. Mann–Whitney is a distributional comparison; interpreting it as a median-only test requires additional assumptions.

### Suggested paper structure

Abstract; motivation and related work; source data and licensing; pipeline and metric definitions; temporal experimental protocol; baselines and model specification; results and uncertainty; ablations; geographic diagnostics; limitations; reproducibility statement; conclusion.

Avoid claims of national market representativeness, causal adoption effects, enterprise-scale performance, fully automated orchestration or guaranteed publication. Novelty must be established against the literature, not inferred from the number of tools used.
