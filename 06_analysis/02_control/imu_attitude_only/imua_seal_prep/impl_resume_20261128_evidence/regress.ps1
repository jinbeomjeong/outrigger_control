param([Parameter(Mandatory = $true)][string]$Label)
# Targeted regression tests of the A-type changes (worktree v5-imua, dynamics-dev).
$Wt = "C:\workspace\outrigger_control\.claude\worktrees\v5-imua"
$Scratch = "C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\c52f3f13-1809-41e7-8ed4-76fbbd933dd2\scratchpad\python-imua"
$env:MKL_THREADING_LAYER = "TBB"; $env:MKL_NUM_THREADS = "1"; $env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"; $env:NUMBA_NUM_THREADS = "1"; $env:PYTHONDONTWRITEBYTECODE = "1"
$env:COVERAGE_FILE = Join-Path $Scratch ".coverage_$Label"
$tests = @(
    "05_tests/unit/test_imua_rerun.py", "05_tests/unit/test_imua_replay.py",
    "05_tests/unit/test_imu_a_harness.py", "05_tests/unit/test_v5_rerun.py",
    "05_tests/unit/test_v5_setting_records.py", "05_tests/unit/test_v5_switch_tags.py",
    "05_tests/unit/test_b5_baseline_compare.py", "05_tests/unit/test_b5_ind_las.py",
    "05_tests/unit/test_s9_slope_fix_candidates.py", "05_tests/unit/test_s9_soil_slope.py",
    "05_tests/unit/test_chrono_t45_replay.py", "05_tests/unit/test_imu_attitude_study.py",
    "05_tests/unit/test_resume4368.py", "05_tests/unit/test_resume4368_rev1.py",
    "05_tests/unit/test_d1_harness_paths.py", "05_tests/unit/test_imua_check_judge.py",
    "05_tests/unit/test_r79_controller_tag.py", "04_scripts/04_hydraulic/coupled/test_las_t3.py"
)
Set-Location $Wt
& C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -B -m pytest -q -p no:cacheprovider -m "not slow" `
    --junitxml "$Scratch\junit_$Label.xml" --durations=8 `
    --cov=04_scripts/04_hydraulic/coupled --cov-branch --cov-report="json:$Scratch\cov_$Label.json" `
    --cov-report=term:skip-covered @tests 2>&1 | Out-File -Encoding utf8 "$Scratch\regress_$Label.log"
"exit $LASTEXITCODE"
