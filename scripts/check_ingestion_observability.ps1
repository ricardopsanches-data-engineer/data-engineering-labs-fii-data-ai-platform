$ErrorActionPreference = "Stop"

$region = "sa-east-1"

$functionName = "fii-data-ai-platform-dev-daily-ingestion"

$logGroupName = (
    "/aws/lambda/" +
    $functionName
)

$bucketName = (
    "fii-data-ai-platform-dev-datalake-625685670804"
)

$namespace = "AWS/Lambda"

$period = 3600

$lambdaMemoryMb = 512
$lambdaTimeoutSeconds = 60

$memoryAttentionPercent = 80
$durationAttentionPercent = 80

$weekdayFreshnessThresholdHours = 30
$weekendFreshnessThresholdHours = 80

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


function Get-SourceAction {
    param (
        [string[]]$Lines
    )

    if (
        $Lines |
        Select-String "Upload S3 conclu"
    ) {
        return "UPLOAD_COMPLETED"
    }

    if (
        $Lines |
        Select-String "reempacotamento detectado"
    ) {
        return "REPACKAGING_DETECTED"
    }

    if (
        $Lines |
        Select-String "Upload S3 ignorado.*SHA-256"
    ) {
        return "UPLOAD_SKIPPED_IDENTICAL"
    }

    if (
        $Lines |
        Select-String "\|\s+ERROR\s+\|"
    ) {
        return "ERROR"
    }

    return "UNKNOWN"
}


function Convert-ToSaoPaulo {
    param (
        [DateTime]$UtcDate
    )

    try {
        $timeZone = [TimeZoneInfo]::FindSystemTimeZoneById(
            "E. South America Standard Time"
        )

        return [TimeZoneInfo]::ConvertTimeFromUtc(
            $UtcDate,
            $timeZone
        )
    }
    catch {
        return $null
    }
}


Write-Host "======================================"
Write-Host "INGESTION OBSERVABILITY"
Write-Host "======================================"
Write-Host

Write-Host "AWS identity..."

$identity = aws sts get-caller-identity `
    --output json `
    --no-cli-pager |
    ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    throw "Could not read AWS identity."
}

Write-Host (
    "Account: " +
    $identity.Account
)

Write-Host (
    "ARN:     " +
    $identity.Arn
)

Write-Host


$nowLocal = Convert-ToSaoPaulo `
    -UtcDate $endTime

if ($null -eq $nowLocal) {
    throw "Could not convert current time to Sao Paulo."
}


$isWeekend = (
    $nowLocal.DayOfWeek -eq "Saturday" -or
    $nowLocal.DayOfWeek -eq "Sunday"
)

if ($isWeekend) {
    $freshnessThresholdHours = (
        $weekendFreshnessThresholdHours
    )
}
else {
    $freshnessThresholdHours = (
        $weekdayFreshnessThresholdHours
    )
}


Write-Host "Reading Lambda logs..."

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

if (-not $logs) {
    throw "No Lambda logs found in the last 24 hours."
}


$startIndexes = @()

for (
    $index = 0;
    $index -lt $logs.Count;
    $index++
) {
    if (
        $logs[$index] -match
        "START RequestId:\s+([^\s]+)"
    ) {
        $startIndexes += $index
    }
}

if (-not $startIndexes) {
    throw "No Lambda execution found."
}


$lastStartIndex = $startIndexes[-1]

$startLine = $logs[$lastStartIndex]

if (
    $startLine -match
    "START RequestId:\s+([^\s]+)"
) {
    $requestId = $Matches[1]
}
else {
    throw "Could not extract latest RequestId."
}


$reportIndex = $null

for (
    $index = $lastStartIndex;
    $index -lt $logs.Count;
    $index++
) {
    if (
        $logs[$index] -match
        (
            "REPORT RequestId:\s+" +
            [regex]::Escape($requestId)
        )
    ) {
        $reportIndex = $index
        break
    }
}

if ($null -eq $reportIndex) {
    throw "Latest Lambda execution is incomplete."
}


$latestExecutionLines = @(
    $logs[
        $lastStartIndex..$reportIndex
    ]
)


$b3SectionIndex = $null
$cvmSectionIndex = $null
$summarySectionIndex = $null

for (
    $index = 0;
    $index -lt $latestExecutionLines.Count;
    $index++
) {
    $line = $latestExecutionLines[$index]

    if (
        $line -match
        "B3 RAW -> S3 \| DAILY"
    ) {
        $b3SectionIndex = $index
    }

    if (
        $line -match
        "CVM RAW -> S3 \| DAILY"
    ) {
        $cvmSectionIndex = $index
    }

    if (
        $line -match
        "Resumo final"
    ) {
        $summarySectionIndex = $index
    }
}


$b3Lines = @()
$cvmLines = @()

if (
    $null -ne $b3SectionIndex -and
    $null -ne $cvmSectionIndex
) {
    $b3Lines = @(
        $latestExecutionLines[
            $b3SectionIndex..(
                $cvmSectionIndex - 1
            )
        ]
    )
}

if (
    $null -ne $cvmSectionIndex -and
    $null -ne $summarySectionIndex
) {
    $cvmLines = @(
        $latestExecutionLines[
            $cvmSectionIndex..(
                $summarySectionIndex - 1
            )
        ]
    )
}


$b3Status = "UNKNOWN"
$cvmStatus = "UNKNOWN"
$lambdaStatus = "UNKNOWN"

if (
    $latestExecutionLines |
    Select-String "B3:\s+success"
) {
    $b3Status = "SUCCESS"
}

if (
    $latestExecutionLines |
    Select-String "B3:\s+error"
) {
    $b3Status = "ERROR"
}

if (
    $latestExecutionLines |
    Select-String "CVM:\s+success"
) {
    $cvmStatus = "SUCCESS"
}

if (
    $latestExecutionLines |
    Select-String "CVM:\s+error"
) {
    $cvmStatus = "ERROR"
}

if (
    $latestExecutionLines |
    Select-String "\[ERROR\]"
) {
    $lambdaStatus = "ERROR"
}
elseif (
    $latestExecutionLines |
    Select-String "END RequestId:"
) {
    $lambdaStatus = "SUCCESS"
}


$b3Action = Get-SourceAction `
    -Lines $b3Lines

