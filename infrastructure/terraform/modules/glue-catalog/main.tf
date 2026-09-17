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
      name = "id_registro_fundo"
      type = "string"
    }

    columns {
      name = "id_registro_classe"
      type = "string"
    }

    columns {
      name = "cnpj_classe"
      type = "string"
    }

    columns {
      name = "codigo_cvm"
      type = "string"
    }

    columns {
      name = "data_registro"
      type = "timestamp"
    }

    columns {
      name = "data_constituicao"
      type = "timestamp"
    }

    columns {
      name = "data_inicio"
      type = "timestamp"
    }

    columns {
      name = "tipo_classe"
      type = "string"
    }

    columns {
      name = "denominacao_social"
      type = "string"
    }

    columns {
      name = "situacao"
      type = "string"
    }

    columns {
      name = "data_inicio_situacao"
      type = "string"
    }

    columns {
      name = "classificacao"
      type = "string"
    }

    columns {
      name = "indicador_desempenho"
      type = "string"
    }

    columns {
      name = "classe_cotas"
      type = "string"
    }

    columns {
      name = "classificacao_anbima"
      type = "string"
    }

    columns {
      name = "tributacao_longo_prazo"
      type = "string"
    }

    columns {
      name = "entidade_investimento"
      type = "string"
    }

    columns {
      name = "permitido_aplicacao_cemporcento_exterior"
      type = "string"
    }

    columns {
      name = "classe_esg"
      type = "string"
    }

    columns {
      name = "forma_condominio"
      type = "string"
    }

    columns {
      name = "exclusivo"
      type = "string"
    }

    columns {
      name = "publico_alvo"
      type = "string"
    }

    columns {
      name = "patrimonio_liquido"
      type = "double"
    }

    columns {
      name = "data_patrimonio_liquido"
      type = "timestamp"
    }

    columns {
      name = "cnpj_auditor"
      type = "string"
    }

    columns {
      name = "auditor"
      type = "string"
    }

    columns {
      name = "cnpj_custodiante"
      type = "string"
    }

    columns {
      name = "custodiante"
      type = "string"
    }

    columns {
      name = "cnpj_controlador"
      type = "string"
    }

    columns {
      name = "controlador"
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

resource "aws_glue_catalog_table" "fii_master" {
  name          = var.fii_master_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "Gold FII master dataset containing resolved CVM and B3 entity relationships."

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
    "storage.location.template" = "s3://${var.data_lake_bucket_name}/gold/fii-master/year=$${year}/month=$${month}/day=$${day}/"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/gold/fii-master/"

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
      name = "cnpj_classe"
      type = "string"
    }

    columns {
      name = "codigo_cvm"
      type = "string"
    }

    columns {
      name = "denominacao_social"
      type = "string"
    }

    columns {
      name = "situacao_cvm"
      type = "string"
    }

    columns {
      name = "core_name"
      type = "string"
    }

    columns {
      name = "primary_instrument_id"
      type = "string"
    }

    columns {
      name = "ticker"
      type = "string"
    }

    columns {
      name = "isin"
      type = "string"
    }

    columns {
      name = "instrument_id_type"
      type = "string"
    }

    columns {
      name = "listing_market"
      type = "string"
    }

    columns {
      name = "asset"
      type = "string"
    }

    columns {
      name = "corporate_name"
      type = "string"
    }

    columns {
      name = "resolution_method"
      type = "string"
    }

    columns {
      name = "resolution_status"
      type = "string"
    }

    columns {
      name = "resolution_evidence"
      type = "string"
    }

    columns {
      name = "reference_date"
      type = "timestamp"
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

resource "aws_glue_catalog_table" "b3_instruments" {
  name          = var.b3_instruments_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "B3 Instruments Silver dataset stored as partitioned Parquet files in Amazon S3."

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
    "storage.location.template" = "s3://${var.data_lake_bucket_name}/silver/b3-instruments/year=$${year}/month=$${month}/day=$${day}/"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/silver/b3-instruments/"

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
      name = "report_date"
      type = "timestamp"
    }

    columns {
      name = "update_type"
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
      name = "listing_market"
      type = "string"
    }

    columns {
      name = "asset"
      type = "string"
    }

    columns {
      name = "asset_description"
      type = "string"
    }

    columns {
      name = "b3_market"
      type = "string"
    }

    columns {
      name = "b3_segment"
      type = "string"
    }

    columns {
      name = "instrument_description"
      type = "string"
    }

    columns {
      name = "instrument_type"
      type = "string"
    }

    columns {
      name = "security_category"
      type = "string"
    }

    columns {
      name = "ticker"
      type = "string"
    }

    columns {
      name = "isin"
      type = "string"
    }

    columns {
      name = "distribution_id"
      type = "string"
    }

    columns {
      name = "cfi_code"
      type = "string"
    }

    columns {
      name = "specification_code"
      type = "string"
    }

    columns {
      name = "corporate_name"
      type = "string"
    }

    columns {
      name = "payment_type"
      type = "string"
    }

    columns {
      name = "round_lot"
      type = "double"
    }

    columns {
      name = "price_factor"
      type = "double"
    }

    columns {
      name = "trading_start_date"
      type = "timestamp"
    }

    columns {
      name = "trading_end_date"
      type = "timestamp"
    }

    columns {
      name = "corporate_action_start_date"
      type = "timestamp"
    }

    columns {
      name = "ex_distribution_number"
      type = "string"
    }

    columns {
      name = "custody_treatment_type"
      type = "string"
    }

    columns {
      name = "trading_currency"
      type = "string"
    }

    columns {
      name = "market_capitalization"
      type = "double"
    }

    columns {
      name = "last_price"
      type = "double"
    }

    columns {
      name = "first_price"
      type = "double"
    }

    columns {
      name = "settlement_days"
      type = "double"
    }

    columns {
      name = "rights_issue_price"
      type = "double"
    }

    columns {
      name = "underlying_instrument_id"
      type = "string"
    }

    columns {
      name = "underlying_instrument_id_type"
      type = "string"
    }

    columns {
      name = "underlying_market"
      type = "string"
    }

    columns {
      name = "source_xml"
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