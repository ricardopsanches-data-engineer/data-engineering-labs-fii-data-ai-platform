variable "fii_daily_snapshot_table_name" {
  description = "AWS Glue table name for the Gold Analytics FII Daily Snapshot dataset."
  type        = string
  default     = "fii_daily_snapshot"
}

resource "aws_glue_catalog_table" "fii_daily_snapshot" {
  name          = var.fii_daily_snapshot_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "Gold Analytics daily snapshot containing consolidated FII identity, market prices, and analytical metrics."

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
    "storage.location.template" = "s3://${var.data_lake_bucket_name}/gold/analytics/fii_daily_snapshot/year=$${year}/month=$${month}/day=$${day}/"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/gold/analytics/fii_daily_snapshot/"

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
      name = "denominacao_social"
      type = "string"
    }

    columns {
      name = "situacao_cvm"
      type = "string"
    }

    columns {
      name = "instrument_id"
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

    columns {
      name = "intraday_variation"
      type = "double"
    }

    columns {
      name = "intraday_variation_pct"
      type = "double"
    }

    columns {
      name = "price_range"
      type = "double"
    }

    columns {
      name = "price_range_pct"
      type = "double"
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
      name = "gold_created_at"
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