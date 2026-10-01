variable "fii_training_dataset_table_name" {
  description = "AWS Glue table name for the Gold ML FII Training Dataset."
  type        = string
  default     = "fii_training_dataset"
}

resource "aws_glue_catalog_table" "fii_training_dataset" {
  name          = var.fii_training_dataset_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "Gold ML FII Training Dataset v4 containing governed supervised-learning samples, features, eligibility metadata, and economic T+5 targets."

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
    "storage.location.template" = "s3://${var.data_lake_bucket_name}/gold/ml/fii_training_dataset/year=$${year}/month=$${month}/"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/gold/ml/fii_training_dataset/"

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
      name = "ticker"
      type = "string"
    }

    columns {
      name = "feature_date"
      type = "timestamp"
    }

    columns {
      name = "target_date"
      type = "timestamp"
    }

    columns {
      name = "feature_global_session_index"
      type = "bigint"
    }

    columns {
      name = "target_global_session_index"
      type = "bigint"
    }

    columns {
      name = "target_horizon"
      type = "bigint"
    }

    columns {
      name = "target_horizon_semantics"
      type = "string"
    }

    columns {
      name = "feature_return_window"
      type = "bigint"
    }

    columns {
      name = "feature_price_lookback_observations"
      type = "bigint"
    }

    columns {
      name = "blocking_feature_lookback_count"
      type = "bigint"
    }

    columns {
      name = "blocking_target_horizon_count"
      type = "bigint"
    }

    columns {
      name = "feature_window_clean"
      type = "boolean"
    }

    columns {
      name = "target_horizon_clean"
      type = "boolean"
    }

    columns {
      name = "ml_eligible"
      type = "boolean"
    }

    columns {
      name = "ml_ineligibility_reason"
      type = "string"
    }

    columns {
      name = "ml_eligibility_version"
      type = "string"
    }

    columns {
      name = "source_feature_version"
      type = "string"
    }

    columns {
      name = "source_price_quality_version"
      type = "string"
    }

    columns {
      name = "eligibility_policy"
      type = "string"
    }

    columns {
      name = "corporate_action_value_semantics_eligibility"
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

    columns {
      name = "economic_curve_at_feature"
      type = "double"
    }

    columns {
      name = "target_price_next_5d"
      type = "double"
    }

    columns {
      name = "target_price_raw"
      type = "double"
    }

    columns {
      name = "economic_curve_at_target"
      type = "double"
    }

    columns {
      name = "target_price_return_next_5d"
      type = "double"
    }

    columns {
      name = "target_price_return_next_5d_pct"
      type = "double"
    }

    columns {
      name = "target_return_next_5d"
      type = "double"
    }

    columns {
      name = "target_return_next_5d_pct"
      type = "double"
    }

    columns {
      name = "target_economic_vs_price_difference"
      type = "double"
    }

    columns {
      name = "target_economic_vs_price_difference_pct"
      type = "double"
    }

    columns {
      name = "target_name"
      type = "string"
    }

    columns {
      name = "target_return_semantics"
      type = "string"
    }

    columns {
      name = "training_dataset_version"
      type = "string"
    }

    columns {
      name = "source_ml_eligibility_version"
      type = "string"
    }

    columns {
      name = "training_sample_policy"
      type = "string"
    }

    columns {
      name = "training_dataset_created_at"
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
}