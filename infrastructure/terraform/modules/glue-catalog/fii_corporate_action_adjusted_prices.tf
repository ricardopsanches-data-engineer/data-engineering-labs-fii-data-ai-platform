variable "fii_corporate_action_adjusted_prices_table_name" {
  description = "AWS Glue table name for the Gold Analytics Corporate Action Adjusted Prices dataset."
  type        = string
  default     = "fii_corporate_action_adjusted_prices"
}

resource "aws_glue_catalog_table" "fii_corporate_action_adjusted_prices" {
  name          = var.fii_corporate_action_adjusted_prices_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "Gold Analytics Corporate Action Adjusted Prices containing raw and adjusted prices, economic return components, corporate action governance, and market evidence."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL                    = "TRUE"
    classification              = "parquet"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2025,2035"
    "projection.year.digits"    = "4"
    "storage.location.template" = "s3://${var.data_lake_bucket_name}/gold/analytics/fii_corporate_action_adjusted_prices/year=$${year}/"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/gold/analytics/fii_corporate_action_adjusted_prices/"

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
      name = "cnpj"
      type = "string"
    }

    columns {
      name = "codigo_cvm"
      type = "string"
    }

    columns {
      name = "instrument_id"
      type = "string"
    }

    columns {
      name = "open_price_raw"
      type = "double"
    }

    columns {
      name = "low_price_raw"
      type = "double"
    }

    columns {
      name = "high_price_raw"
      type = "double"
    }

    columns {
      name = "average_price_raw"
      type = "double"
    }

    columns {
      name = "close_price_raw"
      type = "double"
    }

    columns {
      name = "structural_adjustment_factor"
      type = "double"
    }

    columns {
      name = "open_price_adjusted"
      type = "double"
    }

    columns {
      name = "low_price_adjusted"
      type = "double"
    }

    columns {
      name = "high_price_adjusted"
      type = "double"
    }

    columns {
      name = "average_price_adjusted"
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
      name = "cash_amount_per_unit_raw"
      type = "double"
    }

    columns {
      name = "cash_amount_per_unit_adjusted"
      type = "double"
    }

    columns {
      name = "in_kind_amount_per_unit_raw"
      type = "double"
    }

    columns {
      name = "in_kind_amount_per_unit_adjusted"
      type = "double"
    }

    columns {
      name = "corporate_action_value_per_unit_raw"
      type = "double"
    }

    columns {
      name = "corporate_action_value_per_unit_adjusted"
      type = "double"
    }

    columns {
      name = "cash_flow_per_unit_raw"
      type = "double"
    }

    columns {
      name = "cash_flow_per_unit_adjusted"
      type = "double"
    }

    columns {
      name = "previous_close_price_raw"
      type = "double"
    }

    columns {
      name = "previous_close_price_adjusted"
      type = "double"
    }

    columns {
      name = "daily_return_raw"
      type = "double"
    }

    columns {
      name = "daily_return_adjusted_price"
      type = "double"
    }

    columns {
      name = "daily_return_economic"
      type = "double"
    }

    columns {
      name = "review_status_on_date"
      type = "string"
    }

    columns {
      name = "event_type_on_date"
      type = "string"
    }

    columns {
      name = "discontinuity_confidence_on_date"
      type = "string"
    }

    columns {
      name = "confirmed_action_on_date"
      type = "boolean"
    }

    columns {
      name = "pending_review_on_date"
      type = "boolean"
    }

    columns {
      name = "confirmed_event_type"
      type = "string"
    }

    columns {
      name = "confirmed_quantity_multiplier"
      type = "double"
    }

    columns {
      name = "confirmed_price_adjustment_factor"
      type = "double"
    }

    columns {
      name = "confirmed_cash_amount_per_unit"
      type = "double"
    }

    columns {
      name = "confirmed_in_kind_amount_per_unit"
      type = "double"
    }

    columns {
      name = "confirmed_total_economic_value_per_unit"
      type = "double"
    }

    columns {
      name = "confirmed_in_kind_asset_ticker"
      type = "string"
    }

    columns {
      name = "confirmed_in_kind_quantity_per_unit"
      type = "double"
    }

    columns {
      name = "confirmed_corporate_action_record_date"
      type = "timestamp"
    }

    columns {
      name = "confirmed_corporate_action_effective_date"
      type = "timestamp"
    }

    columns {
      name = "confirmed_cash_payment_date"
      type = "timestamp"
    }

    columns {
      name = "confirmed_in_kind_delivery_date"
      type = "timestamp"
    }

    columns {
      name = "confirmed_first_post_event_trade_date"
      type = "timestamp"
    }

    columns {
      name = "confirmed_action_source"
      type = "string"
    }

    columns {
      name = "confirmed_action_confirmation_date"
      type = "timestamp"
    }

    columns {
      name = "confirmed_governance_review_date"
      type = "timestamp"
    }

    columns {
      name = "ticker_resolution_status"
      type = "string"
    }

    columns {
      name = "market_evidence_confidence"
      type = "string"
    }

    columns {
      name = "adjusted_prices_version"
      type = "string"
    }

    columns {
      name = "adjusted_prices_source"
      type = "string"
    }

    columns {
      name = "corporate_action_source"
      type = "string"
    }

    columns {
      name = "created_at"
      type = "timestamp"
    }
  }

  partition_keys {
    name = "year"
    type = "int"
  }
}