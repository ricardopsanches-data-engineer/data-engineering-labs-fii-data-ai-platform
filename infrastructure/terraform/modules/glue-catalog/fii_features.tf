variable "fii_features_table_name" {
  description = "AWS Glue table name for the Gold ML FII Features dataset."
  type        = string
  default     = "fii_features"
}

resource "aws_glue_catalog_table" "fii_features" {
  name          = var.fii_features_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "Gold ML FII Features containing time-series features derived from the governed FII Price History dataset."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL                    = "TRUE"
    classification              = "parquet"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2025,2035"
    "projection.year.digits"    = "4"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.month.digits"   = "2"
    "storage.location.template" = "s3://${var.data_lake_bucket_name}/gold/ml/fii_features/year=$${year}/month=$${month}/"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/gold/ml/fii_features/"

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
      name = "feature_date"
      type = "timestamp"
    }

    columns {
      name = "ticker"
      type = "string"
    }

    columns {
      name = "cnpj"
      type = "string"
    }

    columns {
      name = "codigo_cvm"
      type = "string"
    }

    columns {
      name = "close_price"
      type = "double"
    }

    columns {
      name = "close_price_raw"
      type = "double"
    }

    columns {
      name = "close_price_adjusted"
      type = "double"
    }

    columns {
      name = "trades_quantity"
      type = "bigint"
    }

    columns {
      name = "daily_return"
      type = "double"
    }

    columns {
      name = "daily_return_raw"
      type = "double"
    }

    columns {
      name = "daily_return_economic"
      type = "double"
    }

    columns {
      name = "daily_return_pct"
      type = "double"
    }

    columns {
      name = "observations_count"
      type = "bigint"
    }

    columns {
      name = "return_5d"
      type = "double"
    }

    columns {
      name = "return_5d_pct"
      type = "double"
    }

    columns {
      name = "ma_5"
      type = "double"
    }

    columns {
      name = "volatility_5d"
      type = "double"
    }

    columns {
      name = "volatility_5d_pct"
      type = "double"
    }

    columns {
      name = "trades_avg_5d"
      type = "double"
    }

    columns {
      name = "price_to_ma5"
      type = "double"
    }

    columns {
      name = "return_10d"
      type = "double"
    }

    columns {
      name = "return_10d_pct"
      type = "double"
    }

    columns {
      name = "ma_10"
      type = "double"
    }

    columns {
      name = "volatility_10d"
      type = "double"
    }

    columns {
      name = "volatility_10d_pct"
      type = "double"
    }

    columns {
      name = "trades_avg_10d"
      type = "double"
    }

    columns {
      name = "price_to_ma10"
      type = "double"
    }

    columns {
      name = "return_20d"
      type = "double"
    }

    columns {
      name = "return_20d_pct"
      type = "double"
    }

    columns {
      name = "ma_20"
      type = "double"
    }

    columns {
      name = "volatility_20d"
      type = "double"
    }

    columns {
      name = "volatility_20d_pct"
      type = "double"
    }

    columns {
      name = "trades_avg_20d"
      type = "double"
    }

    columns {
      name = "price_to_ma20"
      type = "double"
    }

    columns {
      name = "return_spread_5d_10d"
      type = "double"
    }

    columns {
      name = "ma_ratio_5_10"
      type = "double"
    }

    columns {
      name = "volatility_ratio_5d_10d"
      type = "double"
    }

    columns {
      name = "trades_ratio_5d_10d"
      type = "double"
    }

    columns {
      name = "return_spread_10d_20d"
      type = "double"
    }

    columns {
      name = "ma_ratio_10_20"
      type = "double"
    }

    columns {
      name = "volatility_ratio_10d_20d"
      type = "double"
    }

    columns {
      name = "trades_ratio_10d_20d"
      type = "double"
    }

    columns {
      name = "feature_ready"
      type = "boolean"
    }

    columns {
      name = "features_created_at"
      type = "timestamp"
    }

    columns {
      name = "feature_version"
      type = "string"
    }

    columns {
      name = "feature_windows"
      type = "string"
    }

    columns {
      name = "source_price_history_version"
      type = "string"
    }

    columns {
      name = "source_price_history_source"
      type = "string"
    }

    columns {
      name = "price_semantics"
      type = "string"
    }

    columns {
      name = "return_semantics"
      type = "string"
    }

    columns {
      name = "corporate_action_value_semantics"
      type = "string"
    }

    columns {
      name = "feature_price_semantics"
      type = "string"
    }

    columns {
      name = "feature_return_semantics"
      type = "string"
    }

    columns {
      name = "feature_corporate_action_policy"
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
}