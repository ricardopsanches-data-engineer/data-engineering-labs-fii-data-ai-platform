$ErrorActionPreference = "Stop"

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path

$repositoryRoot = Resolve-Path (
    Join-Path $scriptDirectory "..\.."
)

$packageDirectory = Join-Path `
    $scriptDirectory `
    "package"

$buildDirectory = Join-Path `
    $scriptDirectory `
    "build"

$zipPath = Join-Path `
    $buildDirectory `
    "gold_recovery_supervisor.zip"

$fixedTimestamp = [DateTime]::SpecifyKind(
    (Get-Date "2026-01-01T00:00:00"),
    [DateTimeKind]::Utc
)

Write-Host "======================================"
Write-Host "Gold Recovery Supervisor Lambda build"
Write-Host "======================================"
Write-Host "Repository: $repositoryRoot"
Write-Host "Package:    $packageDirectory"
Write-Host "Build:      $buildDirectory"
Write-Host

Write-Host "Cleaning previous artifacts..."

Remove-Item `
    $packageDirectory `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

Remove-Item `
    $buildDirectory `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

New-Item `
    -ItemType Directory `
    -Force `
    -Path $packageDirectory |
    Out-Null

New-Item `
    -ItemType Directory `
    -Force `
    -Path $buildDirectory |
    Out-Null

$packageSrcDirectory = Join-Path `
    $packageDirectory `
    "src"

$packageOrchestrationDirectory = Join-Path `
    $packageSrcDirectory `
    "orchestration"

$packageObservabilityDirectory = Join-Path `
    $packageSrcDirectory `
    "observability"

$packageCalendarDirectory = Join-Path `
    $packageDirectory `
    "config\calendars\b3"

New-Item `
    -ItemType Directory `
    -Force `
    -Path $packageSrcDirectory |
    Out-Null

New-Item `
    -ItemType Directory `
    -Force `
    -Path $packageOrchestrationDirectory |
    Out-Null

New-Item `
    -ItemType Directory `
    -Force `
    -Path $packageObservabilityDirectory |
    Out-Null

New-Item `
    -ItemType Directory `
    -Force `
    -Path $packageCalendarDirectory |
    Out-Null

Write-Host
Write-Host "Copying supervisor source and calendar..."

$filesToCopy = @(
    @{
        Source = "src\__init__.py"
        Destination = "src\__init__.py"
    },
    @{
        Source = "src\orchestration\__init__.py"
        Destination = "src\orchestration\__init__.py"
    },
    @{
        Source = "src\orchestration\b3_trading_calendar.py"
        Destination = "src\orchestration\b3_trading_calendar.py"
    },
    @{
        Source = "src\orchestration\gold_recovery_supervisor.py"
        Destination = "src\orchestration\gold_recovery_supervisor.py"
    },
    @{
        Source = "src\orchestration\gold_recovery.py"
        Destination = "src\orchestration\gold_recovery.py"
    },
    @{
        Source = "src\orchestration\gold_recovery_executor.py"
        Destination = "src\orchestration\gold_recovery_executor.py"
    },
    @{
        Source = "src\orchestration\gold_recovery_state.py"
        Destination = "src\orchestration\gold_recovery_state.py"
    },
    @{
        Source = "src\orchestration\gold_execution_state.py"
        Destination = "src\orchestration\gold_execution_state.py"
    },
    @{
        Source = "src\orchestration\gold_expected_cycles.py"
        Destination = "src\orchestration\gold_expected_cycles.py"
    },
    @{
        Source = "src\orchestration\gold_readiness.py"
        Destination = "src\orchestration\gold_readiness.py"
    },
    @{
        Source = "src\observability\__init__.py"
        Destination = "src\observability\__init__.py"
    },
    @{
        Source = "src\observability\events.py"
        Destination = "src\observability\events.py"
    },
    @{
        Source = "src\observability\gold_recovery_observability.py"
        Destination = "src\observability\gold_recovery_observability.py"
    },
    @{
        Source = "config\calendars\b3\2026.json"
        Destination = "config\calendars\b3\2026.json"
    }
)

