#Requires -Version 7
# Erratum 2 2-2: the full unit suite (every 05_tests/unit/test_*.py) of one worktree, the same
# command on both sides - the baseline worktree at the merge-base of the run commit and master,
# then the run worktree. tools/verif/worktree_tests.py copies the test files, reads the stored
# data (07_results) from the main checkout and keeps the run folder; the JUnit lands in
# OUT_DIR\junit.xml. Then:
#   -Side base  jp3_ed6_suite.py baseline -> OUT_DIR\existing_failures.txt (+ .sha256)
#   -Side run   jp3_ed6_suite.py judge against the baseline list (its sha256 given)
# OUT_DIR must not exist and must lie outside the worktree and the main checkout (the runner
# folder ~\.claude\runners\outrigger-ed6-suite\SIDE). No automatic rerun. Exit code: the
# suite tool's (base: 0 list written; run: 0 pass / 1 failed / 2 not judgeable / 3 error);
# 3 also when the JUnit is missing.
param([Parameter(Mandatory)][ValidateSet('base', 'run')][string]$Side,
    [Parameter(Mandatory)][string]$Worktree, [Parameter(Mandatory)][string]$OutDir,
    [Parameter(Mandatory)][string]$ExpectCommit,
    [string]$BaselineList = '', [string]$BaselineSha256 = '', [int]$TimeoutS = 36000,
    [string]$TestGlob = '05_tests/unit/test_*.py')  # -TestGlob: a smoke check only; both sides use the default
$ErrorActionPreference = 'Stop'
$MainRoot = 'C:\workspace\outrigger_control'
$DevPython = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$TestPython = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
$VerifTools = 'C:\Users\jinbeom\.claude\tools\verif'
$Suite = "$PSScriptRoot\..\..\..\..\..\04_scripts\04_hydraulic\coupled\jp3_ed6_suite.py"

function Stop-Suite([int]$Code, [string]$Reason) { Write-Host "STOP: $Reason"; exit $Code }

if (Test-Path -LiteralPath $OutDir) { Stop-Suite 2 "$OutDir exists (never overwritten)" }
if ($Side -eq 'run' -and (-not $BaselineList -or -not $BaselineSha256)) {
    Stop-Suite 2 '-Side run needs -BaselineList and -BaselineSha256'
}
$Head = (& git -C $Worktree rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or $Head.Trim() -ne $ExpectCommit) { Stop-Suite 3 "HEAD of $Worktree is not $ExpectCommit" }
$Status = (& git -C $Worktree status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $Status) { Stop-Suite 3 "$Worktree is not clean (or git failed)" }
New-Item -ItemType Directory -Path "$OutDir\scratch" | Out-Null

$env:PYTHONDONTWRITEBYTECODE = '1'
& $DevPython -I -B "$VerifTools\worktree_tests.py" --worktree $Worktree --data-root $MainRoot `
    --python $TestPython --scratch "$OutDir\scratch" --test $TestGlob `
    --probe-module outrigger_sim --keep --timeout $TimeoutS --out "$OutDir\worktree_tests.md" *> "$OutDir\worktree_tests.log"
$ToolCode = $LASTEXITCODE  # 1 = findings (failures, skips): judged below from the JUnit
$Junit = @(Get-ChildItem -LiteralPath "$OutDir\scratch" -Recurse -Filter 'junit.xml')
if ($Junit.Count -ne 1) { Stop-Suite 3 "worktree_tests exit $ToolCode, $($Junit.Count) junit.xml files" }
Copy-Item -LiteralPath $Junit[0].FullName -Destination "$OutDir\junit.xml"
[ordered]@{ side = $Side; worktree = $Worktree; head = $ExpectCommit; worktree_tests_exit = $ToolCode
    junit_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath "$OutDir\junit.xml").Hash.ToLower() } |
    ConvertTo-Json | Set-Content -LiteralPath "$OutDir\suite_record.json" -Encoding utf8NoBOM

if ($Side -eq 'base') {
    & $DevPython -I -B $Suite baseline --junit "$OutDir\junit.xml" --merge-base $ExpectCommit `
        --out "$OutDir\existing_failures.txt"
} else {
    & $DevPython -I -B $Suite judge --junit "$OutDir\junit.xml" --baseline-list $BaselineList `
        --baseline-sha256 $BaselineSha256 --out "$OutDir\suite_judgement.json"
}
exit $LASTEXITCODE
