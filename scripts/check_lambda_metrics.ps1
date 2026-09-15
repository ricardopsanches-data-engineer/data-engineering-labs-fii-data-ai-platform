$ErrorActionPreference = "Stop"

$region = "sa-east-1"

$functionName = "fii-data-ai-platform-dev-daily-ingestion"

$namespace = "AWS/Lambda"

$period = 3600

$endTime = (Get-Date).ToUniversalTime()

$startTime = $endTime.AddHours(-24)


function Get-CloudWatchMetric {
    param (
        [string]$MetricName,
        [string]$Statistic
    )

    $result = aws cloudwatch get-metric-statistics `
        --namespace $namespace `
        --metric-name $MetricName `
        --dimensions (
            "Name=FunctionName,Value=" +
            $functionName
        ) `
        --statistics $Statistic `
        --period $period `
        --start-time (
            $startTime.ToString(
                "yyyy-MM-ddTHH:mm:ssZ"
            )
        ) `
        --end-time (
            $endTime.ToString(
                "yyyy-MM-ddTHH:mm:ssZ"
            )
        ) `
        --region $region `
        --output json `
        --no-cli-pager |
        ConvertFrom-Json

    if ($LASTEXITCODE -ne 0) {
        throw (
            "Could not read metric: " +
            $MetricName
        )
    }

    return $result.Datapoints
}


Write-Host "======================================"
Write-Host "LAMBDA METRICS - LAST 24 HOURS"
Write-Host "======================================"
Write-Host

Write-Host (
    "Function: " +
    $functionName
)

Write-Host (
    "Region:   " +
    $region
)

Write-Host (
    "From UTC: " +
    $startTime.ToString(
        "yyyy-MM-dd HH:mm:ss"
    )
)

Write-Host (
    "To UTC:   " +
    $endTime.ToString(
        "yyyy-MM-dd HH:mm:ss"
    )
)

Write-Host


Write-Host "Reading Invocations..."

$invocationDatapoints = Get-CloudWatchMetric `
    -MetricName "Invocations" `
    -Statistic "Sum"

$invocations = 0

foreach ($point in $invocationDatapoints) {
    $invocations += $point.Sum
}


Write-Host "Reading Errors..."

$errorDatapoints = Get-CloudWatchMetric `
    -MetricName "Errors" `
    -Statistic "Sum"

$errors = 0

foreach ($point in $errorDatapoints) {
    $errors += $point.Sum
}


Write-Host "Reading Throttles..."

$throttleDatapoints = Get-CloudWatchMetric `
    -MetricName "Throttles" `
    -Statistic "Sum"

$throttles = 0

foreach ($point in $throttleDatapoints) {
    $throttles += $point.Sum
}


Write-Host "Reading Duration average..."

$durationAverageDatapoints = Get-CloudWatchMetric `
    -MetricName "Duration" `
    -Statistic "Average"

$durationAverage = $null

if ($durationAverageDatapoints) {
    $averageValues = @(
        $durationAverageDatapoints |
        ForEach-Object {
            $_.Average
        }
    )

    if ($averageValues.Count -gt 0) {
        $durationAverage = (
            $averageValues |
            Measure-Object `
                -Average
        ).Average
    }
}


Write-Host "Reading Duration maximum..."

$durationMaximumDatapoints = Get-CloudWatchMetric `
    -MetricName "Duration" `
    -Statistic "Maximum"

$durationMaximum = $null

if ($durationMaximumDatapoints) {
    $maximumValues = @(
        $durationMaximumDatapoints |
        ForEach-Object {
            $_.Maximum
        }
    )

    if ($maximumValues.Count -gt 0) {
        $durationMaximum = (
            $maximumValues |
            Measure-Object `
                -Maximum
        ).Maximum
    }
}


$errorRate = 0

if ($invocations -gt 0) {
    $errorRate = (
        $errors /
        $invocations
    ) * 100
}


Write-Host
Write-Host "======================================"
Write-Host "SUMMARY"
Write-Host "======================================"

Write-Host (
    "Invocations: " +
    [math]::Round(
        $invocations,
        0
    )
)

Write-Host (
    "Errors:      " +
    [math]::Round(
        $errors,
        0
    )
)

Write-Host (
    "Error Rate:  " +
    [math]::Round(
        $errorRate,
        2
    ) +
    "%"
)

Write-Host (
    "Throttles:   " +
    [math]::Round(
        $throttles,
        0
    )
)

if ($null -ne $durationAverage) {
    Write-Host (
        "Avg Duration:" +
        " " +
        [math]::Round(
            $durationAverage,
            2
        ) +
        " ms"
    )
}
else {
    Write-Host "Avg Duration: no data"
}

if ($null -ne $durationMaximum) {
    Write-Host (
        "Max Duration:" +
        " " +
        [math]::Round(
            $durationMaximum,
            2
        ) +
        " ms"
    )
}
else {
    Write-Host "Max Duration: no data"
}


Write-Host
Write-Host "======================================"

if (
    $errors -eq 0 -and
    $throttles -eq 0
) {
    Write-Host "LAMBDA METRICS STATUS: OK"
}
else {
    Write-Host "LAMBDA METRICS STATUS: ATTENTION"
}

Write-Host "======================================"