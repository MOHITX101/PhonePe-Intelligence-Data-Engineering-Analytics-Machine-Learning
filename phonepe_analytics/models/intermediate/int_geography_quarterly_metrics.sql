with transaction_metrics as (

    select
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date,

        sum(transaction_count) as total_transaction_count,
        count(distinct transaction_category)
            as transaction_category_count

    from {{ ref('stg_aggregated_transactions') }}

    group by
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date

),

user_metrics as (

    select
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date,

        max(registered_user_count)
            as registered_user_count

    from {{ ref('stg_aggregated_users') }}

    group by
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date

),

merchant_metrics as (

    select
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date,

        max(registered_merchant_count)
            as registered_merchant_count

    from {{ ref('stg_aggregated_merchants') }}

    group by
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date

),

geography_period_keys as (

    select
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date
    from transaction_metrics

    union

    select
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date
    from user_metrics

    union

    select
        file_scope,
        geography_slug,
        state_slug,
        year,
        quarter,
        period,
        period_start_date
    from merchant_metrics

),

combined as (

    select
        keys.file_scope,
        keys.geography_slug,
        keys.state_slug,
        keys.year,
        keys.quarter,
        keys.period,
        keys.period_start_date,

        transactions.total_transaction_count,
        transactions.transaction_category_count,

        users.registered_user_count,
        merchants.registered_merchant_count,

        transactions.total_transaction_count is not null
            as has_transaction_data,

        users.registered_user_count is not null
            as has_user_data,

        merchants.registered_merchant_count is not null
            as has_merchant_data

    from geography_period_keys as keys

    left join transaction_metrics as transactions
        on keys.file_scope = transactions.file_scope
        and keys.geography_slug = transactions.geography_slug
        and keys.year = transactions.year
        and keys.quarter = transactions.quarter

    left join user_metrics as users
        on keys.file_scope = users.file_scope
        and keys.geography_slug = users.geography_slug
        and keys.year = users.year
        and keys.quarter = users.quarter

    left join merchant_metrics as merchants
        on keys.file_scope = merchants.file_scope
        and keys.geography_slug = merchants.geography_slug
        and keys.year = merchants.year
        and keys.quarter = merchants.quarter

)

select *
from combined