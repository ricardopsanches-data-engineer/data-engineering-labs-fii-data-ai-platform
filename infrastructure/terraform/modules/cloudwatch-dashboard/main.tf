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
          title  = "Lambda Invocations"
          region = var.aws_region
          view   = "timeSeries"
          stat   = "Sum"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Invocations",
              "FunctionName",
              var.lambda_function_name
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
          title  = "Lambda Errors and Throttles"
          region = var.aws_region
          view   = "timeSeries"
          stat   = "Sum"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Errors",
              "FunctionName",
              var.lambda_function_name
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
          title  = "Lambda Duration"
          region = var.aws_region
          view   = "timeSeries"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Duration",
              "FunctionName",
              var.lambda_function_name,
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
              label = "Milliseconds"
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
          title  = "Lambda Error Rate"
          region = var.aws_region
          view   = "timeSeries"
          period = 3600

          metrics = [
            [
              "AWS/Lambda",
              "Errors",
              "FunctionName",
              var.lambda_function_name,
              {
                id      = "errors"
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
                id      = "invocations"
                visible = false
                stat    = "Sum"
              }
            ],
            [
              {
                expression = "IF(invocations>0,(errors/invocations)*100,0)"
                label      = "Error Rate"
                id         = "error_rate"
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