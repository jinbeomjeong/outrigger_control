#Requires -Version 7
# 436.9 edition 5 test run from a list file (erratum 5 5-1): the P5-3 set (purpose P5-3) or the
# edition 4a regression record (purpose regression, not a P5-3 judgement). Same environment as
# run_p53_tests.ps1 (E cores 0x0FFF0000, -n 6 --dist loadfile, OUTRIGGER_RECORDS_ROOT = main
# checkout, X10_BASE_ROOT), then junit_skips --critical . --fail-on-skip (every test critical;
# skip and xfail are not passed). Writes junit_<Tag>.xml / .pytest.log / .skips.log and the step
# record junit_<Tag>.record.json (list file and its sha, test files, head, environment, the sha
# of every -HashFiles path, exit codes) in this folder. Never overwrites: an existing output
# stops with exit 2.
#   -Worktree     the run worktree (HEAD = the run commit, clean tracked tree)
#   -X10BaseRoot  a checkout of the commit before X-10 (df95158d; test_x10_rod_fault (i))
#   -ListFile     test file names under 05_tests/unit, or node ids 'test_x.py::test_y', one per
#                 line ('#' lines are comments)
#   -Tag          the output file stem suffix (mandatory)
#   -Purpose      'P5-3' or 'regression' (recorded only)
#   -HashFiles    extra files whose sha256 goes into the record (erratum 5 5-2)
# Exit: 2 = an output exists or a listed file is missing, 3 = git failed or the worktree is not
# clean, else pytest's code if not 0, else junit_skips' code (0 = every listed test ran and passed).
param([Parameter(Mandatory)][string]$Worktree, [Parameter(Mandatory)][string]$X10BaseRoot,
    [Parameter(Mandatory)][string]$ListFile, [Parameter(Mandatory)][string]$Tag,
    [Parameter(Mandatory)][ValidateSet('P5-3', 'regression')][string]$Purpose,
    [string[]]$HashFiles = @(), [int]$Workers = 6)
Set-StrictMode -Version 3
$ErrorActionPreference = 'Stop'

$Python = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
$DevPython = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$JunitSkips = 'C:\Users\jinbeom\.claude\tools\verif\junit_skips.py'
$MainRoot = 'C:\workspace\outrigger_control'
$Critical = '.'
$AffinityMask = 0x0FFF0000

function Get-Sha256([string]$Path) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$Head = (& git -C $Worktree rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or -not $Head) { Write-Host 'STOP: git rev-parse failed'; exit 3 }
$Head = $Head.Trim()
$Status = (& git -C $Worktree status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $Status) { Write-Host 'STOP: the worktree is not clean (or git failed)'; exit 3 }

$Junit = "$PSScriptRoot\junit_$Tag.xml"
$Log = "$PSScriptRoot\junit_$Tag.pytest.log"
$SkipsLog = "$PSScriptRoot\junit_$Tag.skips.log"
$Record = "$PSScriptRoot\junit_$Tag.record.json"
foreach ($Path in @($Junit, $Log, $SkipsLog, $Record)) {
    if (Test-Path -LiteralPath $Path) { Write-Host "STOP: $Path exists (never overwritten; give another -Tag)"; exit 2 }
}
$Names = @(Get-Content -LiteralPath $ListFile | ForEach-Object { $_.Trim() } |
    Where-Object { $_ -and -not $_.StartsWith('#') })
if ($Names.Count -eq 0) { Write-Host "STOP: no test file in $ListFile"; exit 2 }
$Files = @(foreach ($Name in $Names) { "$Worktree\05_tests\unit\$Name" })
foreach ($File in $Files) {
    # a node id 'test_x.py::test_y' checks its file; pytest itself fails on a missing node
    $FilePart = ($File -split '::')[0]
    if (-not (Test-Path -LiteralPath $FilePart -PathType Leaf)) { Write-Host "STOP: $FilePart missing"; exit 2 }
}
$Hashes = [ordered]@{}
# pwsh -File passes an array argument as one comma-joined string
$HashFiles = @($HashFiles | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
foreach ($Path in $HashFiles) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { Write-Host "STOP: $Path missing"; exit 2 }
    $Hashes[$Path] = Get-Sha256 $Path
}

# E cores (the P cores stay free for the run steps), no cache files in the worktree
(Get-Process -Id $PID).ProcessorAffinity = [IntPtr]$AffinityMask
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OUTRIGGER_RECORDS_ROOT = $MainRoot
$env:X10_BASE_ROOT = $X10BaseRoot
$env:MKL_THREADING_LAYER = 'TBB'
$Started = (Get-Date).ToString('o')
Set-Location -LiteralPath $Worktree
& $Python -m pytest -q -p no:cacheprovider -n $Workers --dist loadfile --junitxml $Junit @Files *> $Log
$PytestCode = $LASTEXITCODE
Write-Host "pytest exit $PytestCode (head $Head) -> $Junit"
& $DevPython -I -B $JunitSkips $Junit --critical $Critical --fail-on-skip *> $SkipsLog
$SkipsCode = $LASTEXITCODE
Write-Host "junit_skips exit $SkipsCode -> $SkipsLog"

$StepRecord = [ordered]@{
    purpose = $Purpose
    head = $Head
    worktree = $Worktree
    list_file = $ListFile
    list_file_sha256 = Get-Sha256 $ListFile
    test_files = $Names
    environment = [ordered]@{
        python = $Python; workers = $Workers; dist = 'loadfile'
        affinity_mask = ('0x{0:X8}' -f $AffinityMask)
        OUTRIGGER_RECORDS_ROOT = $MainRoot; X10_BASE_ROOT = $X10BaseRoot; MKL_THREADING_LAYER = 'TBB'
    }
    junit_skips = [ordered]@{ critical = $Critical; fail_on_skip = $true }
    hashed_files = $Hashes
    started = $Started
    ended = (Get-Date).ToString('o')
    pytest_exit = $PytestCode
    junit_skips_exit = $SkipsCode
    junit = $Junit
    junit_sha256 = Get-Sha256 $Junit
}
$Json = ($StepRecord | ConvertTo-Json -Depth 5).Replace("`r`n", "`n") + "`n"
[IO.File]::WriteAllText($Record, $Json, [Text.UTF8Encoding]::new($false))
Write-Host "record -> $Record"
if ($PytestCode -ne 0) { exit $PytestCode }
exit $SkipsCode
