import datetime
from pyspark.sql.types import *
from pyspark.sql.functions import *


def get_column_list(source_table,filter_condition,exclude_column_list,spark_session):
    source_df = spark_session.sql(f"select * from {source_table} where {filter_condition} limit 1")
    source_column = [col.lower() for col in source_df.columns]
    exclude_column = [col.lower() for col in exclude_column_list]
    final_column_list = list(set(source_column) - set(exclude_column))
    return final_column_list



def compare_source_target(source_table,target_table,column_list,filter_condition,spark_session):
    source_df = spark_session.sql(f"select {', '.join(column_list)} from {source_table} where {filter_condition}")
    target_df = spark_session.sql(f"select {', '.join(column_list)} from {target_table} where {filter_condition}")
    df_missing_rec = (
                    source_df.subtract(target_df).withColumn("Data_Mismatch",lit("Data Missing Values At Target"))
                        .union(target_df.subtract(source_df).withColumn("Data_Mismatch", lit("Data Missing Values At Source")))
                     )
    df_missing_rec = df_missing_rec.withColumn("application_id",lit(spark_session._sc.applicationId))
    return source_df,target_df,df_missing_rec


def write_dataframe(df,target_bucket,prefix,source_table,file_format,partition_flag):
    current_time = datetime.datetime.now()
    load_dtm = current_time.strftime('%Y-%m-%d-%H-%M').strip()
    if partition_flag == "True":
        
        (
           df
          .withColumn("table_name",lit(source_table))  
          .withColumn("load_date",lit(load_dtm)) 
          .coalesce(1)
          .write
          .partitionBy("table_name","load_date")
          .format(file_format)
          .mode("append")
          .save("s3://" + target_bucket + "/" + prefix + "/")
          )
    else:
        (
           df
          .withColumn("table_name",lit(source_table))  
          .withColumn("load_date",lit(load_dtm)) 
          .coalesce(1)
          .write
          .format(file_format)
          .mode("append")
          .save("s3://" + target_bucket + "/" + prefix + "/")
          )
        
    

def accuracy_summary_validation(source_df,target_df,df_missing_rec,spark_session,column_diff):
    accuracy_summary = [
        {
            "source_count":source_df.count(),
            "target_count":target_df.count(),
            "data_mismatched_records":df_missing_rec.count(),
            "data_mismatch_source":df_missing_rec.filter(col("Data_Mismatch")=="Data Missing Values At Source").count(),
            "data_mismatch_target":df_missing_rec.filter(col("Data_Mismatch")=="Data Missing Values At Target").count(),
            "column_difference":column_diff
        }
    
    ]
    
    recon_df = (spark_session.createDataFrame(accuracy_summary)
                          .withColumn("application_id", lit(spark_session._sc.applicationId))
                          .withColumn("data_matched_records",(col("source_count") - col("data_mismatched_records")))
                          .withColumn("Row_Count_Difference_Percent",abs(round((col("data_mismatched_records")/col("data_matched_records")).cast(DoubleType())*100,2)))
               ).selectExpr(
                        "source_count"
                        ,"target_count"
                        ,"column_difference"
                        ,"case when data_matched_records < 0 then 0 else data_matched_records end as data_matched_records"
                        ,"data_mismatched_records"
                        ,"data_mismatch_source"
                        ,"data_mismatch_target"
                        ,"case when Row_Count_Difference_Percent > 100 then 100 else Row_Count_Difference_Percent end as Row_Count_Difference_Percent"
                        ,"application_id"
                       )
    return recon_df



def compare_source_target_1(source_table,target_table,column_list,filter_condition,spark_session):
    source_df = spark_session.sql(f"select {', '.join(column_list)} from {source_table} where {filter_condition}")
    source_df_1 = source_df.withColumn("hash",hash(*source_df.columns))
    target_df = spark_session.sql(f"select {', '.join(column_list)} from {target_table} where {filter_condition}")
    target_df_1 = target_df.withColumn("hash", hash(*target_df.columns))
    df_missing_rec = (
                        source_df_1.join(target_df_1, on="hash", how="left").filter(target_df_1.hash.isNull()).withColumn("Data_Mismatch",lit("Data Missing Values At Target"))
                        .select(source_df_1["*"],"Data_Mismatch")
                        .union(target_df_1.join(source_df_1, on="hash", how="left").filter(source_df_1.hash.isNull()).withColumn("Data_Mismatch",lit("Data Missing Values At Source"))
                        .select(target_df_1["*"],"Data_Mismatch"))
                    )
    df_missing_rec = df_missing_rec.withColumn("application_id",lit(spark_session._sc.applicationId))
    return source_df,target_df,df_missing_rec





def compare_schemas(source_table,target_table,filter_condition,column_list,spark_session):
    source_schema = spark_session.sql(f"select {', '.join(column_list)} from {source_table} where {filter_condition}").schema
    target_schema = spark_session.sql(f"select {', '.join(column_list)} from {target_table} where {filter_condition}").schema
    diff_fields = []
    if len(source_schema.fields) != len(target_schema.fields):
        diff_fields.append("source_column_count:{0},target_column_count:{1}".format(len(source_schema.fields),len(target_schema.fields)))
    for field1, field2 in zip(source_schema.fields, target_schema.fields):
        schema_diff = ""
        if field1.name != field2.name or field1.dataType != field2.dataType:
            schema_diff = "{s_name}:{s_type} <> {t_name}:{t_type}".format(s_name=field1.name, s_type=field1.dataType, t_name=field2.name, t_type=field2.dataType)
            diff_fields.append(schema_diff)
    return "".join(diff_fields)
