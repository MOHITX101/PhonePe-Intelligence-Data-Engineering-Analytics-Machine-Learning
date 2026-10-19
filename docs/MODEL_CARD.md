# Model card: state transaction forecaster

## Intended use

Estimate the next quarter's PhonePe transaction count for each of 36 Indian states/UTs, using the latest available quarterly observations. Suitable for portfolio demonstration and exploratory planning; not a financial decision system or a forecast of all Indian digital payments.

## Model and target

The deployed MLflow PythonModel wraps a scikit-learn preprocessing pipeline and Random Forest trained on `log(next_count/current_count)`. It returns predicted transaction count, predicted log growth and predicted percentage growth. Counts are reconstructed by multiplying the current count by the exponential of predicted growth.

Final forest: 300 estimators; depth 8; minimum leaf size 3; max features 0.8; seed 42. Numeric preprocessing includes median imputation, `log1p` for selected nonnegative features and standard scaling. State identity is one-hot encoded with unknown categories ignored.

### Input contract

| Group | Features |
| --- | --- |
| Identity | `state_slug` |
| Calendar | `quarter`, `time_index`, `quarter_sin`, `quarter_cos` |
| Scale | `total_transaction_count`, `registered_user_count`, `registered_merchant_count` |
| Ratios | `transactions_per_registered_user`, `transactions_per_registered_merchant` |
| Ranks | `transaction_rank`, `registered_user_rank` |
| Lags | `lag_1_transaction_count` through `lag_4_transaction_count` |
| Rolling history | `rolling_4q_transaction_mean`, `rolling_4q_transaction_stddev` |
| Growth | `transaction_yoy_growth_pct`, `transaction_qoq_growth_pct`, `registered_user_qoq_growth_pct`, `registered_merchant_qoq_growth_pct` |

Current-quarter features are permissible only once that quarter's source data is available. Lag columns are relative to the feature quarter, not the target quarter. The SQL rolling mean/stddev excludes the current quarter (`4 preceding` through `1 preceding`). The seasonal-naive baseline correctly uses lag 3 relative to the feature quarter to reach the target quarter one year earlier.

## Temporal experiment design

The feature snapshot contains 1,039 eligible rows. Initial candidate training ends at target period 2024-Q2; candidate validation spans 2024-Q3–2025-Q2. Residual training is restricted to target periods beginning 2021-Q1.

| Fold | Train target range | Validation target range |
| --- | --- | --- |
| 1 | 2021-Q1–2022-Q2 | 2022-Q3–2023-Q2 |
| 2 | 2021-Q1–2023-Q2 | 2023-Q3–2024-Q2 |
| 3 | 2021-Q1–2024-Q2 | 2024-Q3–2025-Q2 |

Eight forest configurations are ranked by mean fold WMAPE, with fold variability as a secondary sort. The selected configuration is refitted on 648 rows covering 2021-Q1–2025-Q2. The held-out period contains 144 rows across 2025-Q3–2026-Q2.

Models remain fixed within evaluation blocks while each prediction uses that feature quarter's actual observations. This is rolling-input one-step-ahead evaluation, not recursive multi-step forecasting. Historical dataset revisions and source publication lag are not modeled by the current snapshot backtest.

## Recorded results

| Method / stage | WMAPE |
| --- | ---: |
| Last-quarter naive, initial validation | 6.29% |
| Direct Ridge, initial validation | 9.96% |
| Direct gradient boosting, initial validation | 10.01% |
| Direct Random Forest, initial validation | 11.44% |
| Residual Random Forest candidate, initial validation | 4.24% |
| Selected forest, mean rolling validation | 5.01% |
| Tuned residual Random Forest, final test | 2.82% |
| Last-quarter naive, final test | 5.30% |

Different stages use different training windows and configurations; their scores are not all paired comparisons. Relative test WMAPE reduction is reported as 46.86% from unrounded values.

```text
WMAPE (%) = 100 × sum(abs(actual − predicted)) / sum(abs(actual))
```

WMAPE is volume-weighted error, not classification accuracy. The recorded state-level test WMAPE ranges substantially: Ladakh is about 23.53%, compared with 3.03% for Maharashtra. Quarterly aggregate bias is negative in all four reported test quarters, with the largest underprediction in 2026-Q2. Report these distributions alongside the global score.

## Interpretation

Permutation importance is computed on the held-out test data using negative MAE of the **log-growth target**, not transaction-count WMAPE. Registered-user QoQ growth, transaction QoQ growth and transaction YoY growth have the largest recorded positive importance values.

The displayed percentage importance normalizes positive permutation-score changes. It is not explained variance, a causal contribution or a percentage of forecast volume. Correlated features can share information; near-zero or negative importance does not prove a feature is useless. Do not redesign features based on test-set explanations and continue calling that same test set untouched.

## Registry and batch output

- Model: `workspace.ml.phonepe_state_transaction_forecaster`
- Recorded version: `1`, alias `Champion`
- Input: `workspace.gold.mart_ml_state_scoring_features`
- Output: `workspace.ml.state_transaction_forecasts`
- Merge key: `state_slug`, `target_period`, `model_version`
- Stored metadata includes model identifiers, feature table, feature/target dates and scoring timestamp.

The supplied notebook registers the final training model; it does not show a separate refit on all labels through 2026-Q2. Repeated scoring updates the same state/period/version key, so the table is not an immutable history of every scoring attempt.

## Reproducibility issues requiring resolution

1. **Clipping mismatch.** Tuning and final evaluation clip log-growth predictions to training-derived quantiles. The registered wrapper exponentiates raw predictions without that clipping. Compare all 144 test predictions from the logged wrapper with the evaluated output; either include the same stored bounds or document/re-evaluate an intentionally unclipped model.
2. **Weak parity check.** The current verification accepts a WMAPE difference within 0.30 percentage points of 2.82. That does not prove prediction equivalence. The reload test checks five examples against the wrapper, not the full evaluated forecast.
3. **Hardcoded metadata.** Some MLflow parameters, scores and version descriptions are literal values. Derive them from the fitted estimator and actual split/results.
4. **Alias race.** Scoring resolves an alias version, then loads by alias separately. Pin the resolved version URI so logged metadata cannot disagree with the loaded model if Champion changes.
5. **Calendar continuity.** SQL row-offset lags and `lead` require contiguous quarters. Check exact feature-to-target date distance and every lag date, not just non-null values.
6. **Availability and issue date.** A historical snapshot does not prove what data was available at each historical origin. The example Q3 forecast was produced after Q3's calendar end in the supplied project chronology; label it a retrospective batch demonstration unless actual release/issue timestamps support a prospective claim.

## Limits and next evaluation

Only 34 source quarters are available. States share national conditions and are not independent temporal replications. No calibrated prediction intervals are shown. Population-normalized adoption, individual behavior and causal merchant effects cannot be inferred from these aggregate records alone.

Before production use: resolve parity; lock evaluation; add release-time-aware splits, per-state and per-quarter metrics, baseline-relative confidence intervals, feature ablations and drift checks. Evaluate any revised model on new untouched periods. Retain the current version and its original experiment record rather than silently replacing its claims.
