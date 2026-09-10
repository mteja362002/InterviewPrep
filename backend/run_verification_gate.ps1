# =====================================================================
#  FINAL VERIFICATION GATE — runtime harness
#  Run from:  InterviewPrep\backend
#      powershell -ExecutionPolicy Bypass -File .\run_verification_gate.ps1
#
#  Produces, under ..\test_reports\ :
#      gate_full_suite.xml         broader regression suite (superset of baseline)
#      gate_new_tests.xml          the two new regression files
#      gate_regression_delta.json  per-test-identity diff vs the 192-test baseline
#      gate_user5.json             User 5 runtime capture
#      gate_ai_timing.json         cold / cache-hit / concurrent timing matrix
#      gate_console.txt            full console transcript
#
#  pytest.ini pins "-n 2 --dist loadscope"; this script does NOT override it.
#  Steps 4 and 5 hit the real database; step 5 also spends real API credits
#  (two KB generations).
# =====================================================================

$ErrorActionPreference = "Continue"
$ROOT    = Split-Path -Parent $MyInvocation.MyCommand.Definition
$REPORTS = Join-Path (Split-Path -Parent $ROOT) "test_reports"
$PY      = Join-Path $ROOT ".venv\Scripts\python.exe"
$LOG     = Join-Path $REPORTS "gate_console.txt"

if (-not (Test-Path $PY)) { $PY = "python" }
New-Item -ItemType Directory -Force -Path $REPORTS | Out-Null
Set-Location $ROOT
Start-Transcript -Path $LOG -Force | Out-Null

function Section($n, $t) {
  Write-Host ""
  Write-Host ("=" * 72)
  Write-Host "  STEP $n — $t"
  Write-Host ("=" * 72)
}

Write-Host "python : $PY"
Write-Host "root   : $ROOT"
Write-Host "reports: $REPORTS"
& $PY --version

# ---------------------------------------------------------------------
Section 1 "New regression tests (the two files this gate added)"
# ---------------------------------------------------------------------
# These ran under a hand-rolled shim during static review because pytest
# could not be installed in the review sandbox. This is their first real
# pytest execution — it is the authoritative result.
& $PY -m pytest `
    tests/test_provenance_status_regression.py `
    tests/test_canonical_relationship_authority.py `
    -v --junitxml="$REPORTS\gate_new_tests.xml"
$newTestsExit = $LASTEXITCODE
Write-Host "exit code: $newTestsExit"

# ---------------------------------------------------------------------
Section 2 "Broader regression suite (full backend tests/)"
# ---------------------------------------------------------------------
# A superset of the 192-test baseline. Running everything avoids the trap
# of a narrower selection appearing green only because it skipped tests.
& $PY -m pytest tests/ `
    --junitxml="$REPORTS\gate_full_suite.xml" `
    -q
$fullExit = $LASTEXITCODE
Write-Host "exit code: $fullExit"

# ---------------------------------------------------------------------
Section 3 "Regression delta vs the 188-passed / 4-failed baseline"
# ---------------------------------------------------------------------
& $PY scratch_gate_compare_regression.py "$REPORTS\gate_full_suite.xml" "$REPORTS\gate_new_tests.xml"

# ---------------------------------------------------------------------
Section 4 "User 5 runtime capture (real DB, read-only)"
# ---------------------------------------------------------------------
& $PY scratch_gate_user5.py

# ---------------------------------------------------------------------
Section 5 "AI generation timing + single-flight (real provider, ~2 calls)"
# ---------------------------------------------------------------------
Write-Host "Spends real API credits. Ctrl-C within 5s to skip."
Start-Sleep -Seconds 5
& $PY scratch_gate_ai_timing.py

# ---------------------------------------------------------------------
Section 6 "Deployment topology (single-flight scope evidence)"
# ---------------------------------------------------------------------
# asyncio.Lock is process-local. Whether that is sufficient depends on how
# uvicorn is actually launched. Capture the evidence rather than assume.
Write-Host "--- uvicorn/gunicorn invocations found in repo ---"
Select-String -Path (Join-Path (Split-Path -Parent $ROOT) "*") `
    -Pattern "uvicorn|gunicorn|--workers|WEB_CONCURRENCY" `
    -Include *.json,*.toml,*.cfg,*.ini,*.yaml,*.yml,*.ps1,*.sh,*.bat,Procfile,Dockerfile `
    -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -notmatch "node_modules|\.venv|__pycache__|\.git" } |
  Select-Object -First 30 |
  ForEach-Object { Write-Host ("  " + $_.Path + ":" + $_.LineNumber + "  " + $_.Line.Trim()) }
Write-Host "--- running python processes serving the app ---"
Get-CimInstance Win32_Process -Filter "Name like '%python%'" -ErrorAction SilentlyContinue |
  Select-Object ProcessId, CommandLine |
  ForEach-Object { Write-Host ("  PID " + $_.ProcessId + "  " + $_.CommandLine) }

# ---------------------------------------------------------------------
Write-Host ""
Write-Host ("=" * 72)
Write-Host "  DONE"
Write-Host ("=" * 72)
Write-Host "new-tests pytest exit : $newTestsExit   (0 = all passed)"
Write-Host "full-suite pytest exit: $fullExit       (1 = some failed, expected: the 4 known)"
Write-Host ""
Write-Host "Paste back:"
Write-Host "  1. this console output   ($LOG)"
Write-Host "  2. $REPORTS\gate_regression_delta.json"
Write-Host "  3. $REPORTS\gate_user5.json"
Write-Host "  4. $REPORTS\gate_ai_timing.json"
Stop-Transcript | Out-Null
