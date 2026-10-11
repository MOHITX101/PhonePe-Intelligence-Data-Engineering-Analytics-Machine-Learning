with transaction_rankings as (

    select
        'transaction' as metric_domain,
        'transaction_count' as metric_name,

        file_scope,
        geography_level,
        parent_state_slug,
        entity_name,
        geography_slug,
        rank_position,

        year,
        quarter,
        period,
        period_start_date,

        cast(transaction_count as double)
            as metric_value,

        source_path,
        source_commit,
        ingested_at_utc

    from {{ ref('stg_top_transactions') }}

),

user_rankings as (

    select
        'user' as metric_domain,
        'registered_user_count' as metric_name,

        file_scope,
        geography_level,
        parent_state_slug,
        entity_name,
        geography_slug,
        rank_position,

        year,
        quarter,
        period,
        period_start_date,

        cast(registered_user_count as double)
            as metric_value,

        source_path,
        source_commit,
        ingested_at_utc

    from {{ ref('stg_top_users') }}

),

merchant_rankings as (

    select
        'merchant' as metric_domain,
        'registered_merchant_count' as metric_name,

        file_scope,
        geography_level,
        parent_state_slug,
        entity_name,
        geography_slug,
        rank_position,

        year,
        quarter,
        period,
        period_start_date,

        cast(registered_merchant_count as double)
            as metric_value,

        source_path,
        source_commit,
        ingested_at_utc

    from {{ ref('stg_top_merchants') }}

),

combined as (

    select * from transaction_rankings

    union all

    select * from user_rankings

    union all

    select * from merchant_rankings

)

select
    *,

    rank_position <= 3 as is_top_3,
    rank_position <= 10 as is_top_10

from combined