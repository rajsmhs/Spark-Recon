spark-submit   --deploy-mode client  --master yarn   --num-executors 5   --executor-cores 4   --driver-memory 1g   --executor-memory 10g   /home/hadoop/Data_Recon/app.py "griffin_datavalidation_blog.balance_sheet_source" "griffin_datavalidation_blog.balance_sheet_target" "1=1" "hbjk,hvhjv" "my-aws-bucket-demo-madhu" > logs/results.txt 2>&1


CREATE EXTERNAL TABLE `griffin_datavalidation_blog.table_accuracy`(
  `table_name` string, 
  `source_count` bigint, 
  `target_count` bigint, 
  `data_mismatched_records` bigint, 
  `data_mismatch_source` bigint, 
  `data_mismatch_target` bigint, 
  `row_count_difference_percent` double, 
  `match_prcentage` double, 
  `application_id` string, 
  `load_date` string)
  stored as PARQUET
  LOCATION 's3://my-aws-bucket-demo-madhu/accuracy/';

