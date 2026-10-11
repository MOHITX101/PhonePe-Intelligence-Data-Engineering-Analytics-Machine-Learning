with source as (

    select
        file_scope,
        state_slug,
        year,
        quarter,
        period,
        registered_user_count,
        relative_path,
        source_path,
        source_commit,
        content_sha256,
        ingested_at_utc

    from {{ source('silver', 'aggregated_users') }}

),

standardized as (

    select
        file_scope,

        case
            when file_scope = 'country' then 'india'
            else state_slug
        end as geography_slug,

        state_slug,
        cast(year as int) as year,
        cast(quarter as int) as quarter,
        period,

        make_date(
            cast(year as int),
            ((cast(quarter as int) - 1) * 3) + 1,
            1
        ) as period_start_date,

        cast(registered_user_count as bigint)
            as registered_user_count,

        relative_path,
        source_path,
        source_commit,
        content_sha256,
        ingested_at_utc

    from source

)

select *
from standardized