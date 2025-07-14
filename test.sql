{{
  config(
    post_hook="{{ audit_log_post_execution('0oalglv9nhtv1qhhh697_efront', this.name, 'success') }}",
    materialized='incremental',
    incremental_strategy='append',
    on_schema_change='sync_all_columns',
    schema='ad_dna_formatted',
    s3_data_dir='s3://' ~ var('s3_bucket_name_formatted') ~ '/formatted/client_0oalglv9nhtv1qhhh697/efront',
    s3_data_naming='table_unique',
    tags=["0oalglv9nhtv1qhhh697", "efront", "formatted"],
    write_compression=none,
    table_type='iceberg',
    format='parquet',
    lf_tags_config={
          'enabled': true,
          'tags': {
            'client': '0oalglv9nhtv1qhhh697',
            'dataset': 'efront'
          }
    },
    partitioned_by=["year", "month", "day", "hour", "minute"],
    alias='0oalglv9nhtv1qhhh697_efront_dna_bankops'
  )
}}

{% set batch_id = audit_log_pre_execution('0oalglv9nhtv1qhhh697_efront', this.name) %}

{% set result = get_dq_macro_pass('ad_dna_formatted_stg', '0oalglv9nhtv1qhhh697_efront_dna_bankops', this) %}

{{ audit_get_latest_date(this.name) }}

SELECT
    fund,
    fund_id,
    bank_account,
    type,
    close_date,
    payment_curr,
    {{ convert_from_string_to_decimal('amount_bank') }} AS amount_bank,
    {{ convert_from_string_to_decimal('amount_payment') }} AS amount_payment,
    {{ convert_from_string_to_decimal('amount_entity') }} AS amount_entity,
    {{ convert_from_string_to_decimal('amount_counterparty') }} AS amount_counterparty,
    x_ad_meta_ingestion_date,
    x_ad_meta_partition_date,
    x_ad_meta_hash_key,
    year,
    month,
    day,
    hour,
    minute,
    {{batch_id}} as batch_id
FROM {{ source('ad_dna_formatted_stg', '0oalglv9nhtv1qhhh697_efront_dna_bankops') }}
WHERE (CAST(x_ad_meta_ingestion_date AS TIMESTAMP(6))) > (
    SELECT MAX(execution_start_date)
    FROM audit_exec_max_date
);
