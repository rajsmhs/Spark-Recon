{ config(
    materialized='table',
    table_type='iceberg'
) }}

{% set record_count = 0 %}

{% if execute %}
    {% set count_query %}
        SELECT COUNT(*) as record_count FROM {{ source('raw', 'check_table') }}
    {% endset %}
    {% set results = run_query(count_query) %}
    {% if results %}
        {% set record_count = results.columns[0].values()[0] %}
    {% endif %}
{% endif %}

{% if record_count < 1000 %}
    {% set dynamic_sql %}
        with customers as (
            select 
                customer_id,
                customer_name,
                region
            from {{ source('raw', 'customers') }}
            where active = true
        ),
        
        orders as (
            select 
                order_id,
                customer_id,
                order_date,
                amount
            from {{ source('raw', 'orders') }}
            where order_date >= '2024-01-01'
        ),
        
        final as (
            select 
                c.customer_id,
                c.customer_name,
                c.region,
                o.order_id,
                o.order_date,
                o.amount
            from customers c
            left join orders o on c.customer_id = o.customer_id
        )
        
        select * from final
    {% endset %}
{% else %}
    {% set dynamic_sql %}
        with large_customers as (
            select 
                customer_id,
                customer_name
            from {{ source('warehouse', 'dim_customers') }}
            where tier = 'PREMIUM'
        ),
        
        aggregated_orders as (
            select 
                customer_id,
                count(*) as order_count,
                sum(amount) as total_amount
            from {{ source('warehouse', 'fact_orders') }}
            group by customer_id
        ),
        
        summary as (
            select 
                c.customer_name,
                a.order_count,
                a.total_amount
            from large_customers c
            join aggregated_orders a on c.customer_id = a.customer_id
        )
        
        select * from summary
    {% endset %}
{% endif %}

{{ dynamic_sql }}
