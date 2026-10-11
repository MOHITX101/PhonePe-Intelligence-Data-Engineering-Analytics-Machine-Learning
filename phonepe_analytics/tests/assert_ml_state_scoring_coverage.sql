with expected_coverage as (

    select
        count(distinct state_slug) as expected_state_count

    from {{ ref('mart_state_quarterly_performance') }}

    where period_start_date = (
        select
            max(period_start_date)

        from {{ ref('mart_state_quarterly_performance') }}
    )

),

actual_coverage as (

    select
        count(*) as actual_row_count,
        count(distinct state_slug) as actual_state_count,
        count(distinct feature_period) as feature_period_count,
        count(distinct target_period) as target_period_count,

        sum(
            case
                when target_period_start_date
                    <>
                    add_months(
                        feature_period_start_date,
                        3
                    )
                then 1
                else 0
            end
        ) as invalid_target_dates

    from {{ ref('mart_ml_state_scoring_features') }}

)

select
    expected_coverage.expected_state_count,
    actual_coverage.actual_row_count,
    actual_coverage.actual_state_count,
    actual_coverage.feature_period_count,
    actual_coverage.target_period_count,
    actual_coverage.invalid_target_dates

from expected_coverage

cross join actual_coverage

where actual_coverage.actual_row_count
        <> expected_coverage.expected_state_count

   or actual_coverage.actual_state_count
        <> expected_coverage.expected_state_count

   or actual_coverage.feature_period_count <> 1

   or actual_coverage.target_period_count <> 1

   or actual_coverage.invalid_target_dates <> 0