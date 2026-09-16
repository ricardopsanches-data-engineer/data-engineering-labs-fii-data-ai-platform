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