$cvmAction = Get-SourceAction `
    -Lines $cvmLines


$reportLine = (
    $latestExecutionLines |
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
    $maxMemoryMb = [int]$Matches[1]
}


$executionUtc = $null
$executionLocal = $null
$executionAgeHours = $null

if (
    $startLine -match
    "^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+)"
) {
    $executionUtc = [DateTime]::Parse(
        $Matches[1]
    )

    $executionUtc = [DateTime]::SpecifyKind(
        $executionUtc,
        [DateTimeKind]::Utc
    )

    $executionLocal = Convert-ToSaoPaulo `
        -UtcDate $executionUtc

    $executionAgeHours = (
        $endTime -
        $executionUtc
    ).TotalHours
}


Write-Host "Reading CloudWatch metrics..."

$invocationDatapoints = Get-CloudWatchMetric `
    -MetricName "Invocations" `
    -Statistic "Sum"

$errorDatapoints = Get-CloudWatchMetric `
    -MetricName "Errors" `
    -Statistic "Sum"

$throttleDatapoints = Get-CloudWatchMetric `
    -MetricName "Throttles" `
    -Statistic "Sum"

$durationAverageDatapoints = Get-CloudWatchMetric `
    -MetricName "Duration" `
    -Statistic "Average"

$durationMaximumDatapoints = Get-CloudWatchMetric `
    -MetricName "Duration" `
    -Statistic "Maximum"


$invocations = 0
$errors = 0
$throttles = 0

foreach ($point in $invocationDatapoints) {
    $invocations += $point.Sum
}

foreach ($point in $errorDatapoints) {
    $errors += $point.Sum
}

foreach ($point in $throttleDatapoints) {
    $throttles += $point.Sum
}


$durationAverage = $null
$durationMaximum = $null

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


Write-Host "Reading latest RAW objects..."

$b3Object = aws s3api list-objects-v2 `
    --bucket $bucketName `
    --prefix "raw/b3/" `
    --region $region `
    --query (
        "reverse(sort_by(" +
        "Contents,&LastModified))[0]"
    ) `
    --output json `
    --no-cli-pager |
    ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    throw "Could not read B3 RAW objects."
}

$cvmObject = aws s3api list-objects-v2 `
    --bucket $bucketName `
    --prefix "raw/cvm/" `
    --region $region `
    --query (
        "reverse(sort_by(" +
        "Contents,&LastModified))[0]"
    ) `
    --output json `
    --no-cli-pager |
    ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    throw "Could not read CVM RAW objects."
}


$b3FreshnessHours = $null
$cvmFreshnessHours = $null

