{{
    config(
        materialized = 'table'
    )
}}

with source_data as (

    select
        state_slug,
        year,
        quarter,
        period as feature_period,
        period_start_date as feature_period_start_date,

        total_transaction_count,
        registered_user_count,
        registered_merchant_count,

        transaction_yoy_growth_pct,
        transactions_per_registered_user,

        transaction_rank,
        registered_user_rank

    from {{ ref('mart_state_quarterly_performance') }}

),

window_features as (

    select
        *,

        lag(total_transaction_count, 1) over (
            partition by state_slug
            order by feature_period_start_date
        ) as lag_1_transaction_count,

        lag(total_transaction_count, 2) over (
            partition by state_slug
            order by feature_period_start_date
        ) as lag_2_transaction_count,

        lag(total_transaction_count, 3) over (
            partition by state_slug
            order by feature_period_start_date
        ) as lag_3_transaction_count,

        lag(total_transaction_count, 4) over (
            partition by state_slug
            order by feature_period_start_date
        ) as lag_4_transaction_count,

        lag(registered_user_count, 1) over (
            partition by state_slug
            order by feature_period_start_date
        ) as lag_1_registered_user_count,

        lag(registered_merchant_count, 1) over (
            partition by state_slug
            order by feature_period_start_date
        ) as lag_1_registered_merchant_count,

        avg(total_transaction_count) over (
            partition by state_slug
            order by feature_period_start_date
            rows between 4 preceding and 1 preceding
        ) as rolling_4q_transaction_mean,

        stddev_samp(total_transaction_count) over (
            partition by state_slug
            order by feature_period_start_date
            rows between 4 preceding and 1 preceding
        ) as rolling_4q_transaction_stddev,

        lead(total_transaction_count, 1) over (
            partition by state_slug
            order by feature_period_start_date
        ) as target_next_quarter_transaction_count,

        lead(feature_period, 1) over (
            partition by state_slug
            order by feature_period_start_date
        ) as target_period,

        lead(feature_period_start_date, 1) over (
            partition by state_slug
            order by feature_period_start_date
        ) as target_period_start_date

    from source_data

),

final_features as (

    select
        state_slug,
        year,
        quarter,
        feature_period,
        feature_period_start_date,

        (
            (year - 2018) * 4 + quarter
        ) as time_index,

        sin(
            2 * pi() * quarter / 4
        ) as quarter_sin,

        cos(
            2 * pi() * quarter / 4
        ) as quarter_cos,

        total_transaction_count,
        registered_user_count,
        registered_merchant_count,

        transaction_yoy_growth_pct,
        transactions_per_registered_user,

        case
            when registered_merchant_count > 0
            then
                total_transaction_count
                / registered_merchant_count
        end as transactions_per_registered_merchant,

        transaction_rank,
        registered_user_rank,

        lag_1_transaction_count,
        lag_2_transaction_count,
        lag_3_transaction_count,
        lag_4_transaction_count,

        rolling_4q_transaction_mean,
        rolling_4q_transaction_stddev,

        case
            when lag_1_transaction_count > 0
            then
                (
                    total_transaction_count
                    / lag_1_transaction_count
                    - 1
                ) * 100
        end as transaction_qoq_growth_pct,

        case
            when lag_1_registered_user_count > 0
            then
                (
                    registered_user_count
                    / lag_1_registered_user_count
                    - 1
                ) * 100
        end as registered_user_qoq_growth_pct,

        case
            when lag_1_registered_merchant_count > 0
            then
                (
                    registered_merchant_count
                    / lag_1_registered_merchant_count
                    - 1
                ) * 100
        end as registered_merchant_qoq_growth_pct,

        target_period,
        target_period_start_date,
        target_next_quarter_transaction_count

    from window_features

   where lag_4_transaction_count is not null
      and target_next_quarter_transaction_count is not null
      and registered_user_count is not null
      and registered_merchant_count is not null
      and lag_1_registered_user_count > 0
      and lag_1_registered_merchant_count > 0
)

select *
from final_features