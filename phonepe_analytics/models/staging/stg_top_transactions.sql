with source as (

    select
        file_scope,
        geography_level,
        parent_state_slug,
        entity_name,
        entity_slug,
        rank_position,
        year,
        quarter,
        period,
        payment_instrument_type,
        transaction_count,
        relative_path,
        source_path,
        source_commit,
        content_sha256,
        ingested_at_utc

    from {{ source('silver', 'top_transactions') }}

),

standardized as (

    select
        file_scope,
        geography_level,
        parent_state_slug,
        entity_name,
        entity_slug as geography_slug,
        cast(rank_position as int) as rank_position,
        cast(year as int) as year,
        cast(quarter as int) as quarter,
        period,

        make_date(
            cast(year as int),
            ((cast(quarter as int) - 1) * 3) + 1,
            1
        ) as period_start_date,

        payment_instrument_type,
        cast(transaction_count as bigint) as transaction_count,

        relative_path,
        source_path,
        source_commit,
        content_sha256,
        ingested_at_utc

    from source

)

select *
from standardized