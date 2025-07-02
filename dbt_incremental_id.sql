#macro 
{% macro get_max_value(table_name, column_name) %}

{% set query %}
    SELECT coalesce(MAX({{ column_name }}),0) as max_value
    FROM {{ table_name }}
{% endset %}

{% set results = run_query(query) %}

{% if execute %}
    {% set max_value = results.columns['max_value'][0] %}
    {{ return(max_value) }}
{% else %}
    {{ return(0) }}
{% endif %}

{% endmacro %}


z#model
{{ config(
    materialized='incremental',
    table_type='iceberg',
    incremental_strategy='append'
) }}

{% set max_value = get_max_value('athena_poc.incremental_id_test', 'acc_sk') %}

with aa as (
 select
transaction_id 
,customer_id
,CAST(CAST(CAST(transaction_date AS timestamp) AS DATE) AS VARCHAR) as transaction_date
,store_id
,product_id
,product_category
,quantity
,unit_price
,payment_method
,discount_applied
,shipping_cost
,customer_rating
,delivery_status
,customer_zipcode
,store_location
,is_online_purchase
,transaction_status
,(row_number() over (order by transaction_id) + {{ max_value }}) as acc_sk
,current_timestamp as load_date
from dbt_athena.glue_trnx_table_partitioned_new where CAST(CAST(CAST(transaction_date AS timestamp) AS DATE) AS VARCHAR) in ('2023-03-21') 
)

select *
from aa