if ($b3Object) {
    $b3LastModified = [DateTime]::Parse(
        $b3Object.LastModified
    ).ToUniversalTime()

    $b3FreshnessHours = (
        $endTime -
        $b3LastModified
    ).TotalHours
}

if ($cvmObject) {
    $cvmLastModified = [DateTime]::Parse(
        $cvmObject.LastModified
    ).ToUniversalTime()

    $cvmFreshnessHours = (
        $endTime -
        $cvmLastModified
    ).TotalHours
}


$memoryPercent = $null
$durationPercent = $null

if ($maxMemoryMb) {
    $memoryPercent = (
        $maxMemoryMb /
        $lambdaMemoryMb
    ) * 100
}

if ($durationMs) {
    $durationPercent = (
        $durationMs /
        ($lambdaTimeoutSeconds * 1000)
    ) * 100
}


$criticalReasons = @()
$attentionReasons = @()
$warningReasons = @()


if ($lambdaStatus -ne "SUCCESS") {
    $criticalReasons += (
        "Latest Lambda execution is not SUCCESS."
    )
}

if ($b3Status -ne "SUCCESS") {
    $criticalReasons += (
        "Latest B3 ingestion is not SUCCESS."
    )
}

if ($cvmStatus -ne "SUCCESS") {
    $criticalReasons += (
        "Latest CVM ingestion is not SUCCESS."
    )
}


if ($b3Action -eq "UNKNOWN") {
    $attentionReasons += (
        "B3 action could not be classified."
    )
}

if ($cvmAction -eq "UNKNOWN") {
    $attentionReasons += (
        "CVM action could not be classified."
    )
}


if ($throttles -gt 0) {
    $attentionReasons += (
        "Lambda throttles detected in the last 24 hours."
    )
}


if (
    $null -ne $executionAgeHours -and
    $executionAgeHours -gt $freshnessThresholdHours
) {
    $attentionReasons += (
        "Latest Lambda execution is older than " +
        $freshnessThresholdHours +
        " hours."
    )
}


if (
    $null -ne $b3FreshnessHours -and
    $b3FreshnessHours -gt $freshnessThresholdHours
) {
    $attentionReasons += (
        "B3 RAW freshness exceeded " +
        $freshnessThresholdHours +
        " hours."
    )
}


if (
    $null -ne $cvmFreshnessHours -and
    $cvmFreshnessHours -gt $freshnessThresholdHours
) {
    $attentionReasons += (
        "CVM RAW freshness exceeded " +
        $freshnessThresholdHours +
        " hours."
    )
}


if (
    $null -ne $memoryPercent -and
    $memoryPercent -gt $memoryAttentionPercent
) {
    $attentionReasons += (
        "Lambda memory usage exceeded " +
        $memoryAttentionPercent +
        "%."
    )
}


if (
    $null -ne $durationPercent -and
    $durationPercent -gt $durationAttentionPercent
) {
    $attentionReasons += (
        "Lambda duration exceeded " +
        $durationAttentionPercent +
        "% of configured timeout."
    )
}


if ($errors -gt 0) {
    $warningReasons += (
        "Historical Lambda errors detected in the last 24 hours: " +
        [math]::Round(
            $errors,
            0
        )
    )
}


Write-Host
Write-Host "======================================"
Write-Host "LATEST EXECUTION"
Write-Host "======================================"

Write-Host (
    "RequestId:    " +
    $requestId
)

if ($executionUtc) {
    Write-Host (
        "UTC:          " +
        $executionUtc.ToString(
            "yyyy-MM-dd HH:mm:ss"
        )
    )
}

if ($executionLocal) {
    Write-Host (
        "Sao Paulo:    " +
        $executionLocal.ToString(
            "yyyy-MM-dd HH:mm:ss"
        )
    )
}

if ($null -ne $executionAgeHours) {
    Write-Host (
        "Age:          " +
        [math]::Round(
            $executionAgeHours,
            2
        ) +
        " hours"
    )
}

Write-Host (
    "Lambda:       " +
    $lambdaStatus
)

Write-Host (
    "B3:           " +
    $b3Status
)

Write-Host (
    "B3 Action:    " +
    $b3Action
)

Write-Host (
    "CVM:          " +
    $cvmStatus
)

Write-Host (
    "CVM Action:   " +
    $cvmAction
)

if ($durationMs) {
    Write-Host (
        "Duration:     " +
        [math]::Round(
            $durationMs,
            2
        ) +
        " ms"
    )
}

