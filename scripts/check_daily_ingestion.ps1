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

Write-Host "======================================"
Write-Host "DAILY INGESTION HEALTH CHECK"
Write-Host "======================================"
Write-Host

Write-Host "AWS identity..."

$identity = aws sts get-caller-identity `
    --output json `
    --no-cli-pager |
    ConvertFrom-Json

Write-Host (
    "Account: " +
    $identity.Account
)

Write-Host (
    "ARN:     " +
    $identity.Arn
)

Write-Host

Write-Host "Reading recent Lambda logs..."

$logs = aws logs tail `
    $logGroupName `
    --since 24h `
    --region $region `
    --format short `
    --no-cli-pager

if ($LASTEXITCODE -ne 0) {
    throw "Could not read Lambda logs."
}

if (-not $logs) {
    throw "No Lambda logs found in the last 24 hours."
}

$requestStarts = @(
    $logs |
    Select-String "START RequestId:"
)

if (-not $requestStarts) {
    throw "No Lambda execution found in the last 24 hours."
}

$lastRequestStart = $requestStarts[-1].Line

if (
    $lastRequestStart -match
    "START RequestId:\s+([^\s]+)"
) {
    $requestId = $Matches[1]
}
else {
    throw "Could not extract the latest RequestId."
}

Write-Host (
    "Latest RequestId: " +
    $requestId
)

Write-Host
Write-Host "Analyzing latest execution..."

$latestExecutionLines = @(
    $logs |
    Select-String `
        -Pattern $requestId `
        -Context 30, 30
) |
ForEach-Object {
    $_.Context.PreContext
    $_.Line
    $_.Context.PostContext
} |
Select-Object -Unique

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

$reportLine = (
    $latestExecutionLines |
    Select-String "REPORT RequestId:" |
    Select-Object -Last 1
)

$durationMs = $null

if (
    $reportLine -and
    $reportLine.Line -match
    "Duration:\s+([0-9.]+)\s+ms"
) {
    $durationMs = $Matches[1]
}

$startLine = (
    $latestExecutionLines |
    Select-String "START RequestId:" |
    Select-Object -First 1
)

$executionTimestamp = "UNKNOWN"

if ($startLine) {
    $parts = (
        $startLine.Line `
            -split "\s+"
    )

    if ($parts.Count -ge 1) {
        $executionTimestamp = $parts[0]
    }
}

Write-Host
Write-Host "======================================"
Write-Host "LAST EXECUTION"
Write-Host "======================================"

Write-Host (
    "RequestId: " +
    $requestId
)

Write-Host (
    "Timestamp: " +
    $executionTimestamp
)

Write-Host (
    "Lambda:    " +
    $lambdaStatus
)

Write-Host (
    "B3:        " +
    $b3Status
)

Write-Host (
    "CVM:       " +
    $cvmStatus
)

if ($durationMs) {
    Write-Host (
        "Duration:  " +
        $durationMs +
        " ms"
    )
}

Write-Host

Write-Host "Reading latest B3 RAW object..."

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

if ($b3Object) {
    Write-Host (
        "B3 RAW:     " +
        $b3Object.Key
    )

    Write-Host (
        "B3 Size:    " +
        $b3Object.Size +
        " bytes"
    )

    Write-Host (
        "B3 Updated: " +
        $b3Object.LastModified
    )
}
else {
    Write-Host "B3 RAW:     NOT FOUND"
}

Write-Host

Write-Host "Reading latest CVM RAW object..."

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

if ($cvmObject) {
    Write-Host (
        "CVM RAW:    " +
        $cvmObject.Key
    )

    Write-Host (
        "CVM Size:   " +
        $cvmObject.Size +
        " bytes"
    )

    Write-Host (
        "CVM Updated:" +
        " " +
        $cvmObject.LastModified
    )
}
else {
    Write-Host "CVM RAW:    NOT FOUND"
}

Write-Host
Write-Host "======================================"

if (
    $lambdaStatus -eq "SUCCESS" -and
    $b3Status -eq "SUCCESS" -and
    $cvmStatus -eq "SUCCESS" -and
    $b3Object -and
    $cvmObject
) {
    Write-Host "HEALTH CHECK: OK"
}
else {
    Write-Host "HEALTH CHECK: ATTENTION"
}

Write-Host "======================================"