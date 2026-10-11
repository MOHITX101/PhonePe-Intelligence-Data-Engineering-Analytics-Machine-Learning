with category_totals as (

    select
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date,
        transaction_category,

        sum(transaction_count)
            as category_transaction_count

    from {{ ref('stg_aggregated_transactions') }}

    group by
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date,
        transaction_category

),

with_comparisons as (

    select
        *,

        sum(category_transaction_count) over (
            partition by
                file_scope,
                geography_slug,
                year,
                quarter
        ) as geography_total_transaction_count,

        lag(category_transaction_count, 1) over (
            partition by
                file_scope,
                geography_slug,
                transaction_category
            order by period_start_date
        ) as previous_quarter_category_count,

        lag(category_transaction_count, 4) over (
            partition by
                file_scope,
                geography_slug,
                transaction_category
            order by period_start_date
        ) as previous_year_category_count

    from category_totals

),

calculated as (

    select
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date,
        transaction_category,

        category_transaction_count,
        geography_total_transaction_count,

        round(
            100.0
            * cast(category_transaction_count as double)
            / nullif(
                cast(geography_total_transaction_count as double),
                0
            ),
            4
        ) as category_share_pct,

        round(
            100.0
            * (
                category_transaction_count
                - previous_quarter_category_count
            )
            / nullif(previous_quarter_category_count, 0),
            4
        ) as category_qoq_growth_pct,

        round(
            100.0
            * (
                category_transaction_count
                - previous_year_category_count
            )
            / nullif(previous_year_category_count, 0),
            4
        ) as category_yoy_growth_pct

    from with_comparisons

),

ranked as (

    select
        *,

        dense_rank() over (
            partition by
                file_scope,
                geography_slug,
                year,
                quarter
            order by category_transaction_count desc
        ) as category_rank

    from calculated

)

select *
from ranked