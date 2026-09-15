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


Write-Host "======================================"
Write-Host "DAILY INGESTION HEALTH CHECK"
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


Write-Host "Reading recent Lambda logs..."

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
    throw "No Lambda execution found in the last 24 hours."
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
    throw (
        "Latest Lambda execution does not contain " +
        "a REPORT line."
    )
}


$latestExecutionLines = @(
    $logs[
        $lastStartIndex..$reportIndex
    ]
)


Write-Host (
    "Latest RequestId: " +
    $requestId
)

Write-Host
Write-Host "Analyzing latest execution..."


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
    $durationMs = $Matches[1]
}

if (
    $reportLine -and
    $reportLine.Line -match
    "Max Memory Used:\s+([0-9]+)\s+MB"
) {
    $maxMemoryMb = $Matches[1]
}


$executionTimestampUtc = "UNKNOWN"
$executionTimestampLocal = "UNKNOWN"

if (
    $startLine -match
    "^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+)"
) {
    $executionTimestampUtc = $Matches[1]

    try {
        $utcDate = [DateTime]::Parse(
            $executionTimestampUtc
        )

        $utcDate = [DateTime]::SpecifyKind(
            $utcDate,
            [DateTimeKind]::Utc
        )

        $timeZone = [TimeZoneInfo]::FindSystemTimeZoneById(
            "E. South America Standard Time"
        )

        $localDate = [TimeZoneInfo]::ConvertTimeFromUtc(
            $utcDate,
            $timeZone
        )

        $executionTimestampLocal = (
            $localDate.ToString(
                "yyyy-MM-dd HH:mm:ss"
            )
        )
    }
    catch {
        $executionTimestampLocal = "UNKNOWN"
    }
}


Write-Host
Write-Host "======================================"
Write-Host "LAST EXECUTION"
Write-Host "======================================"

Write-Host (
    "RequestId:  " +
    $requestId
)

Write-Host (
    "UTC:        " +
    $executionTimestampUtc
)

Write-Host (
    "Sao Paulo:  " +
    $executionTimestampLocal
)

Write-Host (
    "Lambda:     " +
    $lambdaStatus
)

Write-Host

Write-Host (
    "B3:         " +
    $b3Status
)

Write-Host (
    "B3 Action:  " +
    $b3Action
)

Write-Host

Write-Host (
    "CVM:        " +
    $cvmStatus
)

Write-Host (
    "CVM Action: " +
    $cvmAction
)

if ($durationMs) {
    Write-Host
    Write-Host (
        "Duration:   " +
        $durationMs +
        " ms"
    )
}

if ($maxMemoryMb) {
    Write-Host (
        "Max Memory: " +
        $maxMemoryMb +
        " MB"
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

if ($LASTEXITCODE -ne 0) {
    throw "Could not read B3 RAW objects."
}

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

if ($LASTEXITCODE -ne 0) {
    throw "Could not read CVM RAW objects."
}

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
        "CVM Updated: " +
        $cvmObject.LastModified
    )
}
else {
    Write-Host "CVM RAW:    NOT FOUND"
}


Write-Host
Write-Host "======================================"

$actionsKnown = (
    $b3Action -ne "UNKNOWN" -and
    $cvmAction -ne "UNKNOWN"
)

if (
    $lambdaStatus -eq "SUCCESS" -and
    $b3Status -eq "SUCCESS" -and
    $cvmStatus -eq "SUCCESS" -and
    $actionsKnown -and
    $b3Object -and
    $cvmObject
) {
    Write-Host "HEALTH CHECK: OK"
}
else {
    Write-Host "HEALTH CHECK: ATTENTION"
}

Write-Host "======================================"