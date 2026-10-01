resource "aws_athena_named_query" "fii_walk_forward_sample" {
  name = "fii_walk_forward_sample"

  description = (
    "Sample query for the Gold ML FII Walk-Forward fold metrics dataset."
  )

  database  = var.database_name
  workgroup = aws_athena_workgroup.analytics.name

  query = <<-SQL
    SELECT
        fold_id,
        model,
        validation_start,
        validation_end,
        train_rows,
        validation_rows,
        mae,
        rmse,
        r2,
        directional_accuracy,
        directional_lift,
        walk_forward_version
    FROM fii_walk_forward
    ORDER BY fold_id, model;
  SQL
}