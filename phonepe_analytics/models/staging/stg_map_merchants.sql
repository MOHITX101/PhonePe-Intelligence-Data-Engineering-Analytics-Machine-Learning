with source as (

    select
        file_scope,
        geography_level,
        parent_state_slug,
        area_name,
        area_slug,
        year,
        quarter,
        period,
        registered_merchant_count,
        relative_path,
        source_path,
        source_commit,
        content_sha256,
        ingested_at_utc

    from {{ source('silver', 'map_merchants') }}

),

standardized as (

    select
        file_scope,
        geography_level,
        parent_state_slug,
        area_name,
        area_slug as geography_slug,
        cast(year as int) as year,
        cast(quarter as int) as quarter,
        period,

        make_date(
            cast(year as int),
            ((cast(quarter as int) - 1) * 3) + 1,
            1
        ) as period_start_date,

        cast(registered_merchant_count as bigint)
            as registered_merchant_count,

        relative_path,
        source_path,
        source_commit,
        content_sha256,
        ingested_at_utc

    from source

)

select *
from standardized