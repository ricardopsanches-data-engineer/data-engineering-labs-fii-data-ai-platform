variable "fii_ml_eligibility_table_name" {
  description = "AWS Glue table name for the Gold ML FII ML Eligibility dataset."
  type        = string
  default     = "fii_ml_eligibility"
}

resource "aws_glue_catalog_table" "fii_ml_eligibility" {
  name          = var.fii_ml_eligibility_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "Gold ML FII ML Eligibility v3 containing governed supervised-learning eligibility decisions based on FII Features v7 and Price Quality v2."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/gold/ml/fii_ml_eligibility/"

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
      name = "blocking_signal_on_feature_date"
      type = "boolean"
    }

    columns {
      name = "price_quality_review_on_feature_date"
      type = "boolean"
    }

    columns {
      name = "rejected_ca_review_on_feature_date"
      type = "boolean"
    }

    columns {
      name = "blocking_feature_lookback_count"
      type = "bigint"
    }

    columns {
      name = "extreme_feature_lookback_count"
      type = "bigint"
    }

    columns {
      name = "confirmed_ca_feature_lookback_count"
      type = "bigint"
    }

    columns {
      name = "confirmed_economic_ca_feature_lookback_count"
      type = "bigint"
    }

    columns {
      name = "in_kind_ca_feature_lookback_count"
      type = "bigint"
    }

    columns {
      name = "feature_window_clean"
      type = "boolean"
    }

    columns {
      name = "blocking_target_horizon_count"
      type = "bigint"
    }

    columns {
      name = "extreme_target_horizon_count"
      type = "bigint"
    }

    columns {
      name = "price_quality_review_target_count"
      type = "bigint"
    }

    columns {
      name = "rejected_ca_review_target_count"
      type = "bigint"
    }

    columns {
      name = "confirmed_ca_target_count"
      type = "bigint"
    }

    columns {
      name = "confirmed_economic_ca_target_count"
      type = "bigint"
    }

    columns {
      name = "in_kind_ca_target_count"
      type = "bigint"
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
      name = "source_price_quality_source"
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
      name = "eligibility_policy"
      type = "string"
    }

    columns {
      name = "created_at"
      type = "timestamp"
    }
  }
}