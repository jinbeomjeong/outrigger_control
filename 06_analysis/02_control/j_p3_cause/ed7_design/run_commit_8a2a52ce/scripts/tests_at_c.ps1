#Requires -Version 7
# The edition 7 tests at the run commit C (worktree HEAD and clean state recorded before / after).
param([Parameter(Mandatory)][string]$Worktree, [Parameter(Mandatory)][string]$OutDir)
$ErrorActionPreference = 'Continue'
$Py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Get-Identity {
    $Head = (& git -C $Worktree rev-parse HEAD).Trim()
    $Status = @(& git -C $Worktree status --porcelain --untracked-files=no)
    return [ordered]@{ head = $Head; is_clean = ($Status.Count -eq 0); time = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') }
}

$Record = [ordered]@{ interpreter = $Py; start = Get-Identity; runs = [ordered]@{} }
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OUTRIGGER_RECORDS_ROOT = 'C:\workspace\outrigger_control'
$env:MKL_THREADING_LAYER = 'TBB'
Set-Location -LiteralPath $Worktree
$Sets = [ordered]@{
    units   = @('05_tests/unit/test_ed7_run_commit.py', '05_tests/unit/test_ed7_units.py')
    harness = @('05_tests/unit/test_ed7_harness.py')
}
foreach ($Name in $Sets.Keys) {
    & $Py -B -m pytest -p no:cacheprovider -rs -q @($Sets[$Name]) --junitxml "$OutDir\junit_$Name.xml" *> "$OutDir\pytest_$Name.txt"
    $Record.runs[$Name] = [ordered]@{ files = $Sets[$Name]; exit_code = $LASTEXITCODE
        summary = (Get-Content -LiteralPath "$OutDir\pytest_$Name.txt" | Select-Object -Last 1) }
}
$Record['end'] = Get-Identity
$Record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$OutDir\tests_record.json" -Encoding utf8NoBOM
Write-Host ($Record | ConvertTo-Json -Depth 5 -Compress)
