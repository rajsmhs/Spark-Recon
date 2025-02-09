{% macro cleanup_model() %}
    {% set schema = target.schema %}
    {% set relation = adapter.get_relation(
        database=target.database,
        schema=target.schema,
        identifier=model.name
    ) %}

    {{ log("Starting cleanup for " ~ schema ~ "." ~ model.name, info=True) }}

    {% if relation is not none %}
        {% set drop_query %}
            DROP TABLE IF EXISTS {{ schema }}.{{ model.name }}
        {% endset %}
        
        {% do run_query(drop_query) %}
        {{ log("Table dropped: " ~ model.name, info=True) }}
    {% else %}
        {{ log("Table does not exist: " ~ model.name, info=True) }}
    {% endif %}

    {{ log("Cleanup completed", info=True) }}
{% endmacro %}