foreach ($item in $filesToCopy) {
    $sourcePath = Join-Path `
        $repositoryRoot `
        $item.Source

    $destinationPath = Join-Path `
        $packageDirectory `
        $item.Destination

    $destinationDirectory = Split-Path `
        -Parent `
        $destinationPath

    if (-not (Test-Path $sourcePath)) {
        throw (
            "Required source file missing: " +
            $item.Source
        )
    }

    New-Item `
        -ItemType Directory `
        -Force `
        -Path $destinationDirectory |
        Out-Null

    Copy-Item `
        -Path $sourcePath `
        -Destination $destinationPath
}

Write-Host
Write-Host "Removing Python cache directories..."

Get-ChildItem `
    $packageDirectory `
    -Recurse `
    -Directory `
    -Filter "__pycache__" |
    Remove-Item `
        -Recurse `
        -Force

Write-Host
Write-Host "Normalizing file timestamps..."

Get-ChildItem `
    $packageDirectory `
    -Recurse `
    -File |
    ForEach-Object {
        $_.LastWriteTimeUtc = $fixedTimestamp
    }

Write-Host
Write-Host "Validating package contents..."

$requiredFiles = @(
    "src\__init__.py",
    "src\orchestration\__init__.py",
    "src\orchestration\b3_trading_calendar.py",
    "src\orchestration\gold_recovery_supervisor.py",
    "src\orchestration\gold_recovery.py",
    "src\orchestration\gold_recovery_executor.py",
    "src\orchestration\gold_recovery_state.py",
    "src\orchestration\gold_execution_state.py",
    "src\orchestration\gold_expected_cycles.py",
    "src\orchestration\gold_readiness.py",
    "src\observability\__init__.py",
    "src\observability\events.py",
    "src\observability\gold_recovery_observability.py",
    "config\calendars\b3\2026.json"
)

foreach ($requiredFile in $requiredFiles) {
    $requiredPath = Join-Path `
        $packageDirectory `
        $requiredFile

    if (-not (Test-Path $requiredPath)) {
        throw (
            "Required Lambda package file missing: " +
            $requiredFile
        )
    }

    Write-Host "OK: $requiredFile"
}

Write-Host
Write-Host "Running Python import and calendar smoke test..."

$smokeTestPath = Join-Path `
    $buildDirectory `
    "import_smoke_test.py"

$smokeTestContent = @'
import importlib
from datetime import date

modules = [
    "src.orchestration.b3_trading_calendar",
    "src.orchestration.gold_readiness",
    "src.observability.events",
    "src.observability.gold_recovery_observability",
    "src.orchestration.gold_expected_cycles",
    "src.orchestration.gold_recovery",
    "src.orchestration.gold_recovery_executor",
    "src.orchestration.gold_recovery_supervisor",
]

for module_name in modules:
    importlib.import_module(module_name)
    print("IMPORT OK: " + module_name)

from src.orchestration.b3_trading_calendar import (
    classify_date,
    load_b3_calendar,
    previous_trading_day,
)

calendar = load_b3_calendar(
    year=2026
)

if calendar.get("year") != 2026:
    raise RuntimeError(
        "B3 calendar smoke test failed: invalid year."
    )

print(
    "CALENDAR OK: "
    "config/calendars/b3/2026.json"
)

holiday = classify_date(
    date(2026, 10, 12)
)

if holiday.get("status") != "B3_HOLIDAY":
    raise RuntimeError(
        "B3 calendar smoke test failed: "
        "2026-10-12 must be B3_HOLIDAY."
    )

if holiday.get("expected") is not False:
    raise RuntimeError(
        "B3 calendar smoke test failed: "
        "2026-10-12 must not be expected."
    )

print(
    "CALENDAR CLASSIFICATION OK: "
    "2026-10-12=B3_HOLIDAY"
)

previous_date = previous_trading_day(
    date(2026, 10, 13)
)

if previous_date != date(2026, 10, 9):
    raise RuntimeError(
        "B3 calendar smoke test failed: "
        "previous trading day for "
        "2026-10-13 must be 2026-10-09."
    )

print(
    "CALENDAR D-1 OK: "
    "2026-10-13 -> 2026-10-09"
)
'@

Set-Content `
    -Path $smokeTestPath `
    -Value $smokeTestContent `
    -Encoding utf8

$previousPythonPath = $env:PYTHONPATH

try {
    $env:PYTHONPATH = $packageDirectory

    Push-Location $packageDirectory

    try {
        & python $smokeTestPath

        $pythonExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($null -eq $previousPythonPath) {
        Remove-Item Env:PYTHONPATH `
            -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $previousPythonPath
    }

    Remove-Item `
        $smokeTestPath `
        -Force `
        -ErrorAction SilentlyContinue
}

if ($pythonExitCode -ne 0) {
    throw (
        "Python import/calendar smoke test failed " +
        "with exit code $pythonExitCode."
    )
}

Write-Host
Write-Host "SMOKE OK: supervisor dependency graph and B3 calendar are complete"

Write-Host
Write-Host "Creating deterministic deployment ZIP..."

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$zipStream = [System.IO.File]::Open(
    $zipPath,
    [System.IO.FileMode]::Create
)

$zipArchive = New-Object `
    System.IO.Compression.ZipArchive(
        $zipStream,
        [System.IO.Compression.ZipArchiveMode]::Create,
        $false
    )

try {
    $files = Get-ChildItem `
        $packageDirectory `
        -Recurse `
        -File |
        Sort-Object FullName

    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring(
            $packageDirectory.Length + 1
        )

        $entryName = $relativePath -replace "\\", "/"

        $entry = $zipArchive.CreateEntry(
            $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal
        )

        $entry.LastWriteTime = [DateTimeOffset]$fixedTimestamp

        $entryStream = $entry.Open()

        try {
            $fileStream = [System.IO.File]::OpenRead(
                $file.FullName
            )

            try {
                $fileStream.CopyTo(
                    $entryStream
                )
            }
            finally {
                $fileStream.Dispose()
            }
        }
        finally {
            $entryStream.Dispose()
        }
    }
}
finally {
    $zipArchive.Dispose()
    $zipStream.Dispose()
}

if (-not (Test-Path $zipPath)) {
    throw "Lambda deployment ZIP was not created."
}

$zipFile = Get-Item $zipPath

Write-Host
Write-Host "Validating deployment ZIP..."

$zipArchive = [System.IO.Compression.ZipFile]::OpenRead(
    $zipPath
)

try {
    $zipEntries = $zipArchive.Entries.FullName |
        ForEach-Object {
            $_ -replace "\\", "/"
        }

    foreach ($requiredFile in $requiredFiles) {
        $requiredEntry = (
            $requiredFile -replace "\\", "/"
        )

        if ($zipEntries -notcontains $requiredEntry) {
            throw (
                "Required ZIP entry missing: " +
                $requiredEntry
            )
        }

        Write-Host "ZIP OK: $requiredEntry"
    }

    Write-Host "ZIP OK: supervisor package is complete"
}
finally {
    $zipArchive.Dispose()
}

$zipHash = Get-FileHash `
    -Path $zipPath `
    -Algorithm SHA256

Write-Host
Write-Host "======================================"
Write-Host "Build completed successfully"
Write-Host "======================================"
Write-Host "ZIP:    $($zipFile.FullName)"
Write-Host "Size:   $($zipFile.Length) bytes"
Write-Host "SHA256: $($zipHash.Hash)"
