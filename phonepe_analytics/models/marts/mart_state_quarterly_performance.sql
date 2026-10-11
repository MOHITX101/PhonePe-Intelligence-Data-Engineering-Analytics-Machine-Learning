with base as (

    select
        geography_slug as state_slug,
        year,
        quarter,
        period,
        period_start_date,

        total_transaction_count,
        transaction_category_count,
        registered_user_count,
        registered_merchant_count,

        has_transaction_data,
        has_user_data,
        has_merchant_data

    from {{ ref('int_geography_quarterly_metrics') }}

    where file_scope = 'state'

),

with_lags as (

    select
        *,

        lag(total_transaction_count, 1) over (
            partition by state_slug
            order by period_start_date
        ) as previous_quarter_transaction_count,

        lag(total_transaction_count, 4) over (
            partition by state_slug
            order by period_start_date
        ) as previous_year_transaction_count,

        lag(registered_user_count, 1) over (
            partition by state_slug
            order by period_start_date
        ) as previous_quarter_user_count,

        lag(registered_user_count, 4) over (
            partition by state_slug
            order by period_start_date
        ) as previous_year_user_count,

        lag(registered_merchant_count, 1) over (
            partition by state_slug
            order by period_start_date
        ) as previous_quarter_merchant_count,

        lag(registered_merchant_count, 4) over (
            partition by state_slug
            order by period_start_date
        ) as previous_year_merchant_count

    from base

),

calculated_metrics as (

    select
        state_slug,
        year,
        quarter,
        period,
        period_start_date,

        total_transaction_count,
        transaction_category_count,
        registered_user_count,
        registered_merchant_count,

        round(
            cast(total_transaction_count as double)
            / nullif(cast(registered_user_count as double), 0),
            4
        ) as transactions_per_registered_user,

        round(
            cast(total_transaction_count as double)
            / nullif(cast(registered_merchant_count as double), 0),
            4
        ) as transactions_per_registered_merchant,

        round(
            100.0
            * (
                total_transaction_count
                - previous_quarter_transaction_count
            )
            / nullif(previous_quarter_transaction_count, 0),
            4
        ) as transaction_qoq_growth_pct,

        round(
            100.0
            * (
                total_transaction_count
                - previous_year_transaction_count
            )
            / nullif(previous_year_transaction_count, 0),
            4
        ) as transaction_yoy_growth_pct,

        round(
            100.0
            * (
                registered_user_count
                - previous_quarter_user_count
            )
            / nullif(previous_quarter_user_count, 0),
            4
        ) as user_qoq_growth_pct,

        round(
            100.0
            * (
                registered_user_count
                - previous_year_user_count
            )
            / nullif(previous_year_user_count, 0),
            4
        ) as user_yoy_growth_pct,

        round(
            100.0
            * (
                registered_merchant_count
                - previous_quarter_merchant_count
            )
            / nullif(previous_quarter_merchant_count, 0),
            4
        ) as merchant_qoq_growth_pct,

        round(
            100.0
            * (
                registered_merchant_count
                - previous_year_merchant_count
            )
            / nullif(previous_year_merchant_count, 0),
            4
        ) as merchant_yoy_growth_pct,

        (
            case when has_transaction_data then 1 else 0 end
            + case when has_user_data then 1 else 0 end
            + case when has_merchant_data then 1 else 0 end
        ) as available_metric_count,

        has_transaction_data,
        has_user_data,
        has_merchant_data

    from with_lags

),

ranked as (

    select
        *,

        dense_rank() over (
            partition by year, quarter
            order by total_transaction_count desc
        ) as transaction_rank,

        dense_rank() over (
            partition by year, quarter
            order by registered_user_count desc
        ) as registered_user_rank,

        dense_rank() over (
            partition by year, quarter
            order by registered_merchant_count desc nulls last
        ) as registered_merchant_rank

    from calculated_metrics

)

select *
from ranked