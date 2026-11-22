#Requires -Version 7
# 436.9 edition 5 P5-3 (spec v5 5, 7.2; prelaunch audit W-2): the unit tests of 7.2 at a run
# commit with the X-10 bit-identity base, the junit kept in this folder (committed with the
# run's prelaunch outputs), then junit_skips --critical ... --fail-on-skip (skip and xfail are
# not passed). Never overwrites a junit file: a rerun takes -Tag.
#   -Worktree     the run worktree (HEAD = the run commit, clean tracked tree)
#   -X10BaseRoot  a checkout of the commit before X-10 (df95158d; test_x10_rod_fault (i))
#   -Tag          the junit file stem suffix (default: the run commit's first 8 characters)
# Exit: pytest's code if not 0, else junit_skips' code (0 = every test ran and passed).
param([Parameter(Mandatory)][string]$Worktree, [Parameter(Mandatory)][string]$X10BaseRoot,
    [string]$Tag = '', [int]$Workers = 6)
Set-StrictMode -Version 3
$ErrorActionPreference = 'Stop'

$Python = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
$DevPython = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$JunitSkips = 'C:\Users\jinbeom\.claude\tools\verif\junit_skips.py'
$MainRoot = 'C:\workspace\outrigger_control'
$Critical = 'test_x10_rod_fault|test_jp3_rev6|test_jp3_12b_tools|test_jp3_ed5_erratum|test_jp3_j9main|test_jp3_ckdrop|test_jp3_p5_fixed_values|test_jp3_p51_compare|test_jp3_ed5_prelaunch_fix'

$Head = (& git -C $Worktree rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { Write-Host 'STOP: git rev-parse failed'; exit 3 }
$Status = (& git -C $Worktree status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $Status) { Write-Host 'STOP: the worktree is not clean (or git failed)'; exit 3 }
if (-not $Tag) { $Tag = $Head.Substring(0, 8) }
$Junit = "$PSScriptRoot\junit_$Tag.xml"
$Log = "$PSScriptRoot\junit_$Tag.pytest.log"
$SkipsLog = "$PSScriptRoot\junit_$Tag.skips.log"
foreach ($Path in @($Junit, $Log, $SkipsLog)) {
    if (Test-Path -LiteralPath $Path) { Write-Host "STOP: $Path exists (never overwritten; give -Tag)"; exit 2 }
}

# E cores (the P cores stay free for the run steps), no cache files in the worktree
(Get-Process -Id $PID).ProcessorAffinity = [IntPtr]0x0FFF0000
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OUTRIGGER_RECORDS_ROOT = $MainRoot
$env:X10_BASE_ROOT = $X10BaseRoot
$env:MKL_THREADING_LAYER = 'TBB'
$Files = @(Get-ChildItem -LiteralPath "$Worktree\05_tests\unit" -Filter 'test_jp3_*.py' | ForEach-Object { $_.FullName }) +
    @("$Worktree\05_tests\unit\test_x10_rod_fault.py")
Set-Location -LiteralPath $Worktree
& $Python -m pytest -q -p no:cacheprovider -n $Workers --dist loadfile --junitxml $Junit @Files *> $Log
$PytestCode = $LASTEXITCODE
Write-Host "pytest exit $PytestCode (head $Head) -> $Junit"
& $DevPython -I -B $JunitSkips $Junit --critical $Critical --fail-on-skip *> $SkipsLog
$SkipsCode = $LASTEXITCODE
Write-Host "junit_skips exit $SkipsCode -> $SkipsLog"
if ($PytestCode -ne 0) { exit $PytestCode }
exit $SkipsCode
