with base as (

    select
        geography_slug,
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

    where file_scope = 'country'

),

with_comparisons as (

    select
        *,

        lag(total_transaction_count, 1) over (
            order by period_start_date
        ) as previous_quarter_transaction_count,

        lag(total_transaction_count, 4) over (
            order by period_start_date
        ) as previous_year_transaction_count,

        lag(registered_user_count, 1) over (
            order by period_start_date
        ) as previous_quarter_user_count,

        lag(registered_user_count, 4) over (
            order by period_start_date
        ) as previous_year_user_count,

        lag(registered_merchant_count, 1) over (
            order by period_start_date
        ) as previous_quarter_merchant_count,

        lag(registered_merchant_count, 4) over (
            order by period_start_date
        ) as previous_year_merchant_count,

        first_value(total_transaction_count) over (
            order by period_start_date
        ) as baseline_transaction_count,

        first_value(registered_user_count) over (
            order by period_start_date
        ) as baseline_user_count,

        first_value(registered_merchant_count) over (
            order by period_start_date
        ) as baseline_merchant_count

    from base

)

select
    geography_slug,
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
        * (total_transaction_count - previous_quarter_transaction_count)
        / nullif(previous_quarter_transaction_count, 0),
        4
    ) as transaction_qoq_growth_pct,

    round(
        100.0
        * (total_transaction_count - previous_year_transaction_count)
        / nullif(previous_year_transaction_count, 0),
        4
    ) as transaction_yoy_growth_pct,

    round(
        100.0
        * (registered_user_count - previous_quarter_user_count)
        / nullif(previous_quarter_user_count, 0),
        4
    ) as user_qoq_growth_pct,

    round(
        100.0
        * (registered_user_count - previous_year_user_count)
        / nullif(previous_year_user_count, 0),
        4
    ) as user_yoy_growth_pct,

    round(
        100.0
        * (registered_merchant_count - previous_quarter_merchant_count)
        / nullif(previous_quarter_merchant_count, 0),
        4
    ) as merchant_qoq_growth_pct,

    round(
        100.0
        * (registered_merchant_count - previous_year_merchant_count)
        / nullif(previous_year_merchant_count, 0),
        4
    ) as merchant_yoy_growth_pct,

    round(
        100.0
        * cast(total_transaction_count as double)
        / nullif(cast(baseline_transaction_count as double), 0),
        4
    ) as transaction_index,

    round(
        100.0
        * cast(registered_user_count as double)
        / nullif(cast(baseline_user_count as double), 0),
        4
    ) as registered_user_index,

    round(
        100.0
        * cast(registered_merchant_count as double)
        / nullif(cast(baseline_merchant_count as double), 0),
        4
    ) as registered_merchant_index,

    has_transaction_data,
    has_user_data,
    has_merchant_data

from with_comparisons