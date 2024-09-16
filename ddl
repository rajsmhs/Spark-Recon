create external table my_test_db.table_accuracy_table(
source_count bigint,
target_count bigint,
column_difference string,
data_matched_records bigint,
data_mismatched_records bigint,
data_mismatch_source bigint,
data_mismatch_target bigint,
Row_Count_Difference_Percent double,
application_id string,
table_name string,
load_date string)
stored as parquet location 's3://my-aws-bucket-demo-madhu/accuracy/';


CREATE OR REPLACE VIEW my_test_db.table_accuracy_view AS
SELECT
Source_count ,
target_count,
column_difference,
data_matched_records,
data_mismatched_records,
data_mismatch_source,
data_mismatch_target,
Row_Count_Difference_Percent,
(100 - Row_Count_Difference_Percent) as match_percentage,
application_id,
table_name,
load_date
from my_test_db.table_accuracy_table;
