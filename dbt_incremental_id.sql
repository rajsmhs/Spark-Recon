{{ config(
    materialized='incremental',
    table_type='iceberg',
    incremental_strategy='append'
) }}


{% set max_value = 0 %}

{% if execute %}
    {% set query %}
        SELECT coalesce(MAX(acc_sk), 0) as max_value
        FROM {{ this }}
    {% endset %}
    
    {% if adapter.get_relation(database=this.database, schema=this.schema, identifier=this.identifier) %}
        {% set results = run_query(query) %}
        {% if results %}
            {% set max_value = results.columns[0].values()[0] %}
        {% endif %}
    {% endif %}
{% endif %}

with trans_data as (
 select
transaction_id 
,customer_id
-- Convert transaction_date to string format
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
from "union"

)

select *
from trans_data