if ($maxMemoryMb) {
    Write-Host (
        "Max Memory:   " +
        $maxMemoryMb +
        " MB"
    )
}

if ($null -ne $memoryPercent) {
    Write-Host (
        "Memory Usage: " +
        [math]::Round(
            $memoryPercent,
            2
        ) +
        "%"
    )
}

if ($null -ne $durationPercent) {
    Write-Host (
        "Timeout Usage:" +
        " " +
        [math]::Round(
            $durationPercent,
            2
        ) +
        "%"
    )
}


Write-Host
Write-Host "======================================"
Write-Host "LAMBDA METRICS - LAST 24 HOURS"
Write-Host "======================================"

Write-Host (
    "Invocations:   " +
    [math]::Round(
        $invocations,
        0
    )
)

Write-Host (
    "Errors:        " +
    [math]::Round(
        $errors,
        0
    )
)

Write-Host (
    "Error Rate:    " +
    [math]::Round(
        $errorRate,
        2
    ) +
    "%"
)

Write-Host (
    "Throttles:     " +
    [math]::Round(
        $throttles,
        0
    )
)

if ($null -ne $durationAverage) {
    Write-Host (
        "Avg Duration: " +
        [math]::Round(
            $durationAverage,
            2
        ) +
        " ms"
    )
}

if ($null -ne $durationMaximum) {
    Write-Host (
        "Max Duration: " +
        [math]::Round(
            $durationMaximum,
            2
        ) +
        " ms"
    )
}


Write-Host
Write-Host "======================================"
Write-Host "RAW FRESHNESS"
Write-Host "======================================"

Write-Host (
    "Threshold:     " +
    $freshnessThresholdHours +
    " hours"
)

if ($b3Object) {
    Write-Host (
        "B3 RAW:       " +
        $b3Object.Key
    )

    Write-Host (
        "B3 Size:      " +
        $b3Object.Size +
        " bytes"
    )

    Write-Host (
        "B3 Freshness: " +
        [math]::Round(
            $b3FreshnessHours,
            2
        ) +
        " hours"
    )
}
else {
    Write-Host "B3 RAW:       NOT FOUND"

    $criticalReasons += (
        "B3 RAW object not found."
    )
}

Write-Host

if ($cvmObject) {
    Write-Host (
        "CVM RAW:      " +
        $cvmObject.Key
    )

    Write-Host (
        "CVM Size:     " +
        $cvmObject.Size +
        " bytes"
    )

    Write-Host (
        "CVM Freshness:" +
        " " +
        [math]::Round(
            $cvmFreshnessHours,
            2
        ) +
        " hours"
    )
}
else {
    Write-Host "CVM RAW:      NOT FOUND"

    $criticalReasons += (
        "CVM RAW object not found."
    )
}


Write-Host
Write-Host "======================================"
Write-Host "THRESHOLD EVALUATION"
Write-Host "======================================"

Write-Host (
    "Freshness limit: " +
    $freshnessThresholdHours +
    " hours"
)

Write-Host (
    "Memory warning:  " +
    $memoryAttentionPercent +
    "%"
)

Write-Host (
    "Timeout warning: " +
    $durationAttentionPercent +
    "%"
)


if ($warningReasons.Count -gt 0) {
    Write-Host
    Write-Host "Warnings:"

    foreach ($reason in $warningReasons) {
        Write-Host (
            " - " +
            $reason
        )
    }
}


if ($attentionReasons.Count -gt 0) {
    Write-Host
    Write-Host "Attention:"

    foreach ($reason in $attentionReasons) {
        Write-Host (
            " - " +
            $reason
        )
    }
}


if ($criticalReasons.Count -gt 0) {
    Write-Host
    Write-Host "Critical:"

    foreach ($reason in $criticalReasons) {
        Write-Host (
            " - " +
            $reason
        )
    }
}


Write-Host
Write-Host "======================================"

if ($criticalReasons.Count -gt 0) {
    Write-Host "OBSERVABILITY STATUS: CRITICAL"
}
elseif ($attentionReasons.Count -gt 0) {
    Write-Host "OBSERVABILITY STATUS: ATTENTION"
}
elseif ($warningReasons.Count -gt 0) {
    Write-Host "OBSERVABILITY STATUS: OK WITH WARNINGS"
}
else {
    Write-Host "OBSERVABILITY STATUS: OK"
}

Write-Host "======================================"