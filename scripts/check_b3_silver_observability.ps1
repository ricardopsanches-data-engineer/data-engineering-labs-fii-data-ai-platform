$ErrorActionPreference = "Stop"

$region = "sa-east-1"

$functionName = (
    "fii-data-ai-platform-dev-b3-raw-to-silver"
)

$logGroupName = (
    "/aws/lambda/" +
    $functionName
)

Write-Host
Write-Host "======================================"
Write-Host "B3 SILVER LAMBDA OBSERVABILITY"
Write-Host "======================================"

Write-Host
Write-Host "Reading Lambda configuration..."

$configuration = aws lambda get-function-configuration `
    --function-name $functionName `
    --region $region `
    --output json `
    --no-cli-pager |
ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    throw "Could not read Lambda configuration."
}

$memorySizeMb = [double]$configuration.MemorySize
$timeoutSeconds = [double]$configuration.Timeout

Write-Host
Write-Host "Reading latest Lambda execution..."

$logs = @(
    aws logs tail `
        $logGroupName `
        --since 24h `
        --region $region `
        --format short `
        --no-cli-pager
)

if ($LASTEXITCODE -ne 0) {
    throw "Could not read Lambda logs."
}

$reportLine = (
    $logs |
    Select-String "REPORT RequestId:" |
    Select-Object -Last 1
)

$durationMs = $null
$maxMemoryMb = $null

if (
    $reportLine -and
    $reportLine.Line -match
    "Duration:\s+([0-9.]+)\s+ms"
) {
    $durationMs = [double]$Matches[1]
}

if (
    $reportLine -and
    $reportLine.Line -match
    "Max Memory Used:\s+([0-9]+)\s+MB"
) {
    $maxMemoryMb = [double]$Matches[1]
}

$memoryPercent = $null
$timeoutPercent = $null

if ($null -ne $maxMemoryMb) {
    $memoryPercent = (
        $maxMemoryMb /
        $memorySizeMb
    ) * 100
}

if ($null -ne $durationMs) {
    $timeoutPercent = (
        $durationMs /
        ($timeoutSeconds * 1000)
    ) * 100
}

Write-Host
Write-Host "Reading CloudWatch metrics..."

$endTime = (
    Get-Date
).ToUniversalTime()

$startTime = $endTime.AddHours(-24)

function Get-LambdaMetric {
    param (
        [string]$MetricName,
        [string]$Statistic
    )

    $result = aws cloudwatch get-metric-statistics `
        --namespace AWS/Lambda `
        --metric-name $MetricName `
        --dimensions (
            "Name=FunctionName,Value=" +
            $functionName
        ) `
        --statistics $Statistic `
        --period 3600 `
        --start-time (
            $startTime.ToString("o")
        ) `
        --end-time (
            $endTime.ToString("o")
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

    return @(
        $result.Datapoints
    )
}

$invocationPoints = Get-LambdaMetric `
    -MetricName "Invocations" `
    -Statistic "Sum"

$errorPoints = Get-LambdaMetric `
    -MetricName "Errors" `
    -Statistic "Sum"

$throttlePoints = Get-LambdaMetric `
    -MetricName "Throttles" `
    -Statistic "Sum"

$invocations = 0
$errors = 0
$throttles = 0

foreach ($point in $invocationPoints) {
    $invocations += $point.Sum
}

foreach ($point in $errorPoints) {
    $errors += $point.Sum
}

foreach ($point in $throttlePoints) {
    $throttles += $point.Sum
}

$errorRate = 0

if ($invocations -gt 0) {
    $errorRate = (
        $errors /
        $invocations
    ) * 100
}

$status = "OK"
$reasons = @()

if ($errors -gt 0) {
    $status = "WARNING"

    $reasons += (
        "Errors detected in the last 24 hours."
    )
}

if ($throttles -gt 0) {
    $status = "ATTENTION"

    $reasons += (
        "Lambda throttles detected."
    )
}

if (
    $null -ne $memoryPercent -and
    $memoryPercent -gt 80
) {
    $status = "ATTENTION"

    $reasons += (
        "Memory usage exceeded 80%."
    )
}

if (
    $null -ne $timeoutPercent -and
    $timeoutPercent -gt 80
) {
    $status = "ATTENTION"

    $reasons += (
        "Execution exceeded 80% of timeout."
    )
}

Write-Host
Write-Host "======================================"
Write-Host "CONFIGURATION"
Write-Host "======================================"

Write-Host (
    "State:          " +
    $configuration.State
)

Write-Host (
    "Memory:         " +
    $memorySizeMb +
    " MB"
)

Write-Host (
    "Timeout:        " +
    $timeoutSeconds +
    " s"
)

Write-Host
Write-Host "======================================"
Write-Host "LATEST EXECUTION"
Write-Host "======================================"

if ($null -ne $durationMs) {
    Write-Host (
        "Duration:       " +
        [math]::Round(
            $durationMs,
            2
        ) +
        " ms"
    )
}

if ($null -ne $maxMemoryMb) {
    Write-Host (
        "Max Memory:     " +
        $maxMemoryMb +
        " MB"
    )
}

if ($null -ne $memoryPercent) {
    Write-Host (
        "Memory Usage:   " +
        [math]::Round(
            $memoryPercent,
            2
        ) +
        "%"
    )
}

if ($null -ne $timeoutPercent) {
    Write-Host (
        "Timeout Usage:  " +
        [math]::Round(
            $timeoutPercent,
            2
        ) +
        "%"
    )
}

Write-Host
Write-Host "======================================"
Write-Host "LAST 24 HOURS"
Write-Host "======================================"

Write-Host (
    "Invocations:     " +
    [math]::Round(
        $invocations,
        0
    )
)

Write-Host (
    "Errors:          " +
    [math]::Round(
        $errors,
        0
    )
)

Write-Host (
    "Error Rate:      " +
    [math]::Round(
        $errorRate,
        2
    ) +
    "%"
)

Write-Host (
    "Throttles:       " +
    [math]::Round(
        $throttles,
        0
    )
)

if ($reasons.Count -gt 0) {
    Write-Host
    Write-Host "Reasons:"

    foreach ($reason in $reasons) {
        Write-Host (
            " - " +
            $reason
        )
    }
}

Write-Host
Write-Host "======================================"
Write-Host (
    "OBSERVABILITY STATUS: " +
    $status
)
Write-Host "======================================"