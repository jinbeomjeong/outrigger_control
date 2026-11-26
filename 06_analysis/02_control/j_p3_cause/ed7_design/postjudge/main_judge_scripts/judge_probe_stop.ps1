$ErrorActionPreference = 'Stop'
$env:MKL_THREADING_LAYER = 'TBB'
$env:NUMBA_CACHE_DIR = "$env:TEMP\ed7_judge_numba"
$dpy  = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$main = 'C:\workspace\outrigger_control'
$c    = "$main\06_analysis\02_control\j_p3_cause"
$wtj  = "$main\.claude\worktrees\ed7-judge"
$runs = "$c\j9_runs\8a2a52ce"
$J    = "$runs\judge_60ebb4a4"
$tool = '04_scripts/04_hydraulic/coupled/jp3_ed7_judge.py'
$v0   = "$main\06_analysis\03_hydraulic\coupled\v5\main.jsonl"
$ft   = "$c\ed7_design\fixed_table_b46bdf8f\fixed_table_a2.json"
$grid = "$c\ed6_design\keys\confirm_b_grid192.json"
function Get-DoneFolder($s) { (Get-Content -Raw "$runs\$s.done" | ConvertFrom-Json).folder }
Set-Location $wtj
$L  = Get-DoneFolder 'l1ref'; $T8 = Get-DoneFolder 'impl_t8'; $CS = Get-DoneFolder 'impl_cases'; $PR = Get-DoneFolder 'impl_probe'
foreach ($d in "$J\l1ref_a1", "$J\t8_a1", "$J\cases_a1", "$J\probe-repro_a1") {
    if (Test-Path $d) { throw "exists: $d" }
    New-Item -ItemType Directory -Path $d | Out-Null
}
$codes = [ordered]@{}
& $dpy -I -B $tool l1ref --runs "$L\L1_VBM0.json" "$L\L1_VBM.json" "$L\L1a_VBM0.json" "$L\L1a_VBM.json" --step-done "$runs\l1ref.done" --out "$J\l1ref_a1\l1ref.json" *> "$J\l1ref_a1\console.log"
$codes['l1ref'] = $LASTEXITCODE
& $dpy -I -B $tool t8 --rows "$T8\ed7_t8.jsonl" --step-done "$runs\impl_t8.done" --main-jsonl $v0 --out "$J\t8_a1\t8.json" *> "$J\t8_a1\console.log"
$codes['t8'] = $LASTEXITCODE
& $dpy -I -B $tool cases --rows "$CS\ed7_cases.jsonl" --step-done "$runs\impl_cases.done" --out "$J\cases_a1\cases.json" *> "$J\cases_a1\console.log"
$codes['cases'] = $LASTEXITCODE
& $dpy -I -B $tool probe-repro --rows "$PR\ed7_probe_a2.jsonl" --step-done "$runs\impl_probe.done" --reference "$c\j9_runs\6bfb2560\ed7_probe_a1\ed7_probe.jsonl" --fixed-table $ft --v0 $v0 --grid-keys $grid --grid-root $main --probe-keys "$c\ed7_design\tool_6bfb2560\keys\probe_keys_ed7.json" --sens-keys "$c\ed7_design\keys_seal_b46bdf8f\sens_keys_ed7.json" --out "$J\probe-repro_a1\probe-repro.json" *> "$J\probe-repro_a1\console.log"
$codes['probe-repro'] = $LASTEXITCODE
$codes.GetEnumerator() | ForEach-Object { "$($_.Key) exit=$($_.Value)" }
