import os
import sys
from util import get_spark_session
from process import *
import datetime
from pyspark.sql.types import *
from pyspark.sql.functions import *


def main():
    source_table = str(sys.argv[1])
    target_table = str(sys.argv[2])
    filter_condition = str(sys.argv[3])
    exclude_column_list =str(sys.argv[4]).split(",")
    print(exclude_column_list)
    target_bucket = str(sys.argv[5])

    spark = get_spark_session('Recon_'+source_table.replace(".","_"))

    col_list = get_column_list(source_table,filter_condition,exclude_column_list,spark)
    print(col_list)

    src_df,target_df,mismatched_df = compare_source_target(source_table,target_table,col_list,filter_condition,spark)


    write_dataframe(mismatched_df,target_bucket,"mismatched_records",source_table,"json","True")

    recon_df = accuracy_summary_validation(src_df,target_df,mismatched_df,spark)

    recon_df.printSchema()
    write_dataframe(recon_df,target_bucket,"accuracy",source_table,"parquet","False")


if __name__ == '__main__':
    main()
