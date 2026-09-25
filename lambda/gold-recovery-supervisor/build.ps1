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

Write-Host
Write-Host "Copying supervisor source..."

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
    "src\orchestration\gold_recovery_supervisor.py",
    "src\orchestration\gold_recovery.py",
    "src\orchestration\gold_recovery_executor.py",
    "src\orchestration\gold_recovery_state.py",
    "src\orchestration\gold_execution_state.py",
    "src\orchestration\gold_expected_cycles.py",
    "src\orchestration\gold_readiness.py",
    "src\observability\__init__.py",
    "src\observability\events.py",
    "src\observability\gold_recovery_observability.py"
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
Write-Host "Running Python import smoke test..."

$smokeTestPath = Join-Path `
    $buildDirectory `
    "import_smoke_test.py"

$smokeTestContent = @'
import importlib

modules = [
    "src.orchestration.gold_readiness",
    "src.observability.events",
    "src.observability.gold_recovery_observability",
    "src.orchestration.gold_recovery",
    "src.orchestration.gold_recovery_executor",
    "src.orchestration.gold_recovery_supervisor",
]

for module_name in modules:
    importlib.import_module(module_name)
    print("IMPORT OK: " + module_name)
'@

Set-Content `
    -Path $smokeTestPath `
    -Value $smokeTestContent `
    -Encoding utf8

$previousPythonPath = $env:PYTHONPATH

try {
    $env:PYTHONPATH = $packageDirectory

    & python $smokeTestPath

    $pythonExitCode = $LASTEXITCODE
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
        "Python import smoke test failed " +
        "with exit code $pythonExitCode."
    )
}

Write-Host "IMPORT OK: supervisor dependency graph is complete"

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