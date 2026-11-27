#Requires -Version 7
# Edition 8 P8-4 formal rerun: full unit suite at T8''' 2263b246 (one run, no automatic rerun).
# Called by runner p84_t8ppp_runner.ps1 (affinity/priority/lease are set there; children inherit).
$ErrorActionPreference = 'Continue'
$Here = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\p84_t8ppp_2263b246'
$Out = "$Here\out"
$Wt = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge3'
$Expect = '2263b2461238da7f93eda147838c01c847315561'
$Py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
$Dev = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$Tools = 'C:\Users\jinbeom\.claude\tools\cpu-scheduler'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
function Log($m) { "$((Get-Date).ToString('o')) $m" | Out-File -FilePath "$Out\p84_driver.log" -Append -Encoding utf8 }
function Stop-Run($m) { Log "[stop] $m"; "$m" | Out-File -FilePath "$Out\p84.stop" -Encoding utf8; exit 3 }

if ((Test-Path "$Out\p84.done") -or (Test-Path "$Out\p84.stop") -or (Test-Path "$Out\junit_T8ppp_2263b246.xml")) {
    Stop-Run 'out folder already has results (never rerun automatically)'
}
Log '[start] P8-4 T8ppp 2263b246'
$Head = (& git -C $Wt rev-parse HEAD).Trim()
$StatusBefore = @(& git -C $Wt status --porcelain --ignored)
"HEAD=$Head" | Out-File "$Out\git_before.txt" -Encoding utf8
$StatusBefore | Out-File "$Out\git_before.txt" -Append -Encoding utf8
if ($Head -ne $Expect) { Stop-Run "HEAD $Head is not $Expect" }
if ($StatusBefore.Count -ne 0) { Stop-Run "worktree not clean (status --porcelain --ignored non-empty)" }

$env:OUTRIGGER_RECORDS_ROOT = 'C:\workspace\outrigger_control'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = "$Out\numba_cache"
$env:HYPOTHESIS_STORAGE_DIRECTORY = "$Out\hypothesis"
New-Item -ItemType Directory -Force -Path $env:NUMBA_CACHE_DIR, $env:HYPOTHESIS_STORAGE_DIRECTORY | Out-Null

"$((Get-Date).ToString('o'))" | Out-File "$Out\time_start.txt" -Encoding utf8
$PyArgs = @('-I', '-B', '-m', 'pytest', '05_tests/unit', '-n', '12', '--dist', 'loadfile', '-p', 'no:cacheprovider',
    "--junitxml=$Out\junit_T8ppp_2263b246.xml")
$p = Start-Process -FilePath $Py -ArgumentList $PyArgs -WorkingDirectory $Wt -NoNewWindow -PassThru `
    -RedirectStandardOutput "$Out\console_T8ppp_2263b246.log" -RedirectStandardError "$Out\console_T8ppp_2263b246.err.log"
Log "[pytest] pid $($p.Id)"
$s = Start-Process -FilePath $Dev -ArgumentList @('-I', '-B', "$Tools\sample.py", '--pid', "$($p.Id)", '--interval', '5',
    '--out', "$Out\p84_T8ppp.sample.json") -WindowStyle Hidden -PassThru
$p.WaitForExit()
$code = $p.ExitCode
"$((Get-Date).ToString('o'))" | Out-File "$Out\time_end.txt" -Encoding utf8
Log "[end] pytest exit=$code"
$null = $s.WaitForExit(60000)

$StatusAfter = @(& git -C $Wt status --porcelain --ignored)
$StatusAfter | Out-File "$Out\git_after.txt" -Encoding utf8
$Pyc = @($StatusAfter | Where-Object { $_ -match '__pycache__' })
$Pyc | Out-File "$Out\pycache_paths.txt" -Encoding utf8
Log "[after] status lines=$($StatusAfter.Count) pycache lines=$($Pyc.Count) head=$((& git -C $Wt rev-parse HEAD).Trim())"
"exit=$code" | Out-File "$Out\p84.done" -Encoding utf8
exit $code
