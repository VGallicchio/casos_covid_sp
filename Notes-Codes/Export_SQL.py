# Databricks notebook source
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql import functions as f

storage_account_name = "estudodecasolake"
storage_key = "V0zy5lIezU8qpC6b/a1xc9LfD1qPVzXLw8TsxD+4EvvkbsLCQokmDK6U1oKKh3W4iLC3iLj9ofyW+AStJt413Q=="

spark.conf.set(f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net", storage_key)

raw = f"abfss://raw@{storage_account_name}.dfs.core.windows.net"
analytics = f"abfss://bronze@{storage_account_name}.dfs.core.windows.net"


# COMMAND ----------

def readControlFile(dataset, control_path):
    control_schema = StructType([
      StructField("process_date", StringType(), True),
      StructField("uuid", StringType(), True),
    ])

    path_control_file = f"{control_path}/Control_file_{dataset}.txt"
    print("Reading control file at: " + path_control_file)

    control_csv_file = spark.read \
      .option("header", "false") \
      .option("sep", "|") \
      .schema(control_schema) \
      .csv(path_control_file) \

    #Selecting Values
    control_select_file = control_csv_file.select("process_date", "uuid")

    return control_select_file

# COMMAND ----------

def readCSV(camada, dataset, process_date):
    df = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(f"{camada}/{dataset}/{process_date}")

    return df

# COMMAND ----------

def writetoTable(df, mode, table):
    df.write.format("jdbc") \
        .mode(mode) \
        .option("url", sqlsUrl) \
        .option("dbtable", table) \
        .option("user", user) \
        .option("password", pwd) \
        .save()

# COMMAND ----------

from pyspark.sql import SparkSession

spark = SparkSession\
    .builder\
    .master('local[*]')\
    .appName('Connection-Test')\
    .config('spark.driver.extraClassPath', '/sqljdbc_10.2/enu/mssql-jdbc-10.2.1.jre11.jar')\
    .config('spark.executor.extraClassPath', '/sqljdbc_10.2/enu/mssql-jdbc-10.2.1.jre11.jar')\
    .getOrCreate()


#Data a ser processada
#process_date_value = " "

#parametros conexão
sqlsUrl = 'jdbc:sqlserver://localhost:1433;database=estudodecaso;encrypt=true;trustServerCertificate=true;'
user = "_"
pwd = "_"

raca_cor = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(f"data/raw/pacientes_internados_por_SRAG/20221103/933dc255-4e61-40d1-aef5-a7069548db5a/pacientes_internados_por_SRAG.csv")

writetoTable(raca_cor, "overwrite", "tb_raca_cor")

aplicacao_dosesDF = readCSV(analytics, "aplicacao_doses", process_date_value)
cidades_codigoDF = readCSV(analytics, "cidades_codigo", process_date_value)
clean_casos_obitosDF = readCSV(analytics, "clean_casos_obitos", process_date_value)
estaticas_gerais_cleanDF = readCSV(analytics, "estaticas_gerais_clean", process_date_value)
last_date_leitosDF = readCSV(analytics, "last_date_leitos", process_date_value)
sem_casos_novosDF = readCSV(analytics, "sem_casos_novos", process_date_value)

clean_microdadosDF = readCSV(analytics, "clean_microdados", process_date_value)
etnias_indigenasDF = readCSV(analytics, "etnias_indigenas", process_date_value)
profissionais_casos_confirmadosDF = readCSV(analytics, "profissionais_casos_confirmados", process_date_value)
total_curadosDF = readCSV(analytics, "total_curados", process_date_value)
total_obitosDF = readCSV(analytics, "total_obitos", process_date_value)

Write Tables
writetoTable(aplicacao_dosesDF, "overwrite", "tb_aplicacao_doses")
writetoTable(cidades_codigoDF, "overwrite", "tb_cidades_codigo")
writetoTable(clean_casos_obitosDF, "overwrite", "tb_clean_casos_obitos")
writetoTable(estaticas_gerais_cleanDF, "overwrite", "tb_estaticas_gerais_clean")
writetoTable(last_date_leitosDF, "overwrite", "tb_last_date_leitos")
writetoTable(sem_casos_novosDF, "overwrite", "tb_sem_casos_novos")

writetoTable(clean_microdadosDF, "overwrite", "tb_clean_microdados")
writetoTable(etnias_indigenasDF, "append", "tb_etnias_indigenas")
writetoTable(profissionais_casos_confirmadosDF, "overwrite", "tb_profissionais_casos_confirmados")
writetoTable(total_curadosDF, "overwrite", "tb_total_curados")
writetoTable(total_obitosDF, "overwrite", "tb_total_obitos")


