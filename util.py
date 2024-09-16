from pyspark.sql import SparkSession


def get_spark_session(app_name):
    spark = SparkSession. \
            builder. \
            master('yarn'). \
            appName(app_name). \
            enableHiveSupport(). \
            getOrCreate()
    return spark
