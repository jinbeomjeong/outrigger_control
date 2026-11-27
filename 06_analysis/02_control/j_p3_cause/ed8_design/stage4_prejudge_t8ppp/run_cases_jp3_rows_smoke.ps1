# T8''' D-1 value-free smoke: J-P3 judged row count of the P8-2 cases lines (expected 10).
# Prints and keeps only counts and structural reasons (cases_jp3_rows_smoke.py); never a status,
# a breach count or a line value. The blind rows file is named here only, never listed or read
# by anything else. Run by the main session.
$ErrorActionPreference = 'Stop'
$Judge = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge3'
$JudgeHead = '2263b2461238da7f93eda147838c01c847315561'
$Py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$CaseRows = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248\impl_cases_a1\ed8_cases.jsonl'
$SmokeDir = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\stage4_prejudge_t8ppp'
$SmokePy = Join-Path $SmokeDir 'cases_jp3_rows_smoke.py'
$SmokeOut = Join-Path $SmokeDir 'cases_jp3_rows_smoke.json'

if (-not (Test-Path -LiteralPath $SmokePy)) { throw "smoke script missing: $SmokePy" }
if (Test-Path -LiteralPath $SmokeOut) { throw "output exists (new path only): $SmokeOut" }
$head = (& git -C $Judge rev-parse HEAD).Trim()
if ($head -ne $JudgeHead) { throw "judge HEAD $head is not $JudgeHead" }
$dirty = & git -C $Judge status --porcelain
if ($dirty) { throw 'judge checkout has tracked or untracked changes' }

$env:MKL_THREADING_LAYER = 'TBB'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache\smoke_2263b246'

Push-Location -LiteralPath $Judge
try {
    $dryLines = @(& $Py -I -B $SmokePy --judge-root $Judge --dry)
    $dryCode = $LASTEXITCODE
    $lines = @(& $Py -I -B $SmokePy --judge-root $Judge --rows $CaseRows)
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
$last = if ($lines.Count) { $lines[-1] } else { '' }
[System.IO.File]::WriteAllText($SmokeOut, "$last`n", [System.Text.UTF8Encoding]::new($false))
Write-Output "dry exit $dryCode : $(if ($dryLines.Count) { $dryLines[-1] })"
Write-Output "smoke exit $code"
Write-Output $last
$after = & git -C $Judge status --porcelain
if ($after) { Write-Output 'WARNING: judge checkout changed by the smoke' }
