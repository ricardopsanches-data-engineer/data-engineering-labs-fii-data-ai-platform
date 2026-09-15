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
    "daily_ingestion.zip"

$sourceDirectory = Join-Path `
    $repositoryRoot `
    "src"

$fixedTimestamp = [DateTime]::SpecifyKind(
    (Get-Date "2026-01-01T00:00:00"),
    [DateTimeKind]::Utc
)

$dependencies = @(
    "requests==2.34.2",
    "charset-normalizer==3.5.1",
    "idna==3.19",
    "urllib3==2.7.0",
    "certifi==2026.7.22"
)

Write-Host "======================================"
Write-Host "AWS Lambda build"
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

Write-Host "Installing pinned Lambda dependencies..."

python -m pip install `
    --platform manylinux2014_x86_64 `
    --implementation cp `
    --python-version 3.12 `
    --only-binary=:all: `
    --target $packageDirectory `
    $dependencies

if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}

Write-Host
Write-Host "Removing non-runtime package artifacts..."

$binDirectory = Join-Path `
    $packageDirectory `
    "bin"

if (Test-Path $binDirectory) {
    Remove-Item `
        $binDirectory `
        -Recurse `
        -Force

    Write-Host "Removed: bin"
}

Get-ChildItem `
    $packageDirectory `
    -Recurse `
    -File `
    -Filter "RECORD" |
    Where-Object {
        $_.Directory.Name -like "*.dist-info"
    } |
    ForEach-Object {
        $relativePath = $_.FullName.Substring(
            $packageDirectory.Length + 1
        )

        Remove-Item `
            $_.FullName `
            -Force

        Write-Host "Removed: $relativePath"
    }

Write-Host
Write-Host "Copying application source..."

Copy-Item `
    -Path $sourceDirectory `
    -Destination $packageDirectory `
    -Recurse

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
    "src\handlers\daily_ingestion.py",
    "src\pipelines\b3_raw_to_s3.py",
    "src\pipelines\cvm_raw_to_s3.py",
    "src\storage\s3.py",
    "src\ingestion\b3\fingerprint.py",
    "requests\__init__.py"
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
        "src/handlers/daily_ingestion.py",
        "src/pipelines/b3_raw_to_s3.py",
        "src/pipelines/cvm_raw_to_s3.py",
        "src/storage/s3.py",
        "src/ingestion/b3/fingerprint.py",
        "requests/__init__.py"
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

    $unexpectedEntries = $zipEntries |
        Where-Object {
            $_ -match "^bin/" -or
            $_ -match "\.dist-info/RECORD$"
        }

    if ($unexpectedEntries) {
        throw (
            "Non-deterministic artifacts found in ZIP: " +
            ($unexpectedEntries -join ", ")
        )
    }

    Write-Host "ZIP OK: no non-deterministic pip artifacts"
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