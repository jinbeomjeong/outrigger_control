# C-1 regression: every 05_tests/unit file that names run_S8C / run_S9 / imua_chrono + the A-type harness tests,
# Chrono-dev, not slow, 8 workers on P cores (no reservation at start, checked with status.py).
$ErrorActionPreference = 'Stop'
$sp = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\c52f3f13-1809-41e7-8ed4-76fbbd933dd2\scratchpad\cad-imua-c1'
$wt = 'C:\workspace\outrigger_control\.claude\worktrees\v5-imua'
Set-Location $wt
$env:HYPOTHESIS_STORAGE_DIRECTORY = "$sp\hyp"
$files = @(Get-ChildItem "$wt\05_tests\unit\test_*.py" | Where-Object {
    (Select-String -Path $_.FullName -Pattern 'run_S8C|run_S9|imua_chrono' -Quiet) }) | ForEach-Object { "05_tests/unit/$($_.Name)" }
$files += @('05_tests/unit/test_imu_a_harness.py', '05_tests/unit/test_imua_expected_sensor.py', '05_tests/unit/test_chrono_t45_replay.py')
$files = $files | Sort-Object -Unique
"files $($files.Count)" | Set-Content "$sp\regress_files.txt"
$files | Add-Content "$sp\regress_files.txt"
& C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -B -X utf8 -m pytest @files -q -p no:cacheprovider -m "not slow" -n 8 --junitxml "$sp\junit_c1.xml" *> "$sp\regress_c1.log"
"rc=$LASTEXITCODE" | Add-Content "$sp\regress_c1.log"
