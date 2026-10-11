with base as (

    select
        state_slug,
        district_slug,
        district_name,
        year,
        quarter,
        period,
        period_start_date,

        total_transaction_count,
        total_transaction_amount,
        registered_user_count,
        registered_merchant_count,

        has_transaction_data,
        has_user_data,
        has_merchant_data

    from {{ ref('int_district_quarterly_metrics') }}

),

with_lags as (

    select
        *,

        lag(total_transaction_count, 1) over (
            partition by state_slug, district_slug
            order by period_start_date
        ) as previous_quarter_transaction_count,

        lag(total_transaction_count, 4) over (
            partition by state_slug, district_slug
            order by period_start_date
        ) as previous_year_transaction_count,

        lag(total_transaction_amount, 1) over (
            partition by state_slug, district_slug
            order by period_start_date
        ) as previous_quarter_transaction_amount,

        lag(total_transaction_amount, 4) over (
            partition by state_slug, district_slug
            order by period_start_date
        ) as previous_year_transaction_amount,

        lag(registered_user_count, 4) over (
            partition by state_slug, district_slug
            order by period_start_date
        ) as previous_year_user_count

    from base

),

calculated as (

    select
        state_slug,
        district_slug,
        district_name,
        year,
        quarter,
        period,
        period_start_date,

        total_transaction_count,
        total_transaction_amount,
        registered_user_count,
        registered_merchant_count,

        round(
            cast(total_transaction_amount as double)
            / nullif(cast(total_transaction_count as double), 0),
            2
        ) as average_transaction_value,

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
        ) as transaction_count_qoq_growth_pct,

        round(
            100.0
            * (
                total_transaction_count
                - previous_year_transaction_count
            )
            / nullif(previous_year_transaction_count, 0),
            4
        ) as transaction_count_yoy_growth_pct,

        round(
            100.0
            * (
                total_transaction_amount
                - previous_quarter_transaction_amount
            )
            / nullif(previous_quarter_transaction_amount, 0),
            4
        ) as transaction_amount_qoq_growth_pct,

        round(
            100.0
            * (
                total_transaction_amount
                - previous_year_transaction_amount
            )
            / nullif(previous_year_transaction_amount, 0),
            4
        ) as transaction_amount_yoy_growth_pct,

        round(
            100.0
            * (
                registered_user_count
                - previous_year_user_count
            )
            / nullif(previous_year_user_count, 0),
            4
        ) as registered_user_yoy_growth_pct,

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

        case
            when total_transaction_count is not null
            then dense_rank() over (
                partition by state_slug, year, quarter
                order by total_transaction_count desc nulls last
            )
        end as state_transaction_count_rank,

        case
            when total_transaction_amount is not null
            then dense_rank() over (
                partition by state_slug, year, quarter
                order by total_transaction_amount desc nulls last
            )
        end as state_transaction_amount_rank,

        case
            when total_transaction_count is not null
            then dense_rank() over (
                partition by year, quarter
                order by total_transaction_count desc nulls last
            )
        end as national_transaction_count_rank,

        case
            when total_transaction_amount is not null
            then dense_rank() over (
                partition by year, quarter
                order by total_transaction_amount desc nulls last
            )
        end as national_transaction_amount_rank

    from calculated

)

select *
from ranked