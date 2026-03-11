# run_full_calibration.ps1
# Scans frontend/sample_data for all *.csv files, runs make_calibration_batch.py
# on each, merges all reviews into one combined batch, and POSTs to the benchmark
# endpoint. Saves the raw JSON response to a timestamped file.

$ErrorActionPreference = "Stop"

# --- Config ------------------------------------------------------------------
$BENCHMARK_URL = "http://localhost:5000/internal/benchmark/batch"
$AUTH_TOKEN    = "Bearer Themepark12"
$TIMEOUT_SEC   = 300
$SCRIPT_DIR    = Split-Path -Parent $MyInvocation.MyCommand.Path
$PYTHON_SCRIPT = Join-Path $SCRIPT_DIR "make_calibration_batch.py"

# --- Timestamp ---------------------------------------------------------------
$timestamp   = Get-Date -Format "yyyyMMdd_HHmmss"
$exportLabel = "full_batch_$timestamp"
$outputFile  = ".\calibration_full_batch_${timestamp}_result.json"

# --- Step 1: Discover CSVs ---------------------------------------------------
$csvFiles = Get-ChildItem -Path $SCRIPT_DIR -Filter "*.csv" -File
Write-Host "CSVs found: $($csvFiles.Count)"

if ($csvFiles.Count -eq 0) {
    Write-Error "No CSV files found in $SCRIPT_DIR - aborting."
    exit 1
}

# --- Step 2: Parse each CSV via make_calibration_batch.py --------------------
$allReviews = [System.Collections.Generic.List[object]]::new()

foreach ($csv in $csvFiles) {
    Write-Host "Processing: $($csv.Name) ..." -NoNewline
    try {
        $rawOutput = python $PYTHON_SCRIPT $csv.FullName 2>&1
        $exitCode  = $LASTEXITCODE

        if ($exitCode -ne 0 -or [string]::IsNullOrWhiteSpace($rawOutput)) {
            Write-Host " WARN: script returned exit $exitCode or empty output - skipping."
            continue
        }

        # Capture only the last non-empty line (stdout) in case stderr leaked through
        $jsonLine = ($rawOutput -split "`n" | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 1).Trim()
        $parsed   = $jsonLine | ConvertFrom-Json
        $reviews  = $parsed.reviews

        if ($null -eq $reviews -or $reviews.Count -eq 0) {
            Write-Host " WARN: 0 reviews parsed - skipping."
            continue
        }

        foreach ($r in $reviews) { $allReviews.Add($r) }
        Write-Host " $($reviews.Count) reviews"
    }
    catch {
        Write-Host " WARN: error processing $($csv.Name): $($_.Exception.Message) - skipping."
    }
}

Write-Host "Total reviews collected: $($allReviews.Count)"

# --- Step 3: Guard - abort if nothing to send --------------------------------
if ($allReviews.Count -eq 0) {
    Write-Error "0 total reviews collected across all CSVs - aborting before HTTP call."
    exit 1
}

# --- Step 4: Build payload ---------------------------------------------------
$payload = @{
    reviews       = $allReviews.ToArray()
    enable_ai     = $true
    fixtures      = $false
    export_report = $true
    export_label  = $exportLabel
} | ConvertTo-Json -Depth 10 -Compress

$payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)

# --- Step 5: POST to benchmark endpoint --------------------------------------
Write-Host "Sending $($allReviews.Count) reviews to $BENCHMARK_URL ..."
Write-Host "Export label: $exportLabel"

try {
    $response = Invoke-WebRequest `
        -Uri $BENCHMARK_URL `
        -Method POST `
        -Headers @{
            "Authorization" = $AUTH_TOKEN
            "Content-Type"  = "application/json"
        } `
        -Body $payloadBytes `
        -TimeoutSec $TIMEOUT_SEC `
        -UseBasicParsing

    # --- Step 6: Save response -----------------------------------------------
    $response.Content | Out-File -FilePath $outputFile -Encoding utf8 -Force
    Write-Host "SUCCESS - response saved to: $outputFile"
}
catch {
    Write-Error "HTTP request failed: $($_.Exception.Message)"
    exit 1
}
