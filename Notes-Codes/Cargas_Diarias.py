# Databricks notebook source
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql import functions as f

storage_account_name = "estudodecasolake"
storage_key = "V0zy5lIezU8qpC6b/a1xc9LfD1qPVzXLw8TsxD+4EvvkbsLCQokmDK6U1oKKh3W4iLC3iLj9ofyW+AStJt413Q=="

spark.conf.set(f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net", storage_key)

raw = f"abfss://raw@{storage_account_name}.dfs.core.windows.net"
bronze = f"abfss://bronze@{storage_account_name}.dfs.core.windows.net"


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
# MAGIC 1 - casos_e_obtos_por_municipio_e_data

# COMMAND ----------

#1 - casos_e_obtos_por_municipio_e_data
dataset = "casos_e_obtos_por_municipio_e_data"
control_path = f"{raw}/{dataset}"
control_select_file = readControlFile(dataset, control_path)

#display(control_select_file)

process_date_value = control_select_file.collect()[0][0]
uuid_value = control_select_file.collect()[0][1]

data_file = f"{control_path}/{process_date_value}/{uuid_value}/{dataset}.csv"

casos_obtosDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)

cleanDF = casos_obtosDF.filter(f.col("nome_munic") != "Ignorado")

cleanDF.coalesce(1).write \
  .format("csv") \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/clean_casos_obitos/{process_date_value}") \

cleanDF.createOrReplaceTempView("clean_table")

#Criar uma sample somente com cidades e codigo_ibge
cidades_codigoDF = spark.sql("""
  SELECT DISTINCT nome_munic, codigo_ibge
  FROM clean_table
  ORDER BY nome_munic
""")

cidades_codigoDF.coalesce(1).write \
  .format("csv") \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/cidades_codigo/{process_date_value}") \

#Cidades sem casos novos
noCasesDF = spark.sql("""
  SELECT nome_munic, COUNT(casos_novos) AS dias_sem_casos_novos
  FROM clean_table 
   WHERE casos_novos == 0
   GROUP BY nome_munic
   ORDER BY dias_sem_casos_novos DESC
""")

noCasesDF.coalesce(1).write \
  .format("csv") \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/sem_casos_novos/{process_date_value}")

# COMMAND ----------

# MAGIC %md
# MAGIC 2 - leitos_internações_por_diretoria_regionaldesaude

# COMMAND ----------

#2 - leitos_internações_por_diretoria_regionaldesaude
dataset = "leitos_internações_por_diretoria_regionaldesaude"
control_path = f"{raw}/{dataset}"
control_select_file = readControlFile(dataset, control_path)

process_date_value = control_select_file.collect()[0][0]
uuid_value = control_select_file.collect()[0][1]

data_file = f"{control_path}/{process_date_value}/{uuid_value}/{dataset}.csv"

leitosDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)

leitosDF = leitosDF.withColumn("datahora", f.to_date(f.col("datahora"), "yyyy-MM-dd").cast("Date"))

leitosDF.printSchema()

windowDept = Window.partitionBy("nome_drs").orderBy(f.col("datahora").desc())

leitos_dataatual = leitosDF.withColumn("row",f.row_number().over(windowDept)) \
  .filter(f.col("row") == 1).drop("row") \

leitos_dataatual.coalesce(1).write \
  .format('com.databricks.spark.csv') \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/last_date_leitos/{process_date_value}")



# COMMAND ----------

# MAGIC %md
# MAGIC 3 - Ranking Vacinação

# COMMAND ----------

#3 - Ranking Vacinação
dataset = "ranking_vacinação"
control_path = f"{raw}/{dataset}"
control_select_file = readControlFile(dataset, control_path)

process_date_value = control_select_file.collect()[0][0]
uuid_value = control_select_file.collect()[0][1]

data_file = f"{control_path}/{process_date_value}/{uuid_value}/{dataset}.csv"

rankingvacinaDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)

vacinometroDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)


rankingvacinaDF = rankingvacinaDF.withColumnRenamed("Municipio ", "Cidade") \
                                        .withColumnRenamed("Rank of % em relação a população geral", "Rank_em_relacao_populacao_geral") \
                                          .withColumnRenamed("PRIMEIRA DOSE", "Dose_1") \
                                           .withColumnRenamed("POPULAÇÃO MUNICÍPIO 2020", "Populacao_senso_2020") \
                                            .withColumnRenamed("% em relação a população geral", "Porcentagem_aplicação_Dose_1") \
                                             .drop("Grand Total")

rankingvacinaDF.repartition(1).write \
  .format('com.databricks.spark.csv') \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/aplicacao_doses/{process_date_value}")

# COMMAND ----------

# MAGIC %md
# MAGIC 4 - Estatisticas Gerais

# COMMAND ----------

#4 - Estatisticas Gerais
geralDF = spark.read \
      .option("header", "true") \
      .option("sep", ";") \
      .option("InferSchema", "true") \
      .csv(data_file)

geralDF = geralDF.withColumnRenamed("Imunobiologico ", "VACINA") \
                              .withColumnRenamed("1º DOSE", "DOSE_1") \
                              .withColumnRenamed("2° DOSE", "DOSE_2") \
                              .withColumnRenamed("UNICA", "Dose_Unica") \
                              .withColumnRenamed("1º DOSE ADICIONAL", "DOSE_ADICIONAL_1") \
                              .withColumnRenamed("2 REFORCO", "DOSE_REFORCO_2") \
                              .withColumnRenamed("3 REFORCO", "DOSE_REFORCO_3") \
                              .withColumnRenamed("4 REFORCO", "DOSE_REFORCO_4") \
                              .withColumnRenamed("REFORCO FORA DO ESQUEMA VACINAL", "REFORCO_FORA_DO_ESQUEMA_VACINAL") \

geralDF.coalesce(1).write \
  .format('com.databricks.spark.csv') \
  .option("header", "true") \
  .option("overwriteSchema", "true") \
  .mode('overwrite') \
  .option("delimiter", ";") \
  .save(f"{analytics}/estaticas_gerais_clean/{process_date_value}")

