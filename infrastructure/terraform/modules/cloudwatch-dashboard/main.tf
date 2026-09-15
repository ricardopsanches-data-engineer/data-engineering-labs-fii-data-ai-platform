resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = var.dashboard_name

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          title  = "Daily Ingestion - Invocations"
          region = var.aws_region
          view   = "timeSeries"
          stat   = "Sum"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Invocations",
              "FunctionName",
              var.ingestion_lambda_function_name
            ]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          title  = "Daily Ingestion - Errors and Throttles"
          region = var.aws_region
          view   = "timeSeries"
          stat   = "Sum"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Errors",
              "FunctionName",
              var.ingestion_lambda_function_name
            ],
            [
              ".",
              "Throttles",
              ".",
              "."
            ]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          title  = "Daily Ingestion - Duration"
          region = var.aws_region
          view   = "timeSeries"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Duration",
              "FunctionName",
              var.ingestion_lambda_function_name,
              {
                stat  = "Average"
                label = "Average"
              }
            ],
            [
              "...",
              {
                stat  = "Maximum"
                label = "Maximum"
              }
            ]
          ]

          yAxis = {
            left = {
              label     = "Milliseconds"
              showUnits = false
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          title  = "Daily Ingestion - Error Rate"
          region = var.aws_region
          view   = "timeSeries"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Errors",
              "FunctionName",
              var.ingestion_lambda_function_name,
              {
                id      = "ingestion_errors"
                visible = false
                stat    = "Sum"
              }
            ],
            [
              ".",
              "Invocations",
              ".",
              ".",
              {
                id      = "ingestion_invocations"
                visible = false
                stat    = "Sum"
              }
            ],
            [
              {
                expression = "IF(ingestion_invocations>0,(ingestion_errors/ingestion_invocations)*100,0)"
                label      = "Error Rate"
                id         = "ingestion_error_rate"
              }
            ]
          ]

          yAxis = {
            left = {
              min   = 0
              label = "Percent"
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          title  = "B3 RAW to Silver - Invocations"
          region = var.aws_region
          view   = "timeSeries"
          stat   = "Sum"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Invocations",
              "FunctionName",
              var.b3_silver_lambda_function_name
            ]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6

        properties = {
          title  = "B3 RAW to Silver - Errors and Throttles"
          region = var.aws_region
          view   = "timeSeries"
          stat   = "Sum"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Errors",
              "FunctionName",
              var.b3_silver_lambda_function_name
            ],
            [
              ".",
              "Throttles",
              ".",
              "."
            ]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 12
        height = 6

        properties = {
          title  = "B3 RAW to Silver - Duration"
          region = var.aws_region
          view   = "timeSeries"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Duration",
              "FunctionName",
              var.b3_silver_lambda_function_name,
              {
                stat  = "Average"
                label = "Average"
              }
            ],
            [
              "...",
              {
                stat  = "Maximum"
                label = "Maximum"
              }
            ]
          ]

          yAxis = {
            left = {
              label     = "Milliseconds"
              showUnits = false
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 18
        width  = 12
        height = 6

        properties = {
          title  = "B3 RAW to Silver - Error Rate"
          region = var.aws_region
          view   = "timeSeries"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Errors",
              "FunctionName",
              var.b3_silver_lambda_function_name,
              {
                id      = "silver_errors"
                visible = false
                stat    = "Sum"
              }
            ],
            [
              ".",
              "Invocations",
              ".",
              ".",
              {
                id      = "silver_invocations"
                visible = false
                stat    = "Sum"
              }
            ],
            [
              {
                expression = "IF(silver_invocations>0,(silver_errors/silver_invocations)*100,0)"
                label      = "Error Rate"
                id         = "silver_error_rate"
              }
            ]
          ]

          yAxis = {
            left = {
              min   = 0
              label = "Percent"
            }
          }
        }
      }
    ]
  })
}