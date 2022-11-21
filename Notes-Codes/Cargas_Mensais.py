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

# MAGIC %md
# MAGIC 1 - Doencas_preexistentes

# COMMAND ----------

#1 - Doencas_preexistentes
dataset = "microdados_dos_casos"
control_path = f"{raw}/{dataset}"
control_select_file = readControlFile(dataset, control_path)

process_date_value = control_select_file.collect()[0][0]
uuid_value = control_select_file.collect()[0][1]

data_file = f"{control_path}/{process_date_value}/{uuid_value}/{dataset}.csv"
microdadosDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)

cleanDF = microdadosDF.withColumn("condition", f.when((f.col("asma") == "IGNORADO") & (f.col("cardiopatia") == "IGNORADO") & 
   (f.col("doenca_hepatica") == "IGNORADO") & (f.col("doenca_neurologica") == "IGNORADO") & (f.col("doenca_renal") == "IGNORADO") & 
   (f.col("imunodepressao") == "IGNORADO") & (f.col("obesidade") == "IGNORADO") & (f.col("outros_fatores_de_risco") == "IGNORADO") & 
   (f.col("pneumopatia") == "IGNORADO") & (f.col("puerpera") == "IGNORADO") & (f.col("sindrome_de_Down") == "IGNORADO") & 
   (f.col("diabetes") == "IGNORADO")  & (f.col("doenca_hematologica") == "IGNORADO"), "false")
.otherwise("true"))

cleanDF = cleanDF.filter(f.col("condition") == "true")

cleanDF.repartition(1).write \
  .format('com.databricks.spark.csv') \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ",") \
  .save(f"{analytics}/clean_microdados/{process_date_value}") \



# COMMAND ----------

# MAGIC %md
# MAGIC 2 - casos_confirmados_covid19_ocupacao_profissional_de_saude

# COMMAND ----------

#2 - casos_confirmados_covid19_ocupacao_profissional_de_saude
dataset = "casos_confirmados_covid19_ocupacao_profissional_de_saude"
control_path = f"{raw}/{dataset}"
control_select_file = readControlFile(dataset, control_path)

process_date_value = control_select_file.collect()[0][0]
uuid_value = control_select_file.collect()[0][1]

data_file = f"{control_path}/{process_date_value}/{uuid_value}/{dataset}.csv"
prsaudeDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)

prsaudeDF = prsaudeDF.withColumnRenamed("Número de casos confirmados COVID-19", "casos_confirmados_COVID-19") \
                                        .drop("Código CBO") \
                                          .sort(f.col("Número de casos confirmados COVID-19").desc())

prsaudeDF.repartition(1).write \
  .format('com.databricks.spark.csv') \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/profissionais_casos_confirmados/{process_date_value}") \

# COMMAND ----------

# MAGIC %md
# MAGIC 3 - etnias_indigenas

# COMMAND ----------

#3 - etnias_indigenas
dataset = "etnias_indigenas"
control_path = f"{raw}/{dataset}"
control_select_file = readControlFile(dataset, control_path)

process_date_value = control_select_file.collect()[0][0]
uuid_value = control_select_file.collect()[0][1]

data_file = f"{control_path}/{process_date_value}/{uuid_value}/{dataset}.csv"

indigenasDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)

indigenasDF = indigenasDF.withColumnRenamed("Municipio", "Municipio") \
      .withColumnRenamed("Número de casos confirmados", "Total_Casos_Confirmados") \
      .withColumn("data_execucao", f.current_date())

indigenasDF.repartition(1).write \
  .format('com.databricks.spark.csv') \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/etnias_indigenas/{process_date_value}")

# COMMAND ----------

# MAGIC %md
# MAGIC 4 - casos_obitos_raca_cor

# COMMAND ----------

#4 - casos_obitos_raca_cor
dataset = "pacientes_internados_por_SRAG"
control_path = f"{raw}/{dataset}"
control_select_file = readControlFile(dataset, control_path)

process_date_value = control_select_file.collect()[0][0]
uuid_value = control_select_file.collect()[0][1]

data_file = f"{control_path}/{process_date_value}/{uuid_value}/{dataset}.csv"
SRAGDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)

SRAGDF.createOrReplaceTempView("table")

curadosDF = SRAGDF.filter(f.col("obito") == "false") \
                        .groupBy("nome_munic", "nome_drs","idade", "raca_cor", "cs_sexo", "diagnostico_covid19").count() \
                         .withColumnRenamed("count", "Total_Curados") \
                         .sort(f.col("idade").desc())

obitosDF = SRAGDF.filter(f.col("obito") == "true") \
                        .groupBy("nome_munic", "nome_drs","idade", "raca_cor", "cs_sexo", "diagnostico_covid19").count() \
                         .withColumnRenamed("count", "Total_Obitos") \
                         .sort(f.col("idade").desc())                         

obitosDF.repartition(1).write \
  .format('com.databricks.spark.csv') \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/total_obitos/{process_date_value}")

curadosDF.repartition(1).write \
  .format('com.databricks.spark.csv') \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/total_curados/{process_date_value}")

# COMMAND ----------

# MAGIC %md
# MAGIC 5 - placar_testes

# COMMAND ----------

#5 - placar_testes 
dataset = "placar_testes"
control_path = f"{raw}/{dataset}"
control_select_file = readControlFile(dataset, control_path)

process_date_value = control_select_file.collect()[0][0]
uuid_value = control_select_file.collect()[0][1]

data_file = f"{control_path}/{process_date_value}/{uuid_value}/{dataset}.csv"
testagemDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)

testagemDF = testagemDF.withColumnRenamed("Mês de Data coleta", "Data_Coleta") \
                  .withColumnRenamed("Tipo teste", "Tipo_Teste") \
                  .withColumnRenamed("Qtde", "Quantidade") \
                  .withColumn("Data_Coleta", f.to_date(f.col("Data_Coleta"), "dd/MM/yyyy").cast("Date")) \

testagemDF.repartition(1).write \
  .format('com.databricks.spark.csv') \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/total_curados/{process_date_value}")

