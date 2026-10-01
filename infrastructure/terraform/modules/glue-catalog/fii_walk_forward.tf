variable "fii_walk_forward_table_name" {
  description = "AWS Glue table name for the Gold ML FII Walk-Forward fold metrics dataset."
  type        = string
  default     = "fii_walk_forward"
}

resource "aws_glue_catalog_table" "fii_walk_forward" {
  name          = var.fii_walk_forward_table_name
  database_name = aws_glue_catalog_database.analytics.name

  description = "Gold ML FII Walk-Forward v1 fold-level evaluation metrics using expanding-window purged validation with the final TEST holdout protected."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location = "s3://${var.data_lake_bucket_name}/gold/ml/fii_walk_forward/fold_metrics/"

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
      name = "walk_forward_version"
      type = "string"
    }

    columns {
      name = "fold_id"
      type = "bigint"
    }

    columns {
      name = "model"
      type = "string"
    }

    columns {
      name = "validation_feature_sessions"
      type = "bigint"
    }

    columns {
      name = "train_start"
      type = "timestamp"
    }

    columns {
      name = "train_end"
      type = "timestamp"
    }

    columns {
      name = "train_target_max"
      type = "timestamp"
    }

    columns {
      name = "validation_start"
      type = "timestamp"
    }

    columns {
      name = "validation_end"
      type = "timestamp"
    }

    columns {
      name = "validation_target_min"
      type = "timestamp"
    }

    columns {
      name = "validation_target_max"
      type = "timestamp"
    }

    columns {
      name = "train_rows"
      type = "bigint"
    }

    columns {
      name = "validation_rows"
      type = "bigint"
    }

    columns {
      name = "train_tickers"
      type = "bigint"
    }

    columns {
      name = "validation_tickers"
      type = "bigint"
    }

    columns {
      name = "train_feature_dates"
      type = "bigint"
    }

    columns {
      name = "validation_feature_dates"
      type = "bigint"
    }

    columns {
      name = "train_nan_count"
      type = "bigint"
    }

    columns {
      name = "validation_nan_count"
      type = "bigint"
    }

    columns {
      name = "train_target_mean"
      type = "double"
    }

    columns {
      name = "train_target_median"
      type = "double"
    }

    columns {
      name = "train_positive_share"
      type = "double"
    }

    columns {
      name = "validation_target_mean"
      type = "double"
    }

    columns {
      name = "validation_target_median"
      type = "double"
    }

    columns {
      name = "validation_positive_share"
      type = "double"
    }

    columns {
      name = "majority_direction"
      type = "string"
    }

    columns {
      name = "majority_directional_accuracy"
      type = "double"
    }

    columns {
      name = "mae"
      type = "double"
    }

    columns {
      name = "rmse"
      type = "double"
    }

    columns {
      name = "r2"
      type = "double"
    }

    columns {
      name = "directional_accuracy"
      type = "double"
    }

    columns {
      name = "directional_lift"
      type = "double"
    }

    columns {
      name = "prediction_mean"
      type = "double"
    }

    columns {
      name = "prediction_median"
      type = "double"
    }

    columns {
      name = "prediction_min"
      type = "double"
    }

    columns {
      name = "prediction_max"
      type = "double"
    }
  }
}