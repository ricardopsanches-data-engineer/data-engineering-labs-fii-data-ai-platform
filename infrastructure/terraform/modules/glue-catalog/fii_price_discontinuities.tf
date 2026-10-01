variable "fii_price_discontinuities_table_name" {
  description = "AWS Glue table name for the Gold Analytics FII Price Discontinuities dataset."
  type        = string
  default     = "fii_price_discontinuities"
}

resource "aws_glue_catalog_table" "fii_price_discontinuities" {
  name          = var.fii_price_discontinuities_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "Gold Analytics FII Price Discontinuities containing governed discontinuity candidates, review decisions, corporate action metadata, detection thresholds, and governance information."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/gold/analytics/fii_price_discontinuities/"

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
      name = "cnpj"
      type = "string"
    }

    columns {
      name = "codigo_cvm"
      type = "string"
    }

    columns {
      name = "previous_trade_date"
      type = "timestamp"
    }

    columns {
      name = "event_date"
      type = "timestamp"
    }

    columns {
      name = "price_before"
      type = "double"
    }

    columns {
      name = "price_after"
      type = "double"
    }

    columns {
      name = "daily_return"
      type = "double"
    }

    columns {
      name = "daily_return_pct"
      type = "double"
    }

    columns {
      name = "absolute_daily_return"
      type = "double"
    }

    columns {
      name = "observed_factor"
      type = "double"
    }

    columns {
      name = "nearest_common_factor"
      type = "double"
    }

    columns {
      name = "factor_relative_error"
      type = "double"
    }

    columns {
      name = "factor_match"
      type = "boolean"
    }

    columns {
      name = "classification"
      type = "string"
    }

    columns {
      name = "confidence"
      type = "string"
    }

    columns {
      name = "candidate_reason"
      type = "string"
    }

    columns {
      name = "review_status"
      type = "string"
    }

    columns {
      name = "event_type"
      type = "string"
    }

    columns {
      name = "quantity_multiplier"
      type = "double"
    }

    columns {
      name = "price_adjustment_factor"
      type = "double"
    }

    columns {
      name = "cash_amount_per_unit"
      type = "double"
    }

    columns {
      name = "in_kind_amount_per_unit"
      type = "double"
    }

    columns {
      name = "total_economic_value_per_unit"
      type = "double"
    }

    columns {
      name = "in_kind_asset_ticker"
      type = "string"
    }

    columns {
      name = "in_kind_quantity_per_unit"
      type = "double"
    }

    columns {
      name = "corporate_action_record_date"
      type = "timestamp"
    }

    columns {
      name = "corporate_action_effective_date"
      type = "timestamp"
    }

    columns {
      name = "cash_payment_date"
      type = "timestamp"
    }

    columns {
      name = "in_kind_delivery_date"
      type = "timestamp"
    }

    columns {
      name = "first_post_event_trade_date"
      type = "timestamp"
    }

    columns {
      name = "confirmation_source"
      type = "string"
    }

    columns {
      name = "confirmation_date"
      type = "timestamp"
    }

    columns {
      name = "governance_review_date"
      type = "timestamp"
    }

    columns {
      name = "review_notes"
      type = "string"
    }

    columns {
      name = "is_confirmed_corporate_action"
      type = "boolean"
    }

    columns {
      name = "detected_by_v4_threshold"
      type = "boolean"
    }

    columns {
      name = "newly_visible_in_v5_band"
      type = "boolean"
    }

    columns {
      name = "candidate_threshold"
      type = "double"
    }

    columns {
      name = "detection_policy"
      type = "string"
    }

    columns {
      name = "review_policy"
      type = "string"
    }

    columns {
      name = "discontinuity_version"
      type = "string"
    }

    columns {
      name = "discontinuity_source"
      type = "string"
    }

    columns {
      name = "created_at"
      type = "timestamp"
    }
  }
}