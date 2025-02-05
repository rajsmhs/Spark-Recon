CREATE EXTERNAL TABLE `transaction_data`(
  `src_strt_dt` date, 
  `det_amount` decimal(18,3), 
  `det_func_code` string, 
  `det_prod_code` string, 
  `det_sub_prod_code` string, 
  `det_acc_nbr_orig` string, 
  `brr_mrch_nbr` string, 
  `row_chksum` string, 
  `brr_mrch_nbr1` string, 
  `det_date_capture` date, 
  `det_tran_class` string, 
  `det_source_id` string, 
  `det_ods_end_point` string, 
  `curr_code` string, 
  `det_channel_code` string, 
  `det_rec_type` string, 
  `tand_wallet_id` string, 
  `mcc` string, 
  `crx_mcc_code` string, 
  `pmt_auxdom` string, 
  `aux_dom` string, 
  `ex_aux_dom` string, 
  `af_type` string, 
  `track_2` string, 
  `det_bank_origin` string, 
  `det_bank_origin_1` string, 
  `statement_details` string, 
  `det_tran_code` string, 
  `dup_sqnc_nbr` string, 
  `det_bsb` string, 
  `det_trace_id` string, 
  `brr_number_of_items` int, 
  `receipt_number` string, 
  `from_account` string, 
  `to_account` string, 
  `det_app_group_code` string, 
  `source1` string, 
  `det_seq_nbr` string, 
  `det_app_delv_code` string, 
  `bpay_payer_initr_code` string, 
  `det_date_effective` date, 
  `csl_refund_reason` string, 
  `det_value_nonval` decimal(18,3), 
  `det_float_3_days` int, 
  `cash_amt` decimal(18,3), 
  `det_time_capture` timestamp, 
  `biller_number` string, 
  `det_misc_field` string, 
  `brr_item_cheque_nbr` string, 
  `src_delt_flag` string)
PARTITIONED BY ( 
  `load_date` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  's3://dbt-athena-vrajabhi-bucket/transaction_data/'
TBLPROPERTIES (
  'CrawlerSchemaDeserializerVersion'='1.0', 
  'CrawlerSchemaSerializerVersion'='1.0', 
  'UPDATED_BY_CRAWLER'='bteq-transaction-crawler', 
  'averageRecordSize'='459', 
  'classification'='parquet', 
  'compressionType'='none', 
  'objectCount'='10', 
  'partition_filtering.enabled'='true', 
  'recordCount'='100000', 
  'sizeKey'='38576318', 
  'typeOfData'='file')

CloudShell
Feedback
