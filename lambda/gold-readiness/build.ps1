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
    "gold_readiness.zip"

$sourceRoot = Join-Path `
    $repositoryRoot `
    "src"

$fixedTimestamp = [DateTime]::SpecifyKind(
    (Get-Date "2026-01-01T00:00:00"),
    [DateTimeKind]::Utc
)

Write-Host "======================================"
Write-Host "Gold Readiness Lambda build"
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

Write-Host
Write-Host "Copying coordinator source..."

Copy-Item `
    -Path (
        Join-Path `
            $sourceRoot `
            "__init__.py"
    ) `
    -Destination (
        Join-Path `
            $packageSrcDirectory `
            "__init__.py"
    )

Copy-Item `
    -Path (
        Join-Path `
            $sourceRoot `
            "orchestration\__init__.py"
    ) `
    -Destination (
        Join-Path `
            $packageOrchestrationDirectory `
            "__init__.py"
    )

Copy-Item `
    -Path (
        Join-Path `
            $sourceRoot `
            "orchestration\gold_readiness_coordinator.py"
    ) `
    -Destination (
        Join-Path `
            $packageOrchestrationDirectory `
            "gold_readiness_coordinator.py"
    )

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
    "src\orchestration\gold_readiness_coordinator.py"
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

    $requiredZipEntries = @(
        "src/__init__.py",
        "src/orchestration/__init__.py",
        "src/orchestration/gold_readiness_coordinator.py"
    )

    foreach ($requiredEntry in $requiredZipEntries) {
        if ($zipEntries -notcontains $requiredEntry) {
            throw (
                "Required ZIP entry missing: " +
                $requiredEntry
            )
        }

        Write-Host "ZIP OK: $requiredEntry"
    }

    Write-Host "ZIP OK: coordinator package is complete"
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