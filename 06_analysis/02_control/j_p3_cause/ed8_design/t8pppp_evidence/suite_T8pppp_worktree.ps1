#Requires -Version 7
# P8-4 check of the T8'''' working tree (ed8-judge4): full unit suite, one run.
$ErrorActionPreference = 'Continue'
$Out = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\c52f3f13-1809-41e7-8ed4-76fbbd933dd2\scratchpad\python-t8pppp\suite'
$Wt = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4'
$Py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$env:OUTRIGGER_RECORDS_ROOT = 'C:\workspace\outrigger_control'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = "$Out\numba_cache"
$env:HYPOTHESIS_STORAGE_DIRECTORY = "$Out\hypothesis"
New-Item -ItemType Directory -Force -Path $env:NUMBA_CACHE_DIR, $env:HYPOTHESIS_STORAGE_DIRECTORY | Out-Null
"HEAD=$((& git -C $Wt rev-parse HEAD).Trim())" | Out-File "$Out\git_before.txt" -Encoding utf8
@(& git -C $Wt status --porcelain --ignored) | Out-File "$Out\git_before.txt" -Append -Encoding utf8
"$((Get-Date).ToString('o'))" | Out-File "$Out\time_start.txt" -Encoding utf8
$PyArgs = @('-I', '-B', '-m', 'pytest', '05_tests/unit', '-n', '12', '--dist', 'loadfile', '-p', 'no:cacheprovider',
    "--junitxml=$Out\junit_T8pppp_worktree.xml")
$p = Start-Process -FilePath $Py -ArgumentList $PyArgs -WorkingDirectory $Wt -NoNewWindow -PassThru `
    -RedirectStandardOutput "$Out\suite_T8pppp_worktree.txt" -RedirectStandardError "$Out\suite_T8pppp_worktree.err.txt"
"pid=$($p.Id)" | Out-File "$Out\pid.txt" -Encoding utf8
$p.WaitForExit()
"$((Get-Date).ToString('o'))" | Out-File "$Out\time_end.txt" -Encoding utf8
@(& git -C $Wt status --porcelain --ignored) | Out-File "$Out\git_after.txt" -Encoding utf8
"exit=$($p.ExitCode)" | Out-File "$Out\suite.done" -Encoding utf8
