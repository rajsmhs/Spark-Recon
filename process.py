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
    load_dtm = current_time.strftime('%Y-%m-%d-%H-%M')
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


def compare_schemas(source_table,filter_condition,column_list,spark_session):
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




def accuracy_summary_validation(source_df,target_df,df_missing_rec,spark_session):
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
                          .withColumn("Row_Count_Difference_Percent",round((col("data_mismatched_records")/col("data_matched_records")).cast(DoubleType())*100,2))
                          .withColumn("match_prcentage",(lit(100)- col("Row_Count_Difference_Percent").cast(DoubleType())))
                
               ).select(
                        "source_count"
                        ,"target_count"
                        ,"data_mismatched_records"
                        ,"data_mismatch_source"
                        ,"data_mismatch_target"
                        ,"Row_Count_Difference_Percent"
                        ,"match_prcentage"
                        ,"application_id"
                       )
    return recon_df
