with transaction_metrics as (

    select
        parent_state_slug as state_slug,
        geography_slug as district_slug,
        max(area_name) as district_name,
        year,
        quarter,
        period,
        period_start_date,

        sum(transaction_count) as total_transaction_count,
        sum(transaction_amount) as total_transaction_amount

    from {{ ref('stg_map_transactions') }}

    where geography_level = 'district'

    group by
        parent_state_slug,
        geography_slug,
        year,
        quarter,
        period,
        period_start_date

),

user_metrics as (

    select
        parent_state_slug as state_slug,
        geography_slug as district_slug,
        max(area_name) as district_name,
        year,
        quarter,
        period,
        period_start_date,

        max(registered_user_count)
            as registered_user_count

    from {{ ref('stg_map_users') }}

    where geography_level = 'district'

    group by
        parent_state_slug,
        geography_slug,
        year,
        quarter,
        period,
        period_start_date

),

merchant_metrics as (

    select
        parent_state_slug as state_slug,
        geography_slug as district_slug,
        max(area_name) as district_name,
        year,
        quarter,
        period,
        period_start_date,

        max(registered_merchant_count)
            as registered_merchant_count

    from {{ ref('stg_map_merchants') }}

    where geography_level = 'district'

    group by
        parent_state_slug,
        geography_slug,
        year,
        quarter,
        period,
        period_start_date

),

district_period_keys as (

    select
        state_slug,
        district_slug,
        year,
        quarter,
        period,
        period_start_date
    from transaction_metrics

    union

    select
        state_slug,
        district_slug,
        year,
        quarter,
        period,
        period_start_date
    from user_metrics

    union

    select
        state_slug,
        district_slug,
        year,
        quarter,
        period,
        period_start_date
    from merchant_metrics

),

combined as (

    select
        keys.state_slug,
        keys.district_slug,

        coalesce(
            transactions.district_name,
            users.district_name,
            merchants.district_name
        ) as district_name,

        keys.year,
        keys.quarter,
        keys.period,
        keys.period_start_date,

        transactions.total_transaction_count,
        transactions.total_transaction_amount,
        users.registered_user_count,
        merchants.registered_merchant_count,

        transactions.total_transaction_count is not null
            as has_transaction_data,

        users.registered_user_count is not null
            as has_user_data,

        merchants.registered_merchant_count is not null
            as has_merchant_data

    from district_period_keys as keys

    left join transaction_metrics as transactions
        on keys.state_slug = transactions.state_slug
        and keys.district_slug = transactions.district_slug
        and keys.year = transactions.year
        and keys.quarter = transactions.quarter

    left join user_metrics as users
        on keys.state_slug = users.state_slug
        and keys.district_slug = users.district_slug
        and keys.year = users.year
        and keys.quarter = users.quarter

    left join merchant_metrics as merchants
        on keys.state_slug = merchants.state_slug
        and keys.district_slug = merchants.district_slug
        and keys.year = merchants.year
        and keys.quarter = merchants.quarter

)

select *
from combined