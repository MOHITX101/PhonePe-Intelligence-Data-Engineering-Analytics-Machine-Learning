{% test value_between(
    model,
    column_name,
    minimum_value,
    maximum_value
) %}

    select *
    from {{ model }}

    where {{ column_name }} is not null
      and (
          {{ column_name }} < {{ minimum_value }}
          or {{ column_name }} > {{ maximum_value }}
      )

{% endtest %}