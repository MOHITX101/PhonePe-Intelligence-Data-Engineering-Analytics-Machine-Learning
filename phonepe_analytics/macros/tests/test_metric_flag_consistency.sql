{% test metric_flag_consistency(
    model,
    flag_column,
    metric_columns
) %}

    select *
    from {{ model }}

    where
        (
            {{ flag_column }} = true
            and (
                {% for column_name in metric_columns %}
                    {{ column_name }} is null
                    {% if not loop.last %} or {% endif %}
                {% endfor %}
            )
        )

        or

        (
            {{ flag_column }} = false
            and (
                {% for column_name in metric_columns %}
                    {{ column_name }} is not null
                    {% if not loop.last %} or {% endif %}
                {% endfor %}
            )
        )

{% endtest %}