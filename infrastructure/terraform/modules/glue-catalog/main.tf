resource "aws_glue_catalog_database" "analytics" {
  name        = var.database_name
  description = "AWS Glue Data Catalog database for the FII Data & AI Platform analytics layer."
}

resource "aws_glue_catalog_table" "b3_trades" {
  name          = var.b3_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "B3 trades Silver dataset stored as partitioned Parquet files in Amazon S3."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL                    = "TRUE"
    classification              = "parquet"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2026,2035"
    "projection.year.digits"    = "4"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.month.digits"   = "2"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "projection.day.digits"     = "2"
    "storage.location.template" = "s3://${var.data_lake_bucket_name}/silver/b3/year=$${year}/month=$${month}/day=$${day}/"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/silver/b3/"

    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    compressed = false

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"

      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "trade_date"
      type = "timestamp"
    }

    columns {
      name = "ticker"
      type = "string"
    }

    columns {
      name = "instrument_id"
      type = "string"
    }

    columns {
      name = "instrument_id_type"
      type = "string"
    }

    columns {
      name = "market"
      type = "string"
    }

    columns {
      name = "open_price"
      type = "double"
    }

    columns {
      name = "low_price"
      type = "double"
    }

    columns {
      name = "high_price"
      type = "double"
    }

    columns {
      name = "average_price"
      type = "double"
    }

    columns {
      name = "close_price"
      type = "double"
    }

    columns {
      name = "trades_quantity"
      type = "bigint"
    }
  }

  partition_keys {
    name = "year"
    type = "int"
  }

  partition_keys {
    name = "month"
    type = "int"
  }

  partition_keys {
    name = "day"
    type = "int"
  }
}

resource "aws_glue_catalog_table" "cvm_fund_classes" {
  name          = var.cvm_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "CVM fund classes Silver dataset stored as partitioned Parquet files in Amazon S3."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL                    = "TRUE"
    classification              = "parquet"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2026,2035"
    "projection.year.digits"    = "4"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.month.digits"   = "2"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "projection.day.digits"     = "2"
    "storage.location.template" = "s3://${var.data_lake_bucket_name}/silver/cvm/year=$${year}/month=$${month}/day=$${day}/"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/silver/cvm/"

    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    compressed = false

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"

      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "ID_Registro_Fundo"
      type = "string"
    }

    columns {
      name = "ID_Registro_Classe"
      type = "string"
    }

    columns {
      name = "CNPJ_Classe"
      type = "string"
    }

    columns {
      name = "Codigo_CVM"
      type = "string"
    }

    columns {
      name = "Data_Registro"
      type = "timestamp"
    }

    columns {
      name = "Data_Constituicao"
      type = "timestamp"
    }

    columns {
      name = "Data_Inicio"
      type = "timestamp"
    }

    columns {
      name = "Tipo_Classe"
      type = "string"
    }

    columns {
      name = "Denominacao_Social"
      type = "string"
    }

    columns {
      name = "Situacao"
      type = "string"
    }

    columns {
      name = "Data_Inicio_Situacao"
      type = "string"
    }

    columns {
      name = "Classificacao"
      type = "string"
    }

    columns {
      name = "Indicador_Desempenho"
      type = "string"
    }

    columns {
      name = "Classe_Cotas"
      type = "string"
    }

    columns {
      name = "Classificacao_Anbima"
      type = "string"
    }

    columns {
      name = "Tributacao_Longo_Prazo"
      type = "string"
    }

    columns {
      name = "Entidade_Investimento"
      type = "string"
    }

    columns {
      name = "Permitido_Aplicacao_CemPorCento_Exterior"
      type = "string"
    }

    columns {
      name = "Classe_ESG"
      type = "string"
    }

    columns {
      name = "Forma_Condominio"
      type = "string"
    }

    columns {
      name = "Exclusivo"
      type = "string"
    }

    columns {
      name = "Publico_Alvo"
      type = "string"
    }

    columns {
      name = "Patrimonio_Liquido"
      type = "double"
    }

    columns {
      name = "Data_Patrimonio_Liquido"
      type = "timestamp"
    }

    columns {
      name = "CNPJ_Auditor"
      type = "string"
    }

    columns {
      name = "Auditor"
      type = "string"
    }

    columns {
      name = "CNPJ_Custodiante"
      type = "string"
    }

    columns {
      name = "Custodiante"
      type = "string"
    }

    columns {
      name = "CNPJ_Controlador"
      type = "string"
    }

    columns {
      name = "Controlador"
      type = "string"
    }
  }

  partition_keys {
    name = "year"
    type = "int"
  }

  partition_keys {
    name = "month"
    type = "int"
  }

  partition_keys {
    name = "day"
    type = "int"
  }
}